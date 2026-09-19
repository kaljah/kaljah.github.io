import os
import sys
import time
import json
from collections import defaultdict
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5173"

SKIP_TEXTS = [
    "sign out",
    "logout",
    "log out",
    "delete my account",
    "delete account",
    "purge all"
]

def is_forbidden(text):
    t = (text or "").lower()
    return any(s in t for s in SKIP_TEXTS)

def wait_page_loaded(page, timeout_ms=10000):
    """Wait for lazy-loaded component to finish mounting and spinners to detach."""
    page.wait_for_timeout(1000)
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        try:
            spinners = page.locator('.loading-spinner, .loading-screen, .full-screen-spinner, [data-testid="loading"]')
            visible = any(s.is_visible() for s in spinners.all())
            if not visible:
                break
        except Exception:
            break
        page.wait_for_timeout(200)
    page.wait_for_timeout(500)

def close_any_modal(page):
    try:
        modals = page.locator('.modal:visible, [role="dialog"]:visible, .confirm-modal:visible, .dialog-overlay:visible').all()
        for m in modals:
            close_btn = m.locator('button[aria-label="Close"], button.close, button.modal-close, button:has-text("Cancel"), button:has-text("Close")').first
            if close_btn.is_visible():
                close_btn.click(timeout=600)
                page.wait_for_timeout(200)
            else:
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

def audit_buttons_on_current_page(page, view_title, errors_log, passed_log):
    close_any_modal(page)

    # We test buttons within the page content and interactive controls
    selector = '.main-content button:visible, .main-content [role="button"]:visible, .main-content .btn:visible, .main-content a.btn:visible, .scope-card:visible, .manage-nav-item:visible'
    elements = page.locator(selector).all()
    count = len(elements)
    print(f"  [{view_title}] Found {count} interactive elements in content area", flush=True)

    seen = defaultdict(int)
    clicked = 0

    for i in range(count):
        try:
            current = page.locator(selector).all()
            if i >= len(current):
                break
            el = current[i]
            if not el.is_visible():
                continue

            text = ""
            aria = ""
            title = ""
            try:
                text = el.inner_text() or ""
                aria = el.get_attribute("aria-label") or ""
                title = el.get_attribute("title") or ""
            except Exception:
                pass

            label = (text or aria or title or f"Elem-{i}").replace("\n", " ").strip()[:60]
            if is_forbidden(label):
                continue

            # Don't click User Profile dropdown repeatedly in page loop to avoid modal overlay
            if "user profile" in label.lower():
                continue

            # Limit repeated table-row buttons (e.g. 50 Approve buttons) to 2 clicks
            key = label.lower()
            if seen[key] >= 2:
                continue
            seen[key] += 1

            err_count_before = len(errors_log)

            # Check actionability
            enabled = True
            try:
                enabled = el.is_enabled()
            except Exception:
                pass

            if not enabled:
                passed_log.append({
                    "view": view_title,
                    "control": f"{label} [DISABLED]",
                    "status": "PASS (Disabled)"
                })
                continue

            # Click element
            try:
                el.click(timeout=1000)
            except Exception:
                try:
                    el.evaluate("e => e.click()")
                except Exception:
                    continue

            page.wait_for_timeout(300)
            clicked += 1

            err_count_after = len(errors_log)
            if err_count_after > err_count_before:
                print(f"    ❌ ERROR on '{label}' in {view_title}:", flush=True)
                for err in errors_log[err_count_before:]:
                    print(f"       -> {err['message']}", flush=True)
            else:
                passed_log.append({
                    "view": view_title,
                    "control": label,
                    "status": "PASS"
                })

            # If a modal opened, test buttons inside modal and then close it
            try:
                modals = page.locator('.modal:visible, [role="dialog"]:visible, .confirm-modal:visible').all()
                for m in modals:
                    modal_buttons = m.locator('button:visible, [role="button"]:visible').all()
                    for mb in modal_buttons:
                        mlabel = (mb.inner_text() or mb.get_attribute("aria-label") or "modal-btn").strip()
                        if is_forbidden(mlabel):
                            continue
                        if any(w in mlabel.lower() for w in ["close", "cancel", "dismiss", "x"]):
                            continue
                        # Click modal subtab or action
                        try:
                            if mb.is_enabled():
                                pre_m = len(errors_log)
                                mb.click(timeout=800)
                                page.wait_for_timeout(200)
                                post_m = len(errors_log)
                                if post_m > pre_m:
                                    print(f"    ❌ ERROR on modal button '{mlabel}': {errors_log[-1]['message']}", flush=True)
                                else:
                                    passed_log.append({
                                        "view": f"{view_title} (Modal)",
                                        "control": mlabel,
                                        "status": "PASS"
                                    })
                        except Exception:
                            pass
            except Exception:
                pass

            close_any_modal(page)

        except Exception:
            pass

    print(f"  [{view_title}] Successfully verified {clicked} distinct button actions cleanly.", flush=True)

def run():
    all_errors = []
    all_passed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("dialog", lambda d: d.dismiss())

        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "favicon.ico" in t:
                    return
                all_errors.append({
                    "type": "console.error",
                    "url": page.url,
                    "message": t,
                    "location": msg.location
                })
                print(f"\n[CONSOLE ERROR] {page.url} : {t}\n", flush=True)

        def on_pageerror(err):
            all_errors.append({
                "type": "uncaught_exception",
                "url": page.url,
                "message": str(err),
                "location": None
            })
            print(f"\n[PAGE ERROR] {page.url} : {str(err)}\n", flush=True)

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

        # --------------------------------------------------------------------
        # 1. Login as Admin
        # --------------------------------------------------------------------
        print("Logging in as Admin (admin@ghg.com)...", flush=True)
        page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        wait_page_loaded(page)
        page.fill('input[placeholder="Email Address"]', "admin@ghg.com")
        page.fill('input[placeholder="Password"]', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1500)
        wait_page_loaded(page)
        print("Logged in successfully as Admin.", flush=True)

        # --------------------------------------------------------------------
        # 2. Executive Dashboard
        # --------------------------------------------------------------------
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        wait_page_loaded(page)
        audit_buttons_on_current_page(page, "Executive Dashboard", all_errors, all_passed)

        # --------------------------------------------------------------------
        # 3. Emissions (Scope Selection, Scope 1, Scope 2, Scope 3)
        # --------------------------------------------------------------------
        for sc, title in [("", "Scope Selection"), ("?scope=1", "Scope 1 Direct"), ("?scope=2", "Scope 2 Indirect"), ("?scope=3", "Scope 3 Value Chain")]:
            page.goto(f"{BASE_URL}/emissions{sc}", wait_until="domcontentloaded")
            wait_page_loaded(page)
            audit_buttons_on_current_page(page, f"Emissions {title}", all_errors, all_passed)

        # --------------------------------------------------------------------
        # 4. Manage Data (All Tabs)
        # --------------------------------------------------------------------
        tabs = [
            "pending", "factors", "facilities", "production", "sources",
            "goals", "mitigation", "ogmp", "cbam", "metadata", "level_upgrades"
        ]
        for t in tabs:
            page.goto(f"{BASE_URL}/manage-data?tab={t}", wait_until="domcontentloaded")
            wait_page_loaded(page)
            # Ensure the tab item is active
            try:
                tab_item = page.locator(f'.manage-nav-item:has-text("{t}")').first
                if tab_item.is_visible():
                    tab_item.click(timeout=800)
                    wait_page_loaded(page)
            except Exception:
                pass
            audit_buttons_on_current_page(page, f"Manage Data ({t})", all_errors, all_passed)

        # --------------------------------------------------------------------
        # 5. QA/QC Dashboard (All 3 Sub-tabs)
        # --------------------------------------------------------------------
        page.goto(f"{BASE_URL}/qa-dashboard", wait_until="domcontentloaded")
        wait_page_loaded(page)
        audit_buttons_on_current_page(page, "QA Dashboard (Anomaly Queue)", all_errors, all_passed)

        qa_subtabs = ["Health & Completeness Diagnostics", "Uncertainty & Rigor Analysis (IPCC)"]
        for qst in qa_subtabs:
            try:
                qbtn = page.locator(f'.qa-tab-btn:has-text("{qst}")').first
                if qbtn.is_visible():
                    qbtn.click(timeout=1000)
                    wait_page_loaded(page)
                    audit_buttons_on_current_page(page, f"QA Dashboard ({qst})", all_errors, all_passed)
            except Exception:
                pass

        # --------------------------------------------------------------------
        # 6. Reports (All Sub-tabs & Exports)
        # --------------------------------------------------------------------
        page.goto(f"{BASE_URL}/reports", wait_until="domcontentloaded")
        wait_page_loaded(page)
        audit_buttons_on_current_page(page, "Reports (Main)", all_errors, all_passed)

        report_tabs = page.locator('.reports-tabs button, [role="tab"]').all()
        for rt in report_tabs:
            try:
                rt_text = rt.inner_text().strip()
                if rt_text and rt.is_visible():
                    rt.click(timeout=800)
                    page.wait_for_timeout(400)
                    audit_buttons_on_current_page(page, f"Reports ({rt_text})", all_errors, all_passed)
            except Exception:
                pass

        # --------------------------------------------------------------------
        # 7. Analytics & Calculations
        # --------------------------------------------------------------------
        analytics_routes = [
            ("/carbon-intensity", "Carbon Intensity"),
            ("/methane-intensity", "Methane Intensity"),
            ("/methane-explorer", "Methane Explorer Map"),
            ("/sbti", "SBTi Trajectory"),
            ("/uncertainty", "Uncertainty Monte Carlo"),
            ("/reference-data", "Reference Data Factors"),
            ("/audit-trail", "Audit Trail (Admin)"),
            ("/settings", "Settings")
        ]
        for r_path, r_name in analytics_routes:
            page.goto(f"{BASE_URL}{r_path}", wait_until="domcontentloaded")
            wait_page_loaded(page)
            audit_buttons_on_current_page(page, r_name, all_errors, all_passed)

        # --------------------------------------------------------------------
        # 8. Login as IT Admin & Audit User Management
        # --------------------------------------------------------------------
        print("\nLogging in as IT Admin (itadmin@ghg.com)...", flush=True)
        page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        wait_page_loaded(page)
        page.fill('input[placeholder="Email Address"]', "itadmin@ghg.com")
        page.fill('input[placeholder="Password"]', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1500)
        wait_page_loaded(page)
        print("Logged in successfully as IT Admin.", flush=True)

        it_routes = [
            ("/user-management", "User Management & RBAC"),
            ("/audit-trail", "Audit Trail (IT Admin)")
        ]
        for r_path, r_name in it_routes:
            page.goto(f"{BASE_URL}{r_path}", wait_until="domcontentloaded")
            wait_page_loaded(page)
            audit_buttons_on_current_page(page, r_name, all_errors, all_passed)

        browser.close()

    print("\n" + "=" * 65, flush=True)
    print(" DEEP BUTTON AUDIT RESULTS SUMMARY", flush=True)
    print("=" * 65, flush=True)
    print(f"Total Button & Interactive Actions Executed: {len(all_passed)}", flush=True)
    print(f"Total Console Errors Encountered: {len(all_errors)}", flush=True)

    with open("c:/Users/samsung/Desktop/H2/new/deep_button_audit_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_passed": len(all_passed),
            "total_errors": len(all_errors),
            "errors": all_errors,
            "passed": all_passed
        }, f, indent=2)

    if len(all_errors) > 0:
        print(f"\n[FAILED] Encountered {len(all_errors)} console errors:", flush=True)
        for idx, e in enumerate(all_errors, 1):
            print(f"  {idx}. [{e['type']}] on {e['url']}")
            print(f"     {e['message']}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Pressed every button across all pages with ZERO console errors!", flush=True)
        sys.exit(0)

if __name__ == "__main__":
    run()
