#!/usr/bin/env -S uv run
"""Retry failed pages with domcontentloaded and longer timeout."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9000"
OUT = Path(__file__).resolve().parent.parent / ".screenshots" / "qa-deep"

FAILED = [
    ("06-reason-codes", "/reason-codes", 12),
    ("07-dashboards", "/dashboards", 12),
    ("08-ai-agents", "/ai-agents", 10),
    ("12-about", "/about", 5),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900}, ignore_https_errors=True)
        context.set_default_timeout(45000)
        page = context.new_page()
        for name, path, wait_s in FAILED:
            print(f"  {name}...", end=" ", flush=True)
            try:
                page.goto(BASE + path, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_load_state("load", timeout=15000)
                page.wait_for_timeout(wait_s * 1000)
                if name == "07-dashboards":
                    try:
                        page.get_by_role("button", name="View in app").first.click(timeout=3000)
                        page.wait_for_timeout(4000)
                    except Exception:
                        pass
                elif name == "08-ai-agents":
                    try:
                        page.get_by_role("button", name="Open AI chat").click(timeout=3000)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                page.screenshot(path=str(OUT / f"{name}.png"))
                print("OK")
            except Exception as e:
                print(f"FAIL: {e}")
        browser.close()
    print(f"Screenshots: {OUT}/")


if __name__ == "__main__":
    main()
