# Realtime Protocol ADR, Disconnect Load & Runbook Template

```yaml
record_id: "RT-0001"
protocol: "SSE" # WS | SSE | POLLING
supports_cursor_resume: true
cursor_window_minutes: 10
enforces_token_revocation_mid_stream: true
has_bounded_slow_consumer_queue: true
uses_shared_pubsub_broker: true
reconnect_backoff_has_jitter: true
events:
  - { stream: "orders:tenant_a", seq: 101, tenant_id: "tenant_a" }
  - { stream: "orders:tenant_a", seq: 101, tenant_id: "tenant_a" } # duplicate test
  - { stream: "orders:tenant_a", seq: 102, tenant_id: "tenant_a", after_revocation: true }
```
