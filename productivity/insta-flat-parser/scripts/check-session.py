"""Diagnostic: check Instagram session validity."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SESSION_PATH = Path.home() / ".config" / "instaloader" / "session-svaaugust@gmail.com.json"

async def check():
    if not SESSION_PATH.exists():
        print("❌ Session file not found")
        return False

    p = await async_playwright().start()
    b = await p.chromium.launch(headless=True, args=["--no-sandbox"])
    try:
        storage = json.loads(SESSION_PATH.read_text())
        ctx = await b.new_context(
            storage_state=storage,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )

        cookies = await ctx.cookies()
        has_session = any(c["name"] == "ds_user_id" for c in cookies)
        print(f"ds_user_id cookie: {'✅ YES' if has_session else '❌ NO'}")

        if has_session:
            page = await ctx.new_page()
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            content = await page.content()
            if "login" in content.lower()[:5000]:
                print("❌ Session INVALID — redirect to login page")
            else:
                print("✅ Session VALID")
            await page.close()

        await ctx.close()
    finally:
        await b.close()
        await p.stop()

asyncio.run(check())