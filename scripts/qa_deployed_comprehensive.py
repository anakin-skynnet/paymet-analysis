#!/usr/bin/env -S uv run
"""Comprehensive UI test: deployed Databricks App."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://payment-analysis-984752964297111.11.azure.databricksapps.com"
OUT = Path(__file__).resolve().parent.parent / ".screenshots" / "qa-deployed-comprehensive"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        context.set_default_timeout(25000)
        page = context.new_page()

        # 1. Landing
        print("1. Landing...")
        page.goto(BASE, wait_until="load", timeout=30000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "01-landing.png"))
        url = page.url
        html = page.content()
        is_login = "login" in url.lower() or "microsoft" in url.lower() or "entra" in html.lower()
        report.append({"step": 1, "page": "landing", "url": url[:70], "login_gate": is_login})

        if is_login:
            report.append({"note": "All app URLs redirect to login. Cannot access sidebar, KPIs, dashboards, or AI chat without authentication."})
        else:
            # 2-3: Check load, sidebar
            report.append({"step": 2, "load": "OK", "errors": "Something went wrong" in html})
            sidebar = page.locator("aside, [data-sidebar], nav")
            sidebar_items = page.locator("a[href*='command-center'], a[href*='dashboards'], a[href*='declines']").all_inner_texts() if page.locator("a[href*='command-center']").count() > 0 else []
            report.append({"step": 3, "sidebar_items": sidebar_items[:10]})

            # 4. Command Center
            print("4. Command Center...")
            page.goto(BASE + "/command-center", wait_until="load", timeout=20000)
            page.wait_for_timeout(5000)
            page.screenshot(path=str(OUT / "02-command-center.png"))
            html4 = page.content()
            kpis = "4,393,200" in html4 or "148,520" in html4 or "88" in html4 or "82" in html4
            report.append({"step": 4, "page": "command-center", "kpi_data": kpis})

            # 5. Check KPIs
            total_tx = "4,393,200" in html4 or "148520" in html4
            approval = "82" in html4 or "88" in html4
            report.append({"step": 5, "total_tx": total_tx, "approval_rate": approval})

            # 6. Dashboards
            print("6. Dashboards...")
            page.goto(BASE + "/dashboards", wait_until="load", timeout=20000)
            page.wait_for_timeout(5000)
            page.screenshot(path=str(OUT / "03-dashboards.png"))
            report.append({"step": 6, "page": "dashboards"})

            # 7. Decisioning
            print("7. Decisioning...")
            page.goto(BASE + "/decisioning", wait_until="load", timeout=20000)
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / "04-decisioning.png"))
            report.append({"step": 7, "page": "decisioning"})

            # 8. AI Chat button
            page.goto(BASE + "/command-center", wait_until="load", timeout=20000)
            page.wait_for_timeout(3000)
            ai_btn = page.locator("button:has-text('AI chat'), [aria-label*='chat']").first
            ai_found = ai_btn.count() > 0
            if ai_found:
                ai_btn.click()
                page.wait_for_timeout(2000)
                page.screenshot(path=str(OUT / "05-ai-chat-open.png"))
            report.append({"step": 8, "ai_chat_visible": ai_found})

            # 9. Error toasts
            errors = page.locator("text=Something went wrong, [role=alert], .toast-error").count()
            report.append({"step": 9, "error_toasts": errors})

        browser.close()

    print("\n" + "=" * 60)
    for r in report:
        print(f"  {r}")
    print(f"\nScreenshots: {OUT}/")


if __name__ == "__main__":
    main()
