# Asynchronous services and human-AI UX
## Async
Distinguish request accepted, queued, processing, partially complete, complete, retryable failure, terminal failure, cancelled. HTTP 202 typically signals acceptance, not completed processing. Design polling/websocket/push fallback and page-leave behavior if implementation supports them; never claim a notification exists unless it does. Define retry semantics, idempotence, timeouts, duplicate actions, partial effects, stale caches, role/session changes, and truthful progress (avoid fabricated percentages).

## Human-AI interaction
Represent model limitations, sources and citations when available, answer uncertainty, missing context, model/tool status, streaming/abort/retry, cost/time visibility if significant, correction/report feedback, and human review before high-impact external action. Separate user content and retrieved untrusted content from system instructions. Never imply the AI validated a source merely by generating a citation marker.

## AI failure scenarios
Hallucinated facts; unsafe/conflicting retrieved documents; tool denied or unavailable; truncated/incomplete generation; streaming disconnected; no source match; corrupted uploaded file; malicious prompt embedded in documents; stale embeddings and delayed indexing; overconfident summaries. UX should communicate evidence and enable recovery without exposing internal secrets.
