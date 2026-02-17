#!/usr/bin/env -S uv run
"""Comprehensive deep test of every page at localhost:9000."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9000"
OUT = Path(__file__).resolve().parent.parent / ".screenshots" / "qa-deep"

# (name, path, wait_s, extra_actions)
PAGES = [
    ("01-landing", "/", 4, None),
    ("02-command-center", "/command-center", 12, None),
    ("03-declines", "/declines", 10, None),
    ("04-smart-retry", "/smart-retry", 10, None),
    ("05-smart-checkout", "/smart-checkout", 10, None),
    ("06-reason-codes", "/reason-codes", 10, None),
    ("07-dashboards", "/dashboards", 10, "click_view_in_app"),
    ("08-ai-agents", "/ai-agents", 8, "open_ai_chat"),
    ("09-decisioning", "/decisioning", 10, "decisioning_interact"),
    ("10-models", "/models", 8, None),
    ("11-data-quality", "/data-quality", 12, None),
    ("12-about", "/about", 4, None),
    ("13-profile", "/profile", 10, None),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    console_errs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        context.set_default_timeout(30000)
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errs.append(msg.text[:200])

        page.on("console", on_console)

        for name, path, wait_s, extra in PAGES:
            print(f"  {name}...", end=" ", flush=True)
            try:
                page.goto(BASE + path, wait_until="load", timeout=25000)
                page.wait_for_timeout(wait_s * 1000)

                # Extra interactions
                if extra == "click_view_in_app":
                    try:
                        btn = page.get_by_role("button", name="View in app").first
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            page.wait_for_timeout(4000)
                    except Exception:
                        pass

                elif extra == "open_ai_chat":
                    try:
                        chat_btn = page.get_by_role("button", name="Open AI chat")
                        if chat_btn.is_visible(timeout=3000):
                            chat_btn.click()
                            page.wait_for_timeout(2000)
                    except Exception:
                        try:
                            page.locator('button:has-text("AI chat")').first.click()
                            page.wait_for_timeout(2000)
                        except Exception:
                            pass

                elif extra == "decisioning_interact":
                    try:
                        page.get_by_role("button", name="High-risk cross-border").click()
                        page.wait_for_timeout(800)
                        page.get_by_role("button", name="Decide authentication").click()
                        page.wait_for_timeout(3000)
                    except Exception:
                        pass

                page.screenshot(path=str(OUT / f"{name}.png"))

                html = page.content()
                mc = page.locator("#main-content")
                chars = 0
                if mc.count() > 0:
                    try:
                        chars = len(mc.first.inner_text(timeout=2000).strip())
                    except Exception:
                        pass
                body_text = page.locator("body").inner_text()
                has_error = "Something went wrong" in html or "Failed to load" in html
                has_mock = "mock" in body_text.lower() or "Data: Mock" in body_text
                has_dash = "—" in body_text
                skeleton_count = page.locator("[class*='skeleton']").count()
                chart_count = page.locator("[class*='recharts']").count()

                report.append({
                    "page": name,
                    "load": "OK",
                    "main_chars": chars,
                    "error": has_error,
                    "mock": has_mock,
                    "skeleton": skeleton_count,
                    "charts": chart_count,
                })
                print("OK")
            except Exception as e:
                report.append({"page": name, "load": "FAIL", "error": str(e)[:120]})
                print(f"FAIL: {e}")

        report.append({"console_errors": len(console_errs), "samples": console_errs[:8]})
        browser.close()

    print("\n" + "=" * 60)
    for r in report:
        print(r)
    print(f"\nScreenshots: {OUT}/")


if __name__ == "__main__":
    main()
