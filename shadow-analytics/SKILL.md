---
name: shadow-analytics
description: "Product Analytics & Experimentation Specialist. Use when designing North Star/OEC metrics, event tracking plans, identity resolution, UU PDP/GDPR multi-vendor DSAR consent, PostHog/GA4/Mixpanel hybrid instrumentation, warehouse modeling, data quality, funnels, retention cohorts, behavioral segmentation, A/B tests (SRM, CUPED, Delta Method, mSPRT, switchbacks), causal inference (DiD/SCM/RDD), or ship decisions. Do NOT use for OTel/infra SRE (/shadow-observe) or SEO (/shadow-seo)."
---

# Shadow Analytics (`/shadow-analytics`) — Product Analytics & Experimentation Engineering

Use this skill whenever the **Monarch** designs KPI frameworks, tracking plans, identity graphs, privacy-compliant analytics pipelines, funnel/retention/behavioral analyses, A/B experiments, quasi-experimental causal studies, or executive ship decisions.

## 1. Core Engineering Principles & Non-Negotiables

1. **Metric & Contract Rigor:** Anchor decisions on a value-driven North Star Metric, OEC, and blocking guardrails. Enforce `Object_Action` event naming, `schema_version`, zero raw PII, and **occurrence-unique retry-stable `event_id` (`UUIDv7`)** on repeatable events (deterministic entity keys apply strictly to once-per-entity domain transitions).
2. **Truthful Instrumentation & End-to-End Privacy:** Use server-side events as the source of truth for revenue/billing, pair with consented first-party client telemetry, rotate `anonymous_id` (`reset()`) on logout/shared kiosks, and orchestrate **multi-vendor DSAR deletion** across BOTH the warehouse and third-party vendors (PostHog/GA4/Mixpanel/ESP) — deleting only `analytics_identity_map` is non-compliant.
3. **Hard Randomization & SRM Gate:** Always separate **Assignment (ITT)** from **Exposure** (triggered identically across Control and Treatment). Compute Pearson chi-square SRM at `alpha = 0.001`; **BLOCK shipping (`BLOCKED_SRM`) whenever `srm_p < 0.001` regardless of positive lift (`e.g. +12%, p = 0.02`)**.
4. **Statistical & Causal Precision:** Match estimator to metric structure (Z-test for user proportions, Welch's t-test for continuous, **Delta Method / cluster bootstrap** for ratio metrics, cluster-robust SE for clusters, **mSPRT / Group Sequential** for peeking, Holm-Bonferroni vs Benjamini-Hochberg FDR). CUPED covariates MUST be strictly **pre-experiment** (`< assignment_ts`). Use **DiD / Synthetic Control / RDD / AIPW** with falsification checks when RCTs are infeasible.
5. **Cross-Skill Boundaries:** Delegate backend logging/Prometheus/OTel SRE to `/shadow-observe`, OLTP DB migrations/RLS to `/shadow-db`/`/shadow-data`, UU PDP legal/DPIA governance to `/shadow-privacy`, and search visibility/CrUX SEO to `/shadow-seo`.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-analytics/scripts/analytics_experiment_verifier.py" --self-test
python "shadow-analytics/scripts/analytics_experiment_verifier.py" --check-event path/to/event.json
python "shadow-analytics/scripts/analytics_experiment_verifier.py" --check-experiment path/to/experiment.json
python "shadow-analytics/scripts/analytics_experiment_verifier.py" --check-dsar-plan path/to/dsar_plan.json
python -m unittest discover -s "shadow-analytics/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (13 scenarios including the SRM `p = 0.0002` vs `+12% lift, p = 0.02` ship-gate benchmark, ratio Delta Method, CUPED leakage, mSPRT peeking, marketplace switchbacks, DiD parallel trends, and multi-vendor DSAR).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 15 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| North Star Metric, OEC, metric trees, anti-Goodhart guardrails & metric governance | CORE | [references/01-product-metrics-and-kpi-design.md](references/01-product-metrics-and-kpi-design.md) |
| `Object_Action` taxonomy, typed contracts, occurrence-unique retry-stable `event_id`, versioning | CORE | [references/02-event-taxonomy-and-tracking-plans.md](references/02-event-taxonomy-and-tracking-plans.md) |
| `anonymous_id -> identify -> reset()`, cross-device stitching, sessions, shared-kiosk protection | CORE | [references/03-identity-resolution.md](references/03-identity-resolution.md) |
| UU PDP / GDPR consent gate, PII scrubbing, retention TTLs & multi-vendor DSAR orchestration | CORE | [references/04-privacy-and-consent-architecture.md](references/04-privacy-and-consent-architecture.md) |
| Hybrid client/server SDKs, first-party `/ingest` proxy, `sendBeacon`, PostHog/GA4/Mixpanel, bots | CORE | [references/05-analytics-instrumentation.md](references/05-analytics-instrumentation.md) |
| Raw/Silver/Gold warehouse modeling, clock-skew clamping, late-arriving mobile events, dedup | ADVANCED | [references/06-analytics-data-architecture.md](references/06-analytics-data-architecture.md) |
| Schema validation quarantine/DLQ, freshness/completeness SLAs, volume anomaly & CI contract gates | OPERATIONAL | [references/07-data-quality-and-observability.md](references/07-data-quality-and-observability.md) |
| Strict ordered vs unordered funnels, conversion windows, right-censoring & Simpson's paradox | CORE | [references/08-funnel-and-conversion-analytics.md](references/08-funnel-and-conversion-analytics.md) |
| Activation, N-day vs bracket vs unbounded retention SQL, cohort masking & lifecycle Quick Ratio | CORE | [references/09-retention-and-cohort-analysis.md](references/09-retention-and-cohort-analysis.md) |
| `L7/L28` power-user curves, journey/path SQL, behavioral cohorts & RFM applicability limits | ADVANCED | [references/10-behavioral-and-segmentation-analytics.md](references/10-behavioral-and-segmentation-analytics.md) |
| Salted bucketing, Assignment vs Exposure (ITT/LATE), A/A tests, SRM taxonomy & exclusion layers | CORE | [references/11-experiment-design-and-randomization.md](references/11-experiment-design-and-randomization.md) |
| Power/MDE, Estimator Matrix, Welch's t, **Delta Method**, valid pre-experiment CUPED, FWER/FDR | ADVANCED | [references/12-statistical-inference.md](references/12-statistical-inference.md) |
| Sequential testing (**mSPRT** / O'Brien-Fleming GST), cluster randomization & marketplace switchbacks | SPECIALIST | [references/13-advanced-experimentation.md](references/13-advanced-experimentation.md) |
| Quasi-experiments: Difference-in-Differences (DiD), Synthetic Control, PSM/AIPW, RDD & falsification | SPECIALIST | [references/14-causal-inference.md](references/14-causal-inference.md) |
| 4-gate Ship/Iterate/Rollback Decision Records, CI reading, novelty decay, holdouts & flag cleanup | OPERATIONAL | [references/15-decision-science-and-reporting.md](references/15-decision-science-and-reporting.md) |

Do not load unrelated references unnecessarily.
