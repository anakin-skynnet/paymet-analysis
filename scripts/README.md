# Scripts

- **validate_bundle.sh** — Run before validate/deploy when using **prod** catalog/schema in dashboards: runs `prepare_dashboards.py` with optional `--catalog`/`--schema`, then `databricks bundle validate -t <target>`. For **dev**, dashboard JSONs are read from `src/payment_analysis/dashboards/`, so `databricks bundle validate -t dev` and `databricks bundle deploy -t dev` work without this script.
- **prepare_dashboards.py** — **Run-once (or per prod deploy):** copies dashboard JSONs to `.build/dashboards/` and optionally substitutes catalog/schema for the target. Use for prod when dashboard datasets must point at a different catalog/schema. Dev uses source files in `src/payment_analysis/dashboards/` directly.

Both scripts are kept; neither is redundant. Use `validate_bundle.sh` for prod or when you want prepare+validate in one step.
