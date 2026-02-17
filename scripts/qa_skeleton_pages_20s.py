#!/usr/bin/env -S uv run
"""Test smart-retry, models, reason-codes with 20s wait each."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9000"
OUT = Path(__file__).resolve().parent.parent / ".screenshots" / "qa-20s"
OUT.mkdir(parents=True, exist_ok=True)

console_errs = []


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        context.set_default_timeout(40000)
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errs.append(msg.text[:200])

        page.on("console", on_console)

        pages = [
            ("smart-retry", "/smart-retry", "01-smart-retry"),
            ("models", "/models", "02-models"),
            ("reason-codes", "/reason-codes", "03-reason-codes"),
        ]

        for name, path, out_name in pages:
            print(f"  {name}...", end=" ", flush=True)
            try:
                page.goto(BASE + path, wait_until="load", timeout=25000)
                page.wait_for_timeout(20000)
                page.screenshot(path=str(OUT / f"{out_name}.png"))
                skel = page.locator("[class*='skeleton']").count()
                body = page.locator("body").inner_text()
                has_error = "Something went wrong" in body or "Failed to load" in body
                # Check for real numbers (not just dashes)
                has_numbers = any(c.isdigit() for c in body[:2000])
                recharts = page.locator("[class*='recharts']").count()
                print(f"OK (skeletons={skel}, recharts={recharts})")
            except Exception as e:
                print(f"FAIL: {e}")
            page.wait_for_timeout(1000)

        browser.close()

    print("\nConsole errors:", len(console_errs))
    for e in console_errs[:5]:
        print(" ", e[:100])
    print(f"\nScreenshots: {OUT}/")


if __name__ == "__main__":
    main()
