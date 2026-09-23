#!/usr/bin/env python3
"""Phone Agent — Twilio Media Streams voice agent (port of OpenClaw phone-agent skill for Hermes).

Стек: Twilio (телефония) + Deepgram (STT) + LLM (KiloCode/OpenAI-совместимый) + TTS (ElevenLabs | edge-tts).
Запуск: uvicorn phone_agent_server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import base64
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import PlainTextResponse

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("phone-agent")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://example.com").rstrip("/")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_CHAT_URL = os.getenv(
    "LLM_CHAT_URL", "https://api.kilo.ai/api/gateway/chat/completions"
)
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash:discounted")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")  # elevenlabs | edge
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — голосовой ассистент. Отвечай кратко и по делу. Разговаривай естественно.",
)

LOG_DIR = Path(os.getenv("LOG_DIR", str(Path.home() / ".hermes" / "phone_agent" / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Phone Agent")
CALL_PROMPTS: dict[str, str] = {}  # call_sid -> prompt (для исходящих)

DG_URL = (
    "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000"
    "&channels=1&model=nova-2&endpointing=500&interim_results=false"
)


def wss_url() -> str:
    base = PUBLIC_BASE_URL.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/stream"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    call_sid = str(form.get("CallSid", ""))
    prompt = request.query_params.get("prompt", "")
    if prompt and call_sid:
        CALL_PROMPTS[call_sid] = prompt
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="{wss_url()}"/></Connect></Response>'
    )
    return PlainTextResponse(twiml, media_type="application/xml")


def llm_reply(messages: list[dict]) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0.7,
    }
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    resp = requests.post(LLM_CHAT_URL, json=payload, headers=headers, timeout=40)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def tts_mp3(text: str) -> bytes:
    if TTS_PROVIDER == "elevenlabs":
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        body = {"text": text, "model_id": "eleven_multilingual_v2"}
        resp = requests.post(url, json=body, headers=headers, timeout=40)
        resp.raise_for_status()
        return resp.content
    import edge_tts

    mp3 = b""
    communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            mp3 += chunk["data"]
    return mp3


def mp3_to_mulaw(mp3: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        tmp.write(mp3)
        tmp.flush()
        result = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", tmp.name,
             "-f", "mulaw", "-ar", "8000", "-ac", "1", "pipe:1"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="ignore"))
        return result.stdout


@app.websocket("/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    stream_sid = ""
    call_sid = ""
    system_prompt = DEFAULT_SYSTEM_PROMPT
    history: list[dict] = []
    transcript: list[str] = []
    busy = False
    dg_ws = None
    outbound = False

    async def send_media(mulaw: bytes) -> None:
        for i in range(0, len(mulaw), 160):  # 20ms кадры @8k
            chunk = mulaw[i : i + 160]
            await ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": base64.b64encode(chunk).decode()},
                    }
                )
            )

    async def agent_turn(instruction: str = "") -> None:
        nonlocal busy
        busy = True
        try:
            msgs = [{"role": "system", "content": system_prompt}]
            msgs.extend(history[-8:])
            if instruction:
                msgs.append({"role": "user", "content": instruction})
            reply = await asyncio.to_thread(llm_reply, msgs)
            history.append({"role": "assistant", "content": reply})
            transcript.append(f"AGENT: {reply}")
            log.info("AGENT: %s", reply)
            mp3 = await tts_mp3(reply)
            await send_media(mp3_to_mulaw(mp3))
        except Exception as exc:  # noqa: BLE001 — звонок не должен умирать
            log.error("agent_turn failed: %s", exc)
        finally:
            busy = False

    async def dg_reader() -> None:
        assert dg_ws is not None
        while True:
            msg = await dg_ws.recv()
            data = json.loads(msg)
            if data.get("type") != "Results":
                continue
            alt = data["channel"]["alternatives"][0]["transcript"].strip()
            if not data.get("is_final") or not alt:
                continue
            log.info("USER: %s", alt)
            if busy:
                continue
            history.append({"role": "user", "content": alt})
            transcript.append(f"USER: {alt}")
            await agent_turn()

    try:
        import websockets

        while True:
            raw = await ws.receive_text()
            event = json.loads(raw)
            kind = event.get("event")

            if kind == "connected":
                continue

            if kind == "start":
                stream_sid = event["stream"]["streamSid"]
                call_sid = event["stream"].get("callSid", "")
                if call_sid in CALL_PROMPTS:
                    system_prompt = CALL_PROMPTS.pop(call_sid)
                    outbound = True
                log.info("call %s started (outbound=%s)", call_sid, outbound)
                dg_ws = await websockets.connect(
                    DG_URL, additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
                )
                await dg_ws.send(json.dumps({"type": "Configure"}))
                asyncio.create_task(dg_reader())
                if outbound:
                    await agent_turn(
                        "Позвонил сам. Начни разговор: поприветствуй собеседника, "
                        "представься и объясни цель звонка. Сейчас твой ход."
                    )
                continue

            if kind == "media":
                payload = base64.b64decode(event["media"]["payload"])
                if dg_ws is not None:
                    await dg_ws.send(payload)
                continue

            if kind == "stop":
                break
    except Exception as exc:  # noqa: BLE001
        log.error("stream error: %s", exc)
    finally:
        if dg_ws is not None:
            await dg_ws.close()
        if transcript and call_sid:
            path = LOG_DIR / f"{call_sid}.txt"
            path.write_text(
                f"--- {datetime.now().isoformat()} ---\n" + "\n".join(transcript) + "\n",
                encoding="utf-8",
            )
            log.info("transcript saved: %s", path)
        await ws.close()
