#!/usr/bin/env -S uv run
"""Test deployed payment analysis app. Run: uv run python scripts/test_deployed_app.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

import os
BASE = os.environ.get("APP_BASE_URL", "https://payment-analysis-984752964297111.11.azure.databricksapps.com")
OUT = Path(__file__).resolve().parent.parent / ".screenshots"
PAGES = [
    ("1-home", "/", "Home"),
    ("2-dashboards", "/dashboards", "Performance Dashboards (3 dashboards)"),
    ("3-about", "/about", "About (CEO presentation)"),
    ("4-declines", "/declines", "Declines"),
    ("5-smart-retry", "/smart-retry", "Smart Retry"),
    ("6-ai-agents", "/ai-agents", "AI Agents"),
]


def main():
    OUT.mkdir(exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        context.set_default_timeout(35000)
        page = context.new_page()

        for fname, path, desc in PAGES:
            try:
                page.goto(f"{BASE}{path}", wait_until="load", timeout=40000)
                page.wait_for_timeout(4000)
                page.screenshot(path=str(OUT / f"{fname}.png"))

                html = page.content()
                has_error = "error" in html.lower() and "Something went wrong" in html
                has_500 = "500" in html or "Internal Server Error" in html

                # Page-specific checks
                dashboards_ok = "dashboards" not in path or ("Executive" in html or "dashboard" in html.lower())
                about_ok = "about" not in path or ("unified" in html.lower() or "CEO" in html)
                declines_ok = "declines" not in path or ("Total" in html or "Declined" in html)
                bell_visible = "Bell" in html or "notification" in html.lower()

                r = {
                    "page": desc,
                    "loaded": True,
                    "error_boundary": has_error,
                    "http_500": has_500,
                    "notification_bell": bell_visible,
                }
                if "dashboards" in path:
                    r["dashboards_visible"] = dashboards_ok
                if "about" in path:
                    r["ceo_content"] = about_ok
                if "declines" in path:
                    r["data_loaded"] = declines_ok
                results.append(r)
                print(f"OK: {desc}")
            except Exception as e:
                results.append({"page": desc, "loaded": False, "error": str(e)[:120]})
                print(f"FAIL: {desc} - {e}")

        browser.close()

    print("\n" + "=" * 60)
    for r in results:
        s = "OK" if r.get("loaded") else "FAILED"
        print(f"{r['page']}: {s}")
        for k, v in r.items():
            if k not in ("page", "loaded") and v is not None:
                print(f"  {k}: {v}")
    print("=" * 60)
    print(f"Screenshots: {OUT}")


if __name__ == "__main__":
    main()
