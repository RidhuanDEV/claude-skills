# DATA-ANALYTICS-ML — Data Analyst, BI, Analytics Engineering (`dbt`) & Classical ML

Use when designing data warehouses, writing analytical SQL or `dbt` models, defining BI dashboard KPIs (Metabase,
Looker, Superset, PowerBI), running product experimentation (A/B testing), or building classical Machine Learning /
forecasting pipelines (`scikit-learn`, `XGBoost`, `LightGBM`, `PyTorch`). Pair with `DATA-AUTOMATION.md` for ETL ingestion.

## 1. Dimensional modeling & Data Warehouse architecture

Organize analytical data into three clear transformation layers (**Medallion / `dbt` convention**):
1. **Staging / Bronze (`stg_<source>__<entity>`)**: 1:1 with source tables. Rename columns to standard `snake_case`, cast
   types explicitly (`TIMESTAMPTZ`, `NUMERIC`), deduplicate raw ingestion events, no joins or business aggregations.
2. **Intermediate / Silver (`int_<domain>__<verb>`)**: reusable business logic joins, sessionization, currency conversion,
   and state stitching.
3. **Marts / Gold (`fct_<event>` & `dim_<entity>`)**: Star Schema consumed by BI tools:
   - **Fact tables (`fct_orders`, `fct_payments`)**: immutable or accumulating business events at a declared **grain**
     (e.g., "one row per order line item"). Always state the grain in the model's header/description.
   - **Dimension tables (`dim_customers`, `dim_products`)**: descriptive attributes (`surrogate_key`, natural key, status).
     Use **Slowly Changing Dimension Type 2 (SCD2)** (`valid_from`, `valid_to`, `is_current`) when historical attribute
     accuracy matters (e.g., customer tier or product price at the time of order).

## 2. `dbt` & Analytical SQL authoring rules

- **Explicit grain & uniqueness tests**: every `dbt` model must declare `unique` and `not_null` schema tests on its primary
  grain key, plus `accepted_values` and `relationships` on foreign keys in `schema.yml`.
- **Readable CTE pipeline**: structure analytical SQL as sequential, well-named CTEs (`WITH source_data AS (...), filtered AS (...), aggregated AS (...) SELECT * FROM final`) rather than deeply nested subqueries.
- **Safe aggregations & joins**:
  - Guard against **fan-out joins** (joining a `1:N` table before summing a fact measure inflates totals). Aggregate the `N`
    side to the `1` grain *before* joining.
  - Handle division by zero with `NULLIF(denominator, 0)` and null sums with `COALESCE(SUM(amount), 0)`.
  - Use explicit `DATE_TRUNC('day', created_at AT TIME ZONE 'Asia/Jakarta')` so daily/monthly reports align with the
    business's reporting timezone rather than UTC midnight.
- **Incremental models**: always include a lookback window (e.g., `WHERE updated_at >= (SELECT MAX(updated_at) - INTERVAL '3 days' FROM {{ this }})`) with `unique_key` upsert to catch late-arriving data.

## 3. BI dashboards & metric governance (Data Analyst)

- **Single source of truth for KPIs**: define core metrics (`GMV`, `Net Revenue`, `Active User`, `Churn Rate`, `Conversion Rate`)
  in the semantic layer / `dbt` mart, never as ad-hoc formulas copy-pasted across 20 dashboard cards.
- **Every metric definition must specify**:
  - Exact numerator & denominator formula.
  - Inclusion/exclusion filters (e.g., exclude test accounts, refunded/cancelled orders, internal staff).
  - Time dimension (`created_at` vs `paid_at` vs `settled_at` — mixing these causes finance vs product discrepancies).
- **Cohort, funnel & retention analysis**:
  - Guard against **survivorship bias** and **right-censoring** (exclude users who joined less than $N$ days ago when
    calculating Day-$N$ retention).
  - Report median (`p50`) and `p90`/`p95` alongside averages whenever distributions are skewed (order value, latency, session duration).

## 4. Classical Machine Learning & Data Science pipelines

- **Zero data leakage (non-negotiable)**:
  - Split data (`train / validation / test`) **before** fitting any scaler, imputer, target encoder, or feature selector.
  - For time-series / forecasting / fraud / churn, always use **temporal splits** (train on past, validate on future),
    never random `train_test_split`, and never include features updated *after* the prediction timestamp (`updated_at`,
    future status columns).
- **Baseline first**: always compare a complex model against a simple heuristic or linear baseline (`DummyClassifier`,
  `LogisticRegression`, moving average) on the exact same validation split.
- **Evaluation aligned with class imbalance & business cost**:
  - Never use raw `Accuracy` on imbalanced datasets (fraud, churn, rare disease). Use **PR-AUC**, **ROC-AUC**,
    **F1 / Precision@K / Recall@K**, and calibrate probability thresholds against business cost of False Positives vs False Negatives.
- **Reproducibility & serving**: fix random seeds, version dataset snapshots + feature pipelines (`scikit-learn` `Pipeline` /
  `ColumnTransformer`), validate input feature schemas at inference time, and monitor **feature drift / prediction distribution shift** in production.

## 5. Anti-patterns

Summing revenue after a `1:N` join (double counting) · mixing `created_at` and `paid_at` across reports · using `SELECT *` in
production `dbt` marts · random train/test split on time-series data · fitting `StandardScaler` on the full dataset before
splitting · deploying an ML model with no schema validation or fallback heuristic when features are missing.
