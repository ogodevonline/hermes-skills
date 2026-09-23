---
name: phone-agent
description: "AI-звонки через Twilio: приём и исходящие, STT+LLM+TTS."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [phone, twilio, voice, ai-agent, deepgram, elevenlabs]
    category: devops
    related_skills: [vps-service-deployment, hermes-ops]
---

# Phone Agent Skill

Порт OpenClaw-навыка **Phone Voice Agent** (clawbot.ai, автор kesslerio) на Hermes: реальный голосовой агент, который принимает входящие звонки и совершает исходящие через Twilio Media Streams. Речь распознаётся (Deepgram), ответ генерирует LLM (KiloCode/OpenAI-совместимый), озвучка — ElevenLabs или edge-tts. Транскрипт каждого звонка пишется в файл.

## When to Use

- Пользователь хочет «ИИ, который сам звонит» (как в рилсе @slavikinvestor) или принимает звонки.
- Нужен голосовой бот: узнать наличие товара, договориться о бартере, записать клиента, отвечать на звонки бизнеса.

## Prerequisites

- Сервер с **публичным HTTPS/WSS** (Twilio не работает с http:// и ws://). vdska + Caddy/nginx.
- **Twilio**: аккаунт, номер телефона, Account SID + Auth Token. Минуты и номер платные (~$1–2/мес номер, ~$0.013/мин США).
- **Deepgram API key** (STT, бесплатные $200 кредитов).
- **TTS**: ElevenLabs API key (free tier ~10K кредитов/мес) ИЛИ `edge-tts` (бесплатно, чуть хуже голос).
- **LLM key**: `KILOCODE_API_KEY` (OpenAI-совместимый, base_url `https://api.kilo.ai/api/gateway`).
- `ffmpeg` на сервере (перекодировка TTS mp3 → mulaw 8k).
- Python 3.11+; зависимости: `pip install -r requirements.txt` (fastapi, uvicorn, websockets, twilio, requests, python-dotenv, edge-tts).

## How to Run

```bash
cd <skill_dir>/scripts
cp .env.example .env          # заполни ключи
uvicorn phone_agent_server:app --host 0.0.0.0 --port 8000
```

Исходящий звонок:

```bash
python outbound.py "+79991234567" "Позвони в обувной, узнай размеры кроссовок, предложи бартер"
```

## Quick Reference

- `GET /health` — проверка живости сервера
- `POST /voice` — Twilio webhook (TwiML `<Connect><Stream>`), публикуется как URL номера
- `WS /stream` — Media Streams: mulaw 8k base64, события connected/start/media/stop
- `python outbound.py <номер> "<промпт>"` — исходящий звонок
- Транскрипты звонков: `~/.hermes/phone_agent/logs/<CallSid>.txt`

## Провайдеры по регионам

Код v1 написан под протокол **Twilio Media Streams** (webhook `/voice` + WS `/stream`). Телефония — сменный слой: webhook и WS-события переписываются под другого провайдера (~2 часа работы). STT/TTS тоже заменяемы через конфиг.

**Телефония:**

| Регион | Провайдер | Что даёт | Замечания |
|---|---|---|---|
| Мир | Twilio | Media Streams (WS), номера US/UK/DE и др. | Не работает в РФ; узбекских номеров не продаёт |
| РФ/СНГ | Voximplant | Voice AI, Media over WebSockets, номера 60+ стран, от 150 ₽/мес, рубли | Прямой аналог Twilio Media Streams (docs.voximplant.ai) |
| РФ | МТС Exolve / Телфин | голосовые API, 8-800/городские | realtime-стрим слабее, чем Voximplant |
| УЗ | pbx.uz (onlinePBX UZ) | узбекские номера, SIP, автообзвон, CRM | через SIP можно поднять свой AI-агент |
| УЗ | Aisha AI (aisha.group) | готовый голосовой ИИ-агент, STT/TTS на узбекском | под ключ (не твой код); кейс «запись к врачу» |

**STT/TTS по регионам:**

| Регион | STT | TTS |
|---|---|---|
| Мир | Deepgram | ElevenLabs / edge-tts |
| РФ | Yandex SpeechKit, Vosk (локально, бесплатно) | Yandex SpeechKit, piper (локально) |
| УЗ | Aisha STT (узбекский/русский/англ.) | Aisha TTS (узбекские голоса, streaming) |

LLM не привязан к региону — KiloCode/DeepSeek работает и в РФ, и в УЗ.

## Procedure

1. **Скопируй навык на сервер** (vdska): `~/.hermes/skills/phone-agent/`.
2. **Заполни `.env`**: Twilio SID/токен/номер, Deepgram key, LLM key/модель, TTS-провайдер, `PUBLIC_BASE_URL=https://твой-домен`.
3. **Запусти**: `uvicorn phone_agent_server:app --host 0.0.0.0 --port 8000`. Отдай наружу: Caddy `reverse_proxy https://твой-домен :8000`.
4. **Настрой Twilio** (консоль → Phone Numbers → свой номер → Voice Configuration):
   - When a call comes in: Webhook → `https://твой-домен/voice`, HTTP POST.
   - Сохрани. Входящие звонки теперь отвечает агент.
5. **Исходящий**: `python outbound.py "+79991234567" "промпт"` — агент сам позвонит и начнёт разговор первым.
6. Проверь: `GET /health` → `ok`, потом тестовый звонок.

## Pitfalls

- **Код v1 — под Twilio-протокол** (Media Streams: события `connected/start/media/stop`, mulaw 8k). Для Voximplant (Media over WebSockets) или pbx.uz/SIP протокол другой — адаптируй `/voice` и WS-обработчик перед продом (см. «Провайдеры по регионам»).
- **HTTPS обязателен.** Twilio отклоняет http-вебхуки (для номера — только HTTPS, для Studio допустимо http на localhost через туннель только для теста).
- **Формат аудио**: mulaw 8kHz 8-bit, base64. Любой другой — Twilio проиграет как шум.
- **Deepgram streaming** требует `encoding=mulaw&sample_rate=8000&channels=1`; `endpointing=500` даёт отсечку конца фразы.
- **Первый ход у исходящего** делает агент (LLM генерирует приветствие сразу после `start`).
- Если LLM endpoint Kilo не отвечает (404) — проверь путь: может нужен `/v1/chat/completions` (см. `LLM_CHAT_URL` в `.env.example`).
- Эхо/перебивание: в v1 агент отвечает целиком после паузы юзера; live-интервенция из чата (как в рилсе) — апгрейд, в v1 не входит.
- Держи `SYSTEM_PROMPT` конкретным: «ты Эрик, звонишь от имени блогера-инвестора, цель — бартер» — иначе LLM болтает впустую.

## Verification

- `curl https://твой-домен/health` → `{"status":"ok"}`.
- После звонка в `~/.hermes/phone_agent/logs/` появляется файл с транскриптом (проверь, что текст покрывает разговор).
- Тестовый входящий: позвони на Twilio-номер → агент должен ответить и поддержать диалог.
