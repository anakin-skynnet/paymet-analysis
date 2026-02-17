#!/usr/bin/env -S uv run
"""Test specific flows: AI chat, Genie, Decisioning, Smart Retry, Models, Reason Codes."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9000"
OUT = Path(__file__).resolve().parent.parent / ".screenshots" / "qa-flows"
OUT.mkdir(parents=True, exist_ok=True)

report = []
console_errs = []


def run():
    global report, console_errs
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        context.set_default_timeout(35000)
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errs.append(msg.text[:200])

        page.on("console", on_console)

        # 1. AI Agents page
        print("1. AI Agents page...", end=" ", flush=True)
        try:
            page.goto(BASE + "/ai-agents", wait_until="load", timeout=25000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUT / "01-ai-agents.png"))
            report.append({"flow": "1-ai-agents", "status": "OK", "note": "page loaded"})
            print("OK")
        except Exception as e:
            report.append({"flow": "1-ai-agents", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")
            return

        # 2. AI chat: click button, type, send, wait 30s
        print("2. AI chat flow...", end=" ", flush=True)
        try:
            page.get_by_role("button", name="Open AI chat").click(timeout=5000)
            page.wait_for_timeout(1500)
            inp = page.locator('[role="dialog"][aria-label*="Approval"] input, [role="dialog"] input').first
            inp.wait_for(state="visible", timeout=5000)
            inp.fill("What is the current approval rate?")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(30000)
            page.screenshot(path=str(OUT / "02-ai-chat-response.png"))
            body = page.locator("body").inner_text()
            has_response = "approval" in body.lower() or "88" in body or "82" in body or "error" in body.lower() or "sorry" in body.lower()
            report.append({"flow": "2-ai-chat", "status": "OK", "has_response": has_response})
            print("OK")
        except Exception as e:
            try:
                page.screenshot(path=str(OUT / "02-ai-chat-response.png"))
            except Exception:
                pass
            report.append({"flow": "2-ai-chat", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        # 3. Genie: "Open Genie to chat" opens Databricks externally. Use Genie Assistant (header) for in-app chat.
        print("3. Genie Assistant flow...", end=" ", flush=True)
        try:
            page.goto(BASE + "/ai-agents", wait_until="load", timeout=25000)
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Open Genie Assistant").click(timeout=5000)
            page.wait_for_timeout(2000)
            inp2 = page.locator('[aria-label="Genie Assistant"] input, [role="dialog"] input').first
            inp2.wait_for(state="visible", timeout=5000)
            inp2.fill("Show me top decline reasons")
            page.wait_for_timeout(500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(30000)
            page.screenshot(path=str(OUT / "03-genie-response.png"))
            body3 = page.locator("body").inner_text()
            has_genie = "decline" in body3.lower() or "sorry" in body3.lower() or "error" in body3.lower()
            report.append({"flow": "3-genie", "status": "OK", "has_response": has_genie})
            print("OK")
        except Exception as e:
            try:
                page.screenshot(path=str(OUT / "03-genie-response.png"))
            except Exception:
                pass
            report.append({"flow": "3-genie", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        # 4. Decisioning: preset + Decide authentication
        print("4. Decisioning flow...", end=" ", flush=True)
        try:
            page.goto(BASE + "/decisioning", wait_until="load", timeout=25000)
            page.wait_for_timeout(3000)
            page.get_by_role("button", name="High-risk cross-border").click()
            page.wait_for_timeout(800)
            page.get_by_role("button", name="Decide authentication").click()
            page.wait_for_timeout(10000)
            page.screenshot(path=str(OUT / "04-decisioning-result.png"))
            body = page.locator("body").inner_text()
            has_result = "allow" in body.lower() or "challenge" in body.lower() or "audit" in body.lower() or "error" in body.lower()
            report.append({"flow": "4-decisioning", "status": "OK", "has_result": has_result})
            print("OK")
        except Exception as e:
            page.screenshot(path=str(OUT / "04-decisioning-result.png"))
            report.append({"flow": "4-decisioning", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        # 5. Smart Retry - wait 10s
        print("5. Smart Retry...", end=" ", flush=True)
        try:
            page.goto(BASE + "/smart-retry", wait_until="load", timeout=25000)
            page.wait_for_timeout(10000)
            page.screenshot(path=str(OUT / "05-smart-retry.png"))
            skel = page.locator("[class*='skeleton']").count()
            report.append({"flow": "5-smart-retry", "status": "OK", "skeletons": skel})
            print("OK")
        except Exception as e:
            report.append({"flow": "5-smart-retry", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        # 6. Models - wait 10s
        print("6. Models...", end=" ", flush=True)
        try:
            page.goto(BASE + "/models", wait_until="load", timeout=25000)
            page.wait_for_timeout(10000)
            page.screenshot(path=str(OUT / "06-models.png"))
            skel = page.locator("[class*='skeleton']").count()
            report.append({"flow": "6-models", "status": "OK", "skeletons": skel})
            print("OK")
        except Exception as e:
            report.append({"flow": "6-models", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        # 7. Reason Codes - wait 10s
        print("7. Reason Codes...", end=" ", flush=True)
        try:
            page.goto(BASE + "/reason-codes", wait_until="load", timeout=25000)
            page.wait_for_timeout(10000)
            page.screenshot(path=str(OUT / "07-reason-codes.png"))
            skel = page.locator("[class*='skeleton']").count()
            report.append({"flow": "7-reason-codes", "status": "OK", "skeletons": skel})
            print("OK")
        except Exception as e:
            report.append({"flow": "7-reason-codes", "status": "FAIL", "error": str(e)[:80]})
            print(f"FAIL: {e}")

        browser.close()

    report.append({"console_errors": len(console_errs), "samples": console_errs[:5]})
    print("\n" + "=" * 50)
    for r in report:
        print(r)
    print(f"\nScreenshots: {OUT}/")


if __name__ == "__main__":
    run()
