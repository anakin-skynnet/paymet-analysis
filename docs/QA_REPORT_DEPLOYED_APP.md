# QA Report: Payment Analysis Databricks App (Deployed)

**Deployed app URL:** https://payment-analysis-984752964297111.11.azure.databricksapps.com  
**Report date:** 2026-03-04  
**Testing method:** Codebase review + HTTP probe (browser automation unavailable; Playwright MCP not returning tools; deployed app returned 503).

---

## 1. Deployed URL Access

| Check | Result |
|-------|--------|
| **HTTP GET** | **503 Service Unavailable** (no redirect to login). Response: `content-type: text/html; charset=UTF-8`, `server: databricks`. |
| **Redirect to login** | Not observed — request did not reach a login page; app/service was unavailable. |
| **Conclusion** | The app instance is either scaled to zero, restarting, or the deployment is unhealthy. No in-browser testing was possible. |

**Recommendation:** Confirm app status in Databricks (Compute → Apps → payment-analysis). If the app is running, retry the URL; if 503 persists, check app logs via `uv run apx databricks-apps logs` or Workspace → Apps → payment-analysis → Logs.

---

## 2. Route Map (from codebase)

All routes are client-side; no route-level auth guard blocks navigation. When not opened from **Compute → Apps**, the landing page shows a card: *"Open from your workspace (Compute → Apps) to sign in with Databricks."* API calls may fail or return empty without a token.

### 2.1 Main routes

| Path | Purpose | Error boundary | Loading / empty handling |
|------|---------|----------------|---------------------------|
| `/` | Landing (index) | Yes (Try again) | Auth banner when unauthenticated |
| `/command-center` | Overview hub (KPIs, trends, dashboards, AI chat) | Implicit (root) | Skeletons, many `useGet*` hooks |
| `/dashboards` | Performance dashboards list + embed view | Yes | Skeleton grid, empty state, isError alert |
| `/decisioning` | Recommendations, auth/retry/routing decisions, ML predictions | Yes | Loading/error on recommendations and decision cards |
| `/declines` | Decline analytics, KPIs, recovery opportunities | Yes | Suspense + Skeletons |
| `/reason-codes` | Reason-code insights, false-insight metrics, expert review | Yes | Loading states on queries |
| `/smart-checkout` | 3DS funnel, service-path performance | Yes | — |
| `/smart-retry` | Retry KPIs, success rates, recovered value | Yes | Suspense (useGetRetryPerformanceSuspense, useGetKpisSuspense) |
| `/ai-agents` | Agents list (Genie, Model Serving, AI Gateway, Custom) | Yes | Loading skeleton, empty list |
| `/models` | ML models (UC registry, serving) | Yes | useGetModelsSuspense |
| `/experiments` | A/B experiments, MLflow runs | Yes | List + create/start/stop |
| `/rules` | Approval/routing rules (CRUD) | Yes | — |
| `/notebooks` | Workspace notebooks browser | Yes | — |
| `/data-quality` | Monitoring, TPS, data quality, alerts | Yes | — |
| `/setup` | Jobs, pipelines, catalog/schema, connection status | Yes | Token/connection messaging |
| `/initiatives` | Initiatives overview | Yes | useGetKpisSuspense, useGetSolutionPerformanceSuspense |
| `/profile` | User profile | Yes | — |
| `/about` | About / documentation links | Yes | — |

### 2.2 Redirects (legacy/bookmark support)

| Path | Redirects to |
|------|--------------|
| `/dashboard` | `/command-center` |
| `/incidents` | `/data-quality` |
| `/alerts-data-quality` | `/data-quality` |

---

## 3. Working Routes (expected when app and backend are healthy)

When the app returns 200 and the backend can reach Databricks:

- **Landing:** `/` — Renders; shows “Open workspace” when not authenticated.
- **Overview:** `/command-center` — KPIs, approval trends, throughput, alerts, 3DS funnel, reason-code insights, retry performance, geography, merchant segments, control panel, AI chat trigger.
- **Analytics:** `/dashboards`, `/declines`, `/reason-codes`, `/data-quality` — List/embed dashboards; decline and reason-code analytics; monitoring and alerts.
- **Optimization:** `/smart-checkout`, `/smart-retry`, `/decisioning` — 3DS/service paths; retry KPIs; decision playground and recommendations.
- **AI & ML:** `/ai-agents`, `/models`, `/experiments` — Agents list; model registry; experiments.
- **Administration:** `/rules`, `/notebooks`, `/setup` — Rules CRUD; notebooks; jobs/pipelines and config.
- **Other:** `/initiatives`, `/profile`, `/about` — Initiatives summary; profile; about.

Redirects `/dashboard`, `/incidents`, `/alerts-data-quality` work as designed.

---

## 4. Issues and UX Observations (from code review)

### 4.1 Deployment / access

- **503 on deployed URL** — App not serving requests; blocks all live testing until resolved.

### 4.2 Consistency

- **Footer copy (landing):** “Data foundation for all initiatives · **Brazil**” — Region-specific; consider making configurable or generic (e.g. “Data foundation for all initiatives”).
- **Incidents / Alerts:** `/incidents` and `/alerts-data-quality` redirect to `/data-quality`; sidebar does not list “Incidents” as a separate item (by design). No issue if intent is a single Monitoring & Quality page.

### 4.3 Loading and empty states

- **Command Center:** Uses many non-Suspense hooks; skeletons and progressive loading are present. When backend/Databricks is down or slow, multiple sections can show loading or empty; consider a single “Connection issue” banner when health check fails.
- **Dashboards:** Empty state and `isError` alert are clear. “View in app” uses `DashboardRenderer` (SQL-powered charts) when iframe embed is not allowed; fallback messaging is documented in code.
- **Decisioning:** Recommendations have loading skeleton and error alert (“Could not load recommendations”); decision and prediction cards show per-card error + Retry. Good.
- **Reason Codes / Smart Retry / Declines:** Error boundaries and loading/skeleton patterns are in place; Smart Retry and Declines use Suspense (root Suspense covers them).

### 4.4 Error handling

- **Root:** `ErrorBoundary` with “Something went wrong” + “Try again” and `router.invalidate()` on reset.
- **Routes reviewed:** Index, Command Center, Dashboards, Decisioning, Declines, Reason Codes, Smart Retry, AI Agents, Experiments each have route-level or component-level `ErrorBoundary` with “Try again”.
- **API errors:** Decisioning and Dashboards surface backend/connection errors in alerts; Recommendation and decision cards show inline errors with retry. No generic “Offline” or “Backend unavailable” bar was found; adding one could help when `useHealthDatabricks` or a similar check fails.

### 4.5 Approval-rate and business value

- **Landing:** Headline “Accelerate approval rates” and subcopy (“One platform for risk, routing, and portfolio visibility”) align with the goal.
- **Command Center:** KPIs, approval trends, retry performance, 3DS funnel, reason-code insights, and control panel support “accelerate approval rates” and portfolio visibility.
- **Decisioning:** “How this accelerates approval rates” card and recommendations with “Create Rule” / “Apply to Context” support actionability.
- **Declines:** “Actionable insights to accelerate approvals” and links to Decisioning are present.
- **Reason Codes:** INTELLIGENCE_OUTCOMES list and false-insight metrics support approval-rate and quality goals.

No missing or misleading high-level value proposition was identified; a few pages could add a one-line “Why this matters for approval rates” where it’s absent (e.g. Models, Notebooks).

---

## 5. Recommendations

### 5.1 Immediate (deployment)

1. **Resolve 503:** Check app status and logs in Databricks; fix scaling/health so the deployed URL returns 200.
2. **Re-test after login:** Open the app from **Compute → Apps → payment-analysis**, then run through the route list above and note any console errors, failed API calls, or broken embeds.

### 5.2 UX and robustness

3. **Global connection/health banner:** When `useHealthDatabricks` (or equivalent) indicates backend/Databricks unreachable, show a single dismissible or persistent banner (e.g. “Can’t reach Databricks. Some data may be missing. [Retry]”) instead of leaving many sections in loading or empty.
4. **Landing footer:** Make “Brazil” configurable or remove if the app is not Brazil-specific.
5. **Empty vs. error:** On key pages (e.g. Command Center), distinguish “no data yet” (e.g. jobs not run) from “backend/API error” in copy or icon so users know whether to run setup jobs or contact support.

### 5.3 Copy and clarity

6. **Low-value or technical pages:** Add a short line on **Models** and **Notebooks** linking to approval-rate impact (e.g. “Models power approval, risk, routing, and retry decisions in Decisioning”).
7. **Embed dashboards:** The “Try native Databricks embed” details and fallback alert are clear; keep as-is for workspace admins who have not enabled embedding.

### 5.4 Manual test checklist (after 503 is fixed)

- [ ] Open app from Compute → Apps; confirm landing and “Open workspace” behavior when not from Apps.
- [ ] Navigate each sidebar section: Command Center, Dashboards, Decisioning, Declines, Reason Codes, Smart Checkout, Smart Retry, AI Agents, Models, Experiments, Rules, Notebooks, Data Quality, Setup, Initiatives, Profile, About.
- [ ] For each: page loads, no uncaught console errors, tables/charts either show data or clear empty/error state.
- [ ] Command Center: KPIs, charts, and AI chat trigger load or show explicit error/empty.
- [ ] Decisioning: Run presets, run auth/retry/routing decisions, run ML predictions; check recommendations and decision cards.
- [ ] Dashboards: “View in app” and “Open in new tab”; iframe embed vs. SQL fallback when embedding not allowed.
- [ ] Setup: Token/connection status and “Refresh job IDs” (with user auth enabled).
- [ ] Check browser console for 4xx/5xx or CORS errors on key API calls.

---

## 6. Summary

| Item | Status |
|------|--------|
| **Deployed URL** | 503 — app not reachable for testing |
| **Route structure** | Documented; redirects and error boundaries in place |
| **Approval-rate alignment** | Landing and main workflows (Command Center, Decisioning, Declines, Reason Codes, Smart Retry) support “accelerate approval rates” with clear KPIs and actions |
| **Error handling** | Error boundaries and inline retry on key pages; optional improvement: global health banner |
| **Loading/empty states** | Present; optional improvement: clearer “no data” vs “error” messaging |
| **Next step** | Fix 503, then run manual test checklist above and capture console/network issues for a follow-up QA pass |
