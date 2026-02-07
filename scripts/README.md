# Scripts

| Script | Purpose |
|--------|---------|
| **bundle.sh** | Bundle validate, deploy, or verify. `./scripts/bundle.sh deploy dev` prepares dashboards then deploys; `validate` prepares then validates; `verify` runs build, backend smoke test, dashboard assets, and bundle validate. See [DEPLOYMENT](../docs/DEPLOYMENT.md). |
| **dashboards.py** | **prepare** — copies dashboard JSONs and gold_views.sql to `.build/` (invoked by bundle.sh). **validate-assets** — lists required tables/views for dashboards. **publish** — optional: publish all 12 dashboards with embed credentials. See [TECHNICAL](../docs/TECHNICAL.md). |

Run from repo root. Use `uv run python scripts/dashboards.py` for the Python script.
