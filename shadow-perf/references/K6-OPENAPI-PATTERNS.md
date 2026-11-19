# k6 workload design from an existing API contract

## Decision and inputs

Identify the decision owner and one question per candidate scenario. A smoke probe establishes that a business journey works. A load experiment estimates performance at a chosen demand. A spike study investigates overload and recovery. A soak study targets a time-dependent failure. Choose scope after identifying the failure mode, expected amplitude, observation window and cleanup cost. Local dry-run fixtures validate wiring across steps. Timing an in-memory fixture cannot establish service latency.

## Building the journey

1. Record the authoritative API revision, the installed client/runtime versions, data revision, route/method, expected status, response fields, auth scope and state prerequisites. Resolve generated routes through their project generator. A duplicate copy of the OpenAPI spec can drift from the service.
2. A successful order journey typically starts with a test identity, creates an order, obtains its ID, then reads or changes that specific resource. Supply request data as synthetic fixtures. One captured ID per iteration prevents another user's resource from silently becoming the target. Follow tenant boundaries and use a per-run prefix or owned disposable store for write cleanup.
3. Use the operation's exact agreed success response. A 401, 403 or 404 can be a correct result in a dedicated negative test and a broken journey in a success scenario. Validate response semantics, such as a created resource ID, cursor continuity, or echoed tenant, according to the contract. Include only bounded operation names as metric labels.
4. Give each script an explicit origin. Apply a verified environment allowlist before running anything, disable cross-origin redirects that could forward credentials, and keep tokens outside generated artifacts. Supply credential lifecycle and fixture adapters from the project when the offline compiler does not support them.
5. Derive traffic mix from traces or an explicit business estimate. Maintain separate state and datasets for independent scenarios. For an arrival-rate experiment, report target/achieved arrivals, dropped starts and completed iterations. For closed-loop concurrency, record active users, think time and completions. Slow responses can lower offered traffic in a closed-loop experiment.
6. Estimate requests, resource consumption and data writes before proposing execution. Agree on stop signals, e.g. sustained lag, error rate above the project budget or a data isolation failure. Define who can stop the test and who owns recovery. Gate approval covers a target, workload, time window, data and side effects.

## Reading results

Compare on the same release/config, dataset, cache regime, workload and warm-up policy. If an old release carries a different workload mix, break down scenario and cohort before interpreting aggregate percentiles. Never average p95 readings to infer an overall p95. State sampling windows, successful sample counts, timeouts, excluded retries and variance.

Client-observed delay includes generator scheduling and transport. Compare generator CPU/network budget and achieved arrivals to application timing and service utilization. A high client p95 with saturated generator, low achieved rate and healthy service timing suggests generator pressure. High server p95 with server resources exhausted and a healthy generator supports a service hypothesis. Multiple simultaneous pressures call for a discriminating follow-up experiment, and missing observations restrict the diagnosis. [Stored-window analyzer](../scripts/diagnose_window.mjs)

## Minimal handoff

Send the exact spec, fixture and script revisions; requested versus measured load; data, auth and cleanup owners; target and stop conditions; aggregate plus scenario results; confidence and gaps. Flag operations omitted because setup, authorization or test evidence is unavailable. The generator's three profile filenames are templates for this process. They carry one local iteration until an authorized performance engineer configures an actual workload.
