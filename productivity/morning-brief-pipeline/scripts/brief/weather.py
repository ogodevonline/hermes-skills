"""Погода — wttr.in для Москвы"""
import json
import subprocess

WEATHER_EMOJI = {
    "sunny": "☀️", "clear": "☀️",
    "partly cloudy": "⛅", "partly": "⛅",
    "cloudy": "☁️", "overcast": "☁️",
    "mist": "🌫️", "fog": "🌫️", "freezing fog": "🌫️",
    "drizzle": "🌦️", "patchy rain": "🌦️", "light rain": "🌧️",
    "rain": "🌧️", "heavy rain": "🌧️",
    "sleet": "🌨️", "snow": "❄️", "blizzard": "🌨️",
    "thunder": "⛈️", "storm": "⛈️",
}


def _run_command(cmd, timeout=30):
    """Выполнить shell-команду"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def _weather_emoji(desc):
    """Эмодзи по описанию погоды"""
    desc_l = desc.lower()
    for key, emoji in WEATHER_EMOJI.items():
        if key in desc_l:
            return emoji
    return "🌤️"


def _outfit_advice(min_temp, max_temp, has_rain, has_snow):
    """Рекомендация по одежде"""
    avg = (min_temp + max_temp) / 2
    advice = []
    if avg < 0:
        advice.append("🧥 Тёплая куртка, шапка, перчатки")
    elif avg < 5:
        advice.append("🧥 Куртка, шарф обязательны")
    elif avg < 10:
        advice.append("🧥 Лёгкая куртка или пальто")
    elif avg < 16:
        advice.append("🪶 Ветровка или кофта")
    elif avg < 22:
        advice.append("👕 Лёгкая одежда, может пригодиться кофта")
    else:
        advice.append("👕 Жарко — лёгкое и дышащее")
    if has_rain:
        advice.append("☂️ Возьми зонт")
    if has_snow:
        advice.append("👢 Непромокаемая обувь")
    return " · ".join(advice)


def get_weather():
    """Детальный прогноз Москва: сейчас + утро/день/вечер + одежда"""
    raw, _ = _run_command("curl -s --max-time 15 'https://wttr.in/Moscow?format=j1'")
    if not raw:
        return "🌤️ Погода недоступна"

    try:
        d = json.loads(raw)
    except Exception:
        return "🌤️ Ошибка парсинга погоды"

    # Текущие условия
    cur = d.get("current_condition", [{}])[0]
    temp_now   = cur.get("temp_C", "?")
    feels_now  = cur.get("FeelsLikeC", "?")
    desc_now   = (cur.get("weatherDesc") or [{}])[0].get("value", "?")
    humidity   = cur.get("humidity", "?")
    wind       = cur.get("windspeedKmph", "?")
    emoji_now  = _weather_emoji(desc_now)

    lines = [
        f"🌡️ Сейчас: {emoji_now} {temp_now}°C (ощущается {feels_now}°C), {desc_now}",
        f"   💧 {humidity}% влажность · 💨 {wind} км/ч",
    ]

    # Прогноз на сегодня по слотам
    weather_days = d.get("weather", [])
    if weather_days:
        today = weather_days[0]
        max_t = int(today.get("maxtempC", 20))
        min_t = int(today.get("mintempC", 0))
        hourly = today.get("hourly", [])

        # Слоты: утро=600, день=1200, вечер=1800
        slots = {"🌅 Утро (6–12)": ["600", "900"], "☀️ День (12–18)": ["1200", "1500"], "🌙 Вечер (18–24)": ["1800", "2100"]}
        slot_lines = []
        has_rain = False
        has_snow = False

        for slot_name, times in slots.items():
            slot_data = [h for h in hourly if h.get("time") in times]
            if not slot_data:
                continue
            temps = [int(h.get("tempC", 0)) for h in slot_data]
            descs = [((h.get("weatherDesc") or [{}])[0].get("value", "")) for h in slot_data]
            precips = [float(h.get("precipMM", 0)) for h in slot_data]
            avg_t = sum(temps) // len(temps)
            desc = descs[0] if descs else "?"
            precip = sum(precips)
            emj = _weather_emoji(desc)
            precip_str = f" 🌧️{precip:.1f}мм" if precip > 0.1 else ""
            slot_lines.append(f"   {slot_name}: {emj} {avg_t}°C, {desc}{precip_str}")
            if precip > 0.1 and "snow" not in desc.lower() and "sleet" not in desc.lower():
                has_rain = True
            if "snow" in desc.lower() or "sleet" in desc.lower():
                has_snow = True

        lines.append(f"\n📆 Прогноз на сегодня (min {min_t}°C / max {max_t}°C):")
        lines.extend(slot_lines)
        lines.append(f"\n👗 Что надеть: {_outfit_advice(min_t, max_t, has_rain, has_snow)}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_weather())