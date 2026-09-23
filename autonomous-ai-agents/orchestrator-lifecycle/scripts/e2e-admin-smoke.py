"""E2E smoke: связка фронт-контракт ↔ backend через Telegram initData.

Проверяет, что backend поднят, авторизация initData работает, роли соблюдаются.
Паттерн переиспользуем для любого FastAPI-проекта с Telegram Mini App авторизацией.

Адаптация под другой проект:
- BASE, TOKEN_* — токены тенанта из БД (patient/worker)
- INSERT-запросы — под схему: tenants (patient_bot_token/worker_bot_token), users (role enum!)
- Роль в БД может быть ВЕРХНИМ регистром ('OWNER'), а в API ответе — нижним ('owner')
- enum user_role: SELECT enum_range(NULL::user_role);

Запуск: .venv/bin/python e2e-admin-smoke.py   (asyncpg + httpx в зависимостях проекта)
"""
import asyncio
import hashlib
import hmac
import json
import time
from urllib.parse import quote

import asyncpg
import httpx

BASE = "http://localhost:8000"
TOKEN_PATIENT = "777777:SMOKE_PATIENT"
TOKEN_WORKER = "888888:SMOKE_WORKER"
OWNER_TG = 1000001
SPEC_TG = 1000002


def make_init_data(bot_token: str, user_id: int, name: str) -> str:
    """Telegram WebApp initData: HMAC-SHA256 с секретом WebAppData(bot_token).

    Формат совпадает с validate_init_data в src/infrastructure/telegram/initdata.py:
    data_check_string = отсортированные пары k=v через \\n, hash = HMAC(secret, dcs).
    """
    auth_date = int(time.time())
    user = json.dumps({"id": user_id, "first_name": name}, separators=(",", ":"))
    dcs = "\n".join(f"{k}={v}" for k, v in sorted({"auth_date": str(auth_date), "user": user}.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return f"auth_date={auth_date}&user={quote(user, safe='')}&hash={digest}"


async def main():
    conn = await asyncpg.connect("postgresql://booking:booking@localhost:5432/booking")
    tid = await conn.fetchval(
        "INSERT INTO tenants (slug, name, patient_bot_token, worker_bot_token, gap_minutes,"
        " confirm_mode, categories_enabled, notify_start, notify_end)"
        " VALUES ('smoke-test', 'Smoke Test', $1, $2, 15, 'manual', false, '09:00', '21:00')"
        " ON CONFLICT (slug) DO UPDATE SET patient_bot_token=EXCLUDED.patient_bot_token,"
        " worker_bot_token=EXCLUDED.worker_bot_token RETURNING id",
        TOKEN_PATIENT, TOKEN_WORKER,
    )
    await conn.execute(
        "INSERT INTO users (telegram_id, name, role, opened_bot, tenant_id) VALUES"
        " ($1, 'Smoke Owner', 'OWNER', true, $2), ($3, 'Smoke Specialist', 'SPECIALIST', true, $2)"
        " ON CONFLICT (tenant_id, telegram_id) DO UPDATE SET name=EXCLUDED.name, role=EXCLUDED.role",
        OWNER_TG, tid, SPEC_TG,
    )
    await conn.close()
    print(f"tenant id={tid}")

    headers_owner = {"X-Telegram-Init-Data": make_init_data(TOKEN_PATIENT, OWNER_TG, "Smoke Owner")}
    headers_spec = {"X-Telegram-Init-Data": make_init_data(TOKEN_PATIENT, SPEC_TG, "Smoke Specialist")}

    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        checks = [
            ("GET /api/me (owner)", c.get("/api/me", headers=headers_owner), 200),
            ("GET /api/me (specialist)", c.get("/api/me", headers=headers_spec), 200),
            ("GET /api/admin/schedule (owner)", c.get("/api/admin/schedule", headers=headers_owner), 200),
            ("GET /api/admin/schedule (specialist)", c.get("/api/admin/schedule", headers=headers_spec), 200),
            ("GET /api/admin/stats (owner)", c.get("/api/admin/stats", headers=headers_owner), 200),
            ("GET /api/admin/stats (specialist → 403)", c.get("/api/admin/stats", headers=headers_spec), 403),
            ("GET /api/admin/clients?lead=1 (owner)", c.get("/api/admin/clients", params={"lead": "1"}, headers=headers_owner), 200),
            ("GET /api/admin/settings (owner)", c.get("/api/admin/settings", headers=headers_owner), 200),
            ("GET /api/admin/services (owner)", c.get("/api/admin/services", headers=headers_owner), 200),
            ("GET /api/admin/specialists (owner)", c.get("/api/admin/specialists", headers=headers_owner), 200),
            ("GET /api/admin/overrides (owner)", c.get("/api/admin/overrides", headers=headers_owner), 200),
        ]
        ok = 0
        for label, req, expected in checks:
            r = await req
            mark = "✅" if r.status_code == expected else f"❌ (expected {expected})"
            detail = ""
            if r.status_code == 200:
                body = r.json()
                if label.startswith("GET /api/me"):
                    detail = f" role={body.get('role')} id={body.get('id')}"
                elif isinstance(body, list):
                    detail = f" n={len(body)}"
                elif isinstance(body, dict):
                    detail = f" keys={sorted(body.keys())[:5]}"
            if r.status_code == expected:
                ok += 1
            print(f"{mark} {label} → {r.status_code}{detail}")
        print(f"\nИТОГ: {ok}/{len(checks)} passed")


asyncio.run(main())
