# ENTERPRISE-INTEGRATION — Message Brokers, Enterprise IAM/SSO, API Gateways & ERP/Payment Ledger

Use when integrating distributed enterprise systems, configuring message brokers (Kafka, RabbitMQ, Redis Streams),
implementing Enterprise SSO/IAM (Keycloak, OAuth2/OIDC, SAML 2.0, LDAP), designing B2B webhooks/API gateways, or
building financial/ERP ledgers and settlement reconciliation pipelines.

## 1. Message Brokers: Kafka, RabbitMQ & Redis Streams rules

- **Pick the right broker for the pattern**:
  - **RabbitMQ / BullMQ / SQS**: task distribution, background job queues, flexible routing, per-message ack/retry/DLQ.
  - **Apache Kafka / Redpanda**: high-throughput event streaming, durable log replay, multiple independent consumer groups
    reading the same event stream.
- **Event contract & naming discipline**:
  - Topic/exchange naming: `<domain>.<entity>.<event>.v<major>` (e.g., `billing.invoice.paid.v1`).
  - Every event envelope includes: `event_id` (UUIDv4/v7), `event_type`, `event_version`, `occurred_at` (ISO-8601 UTC),
    `producer`, `correlation_id` / `trace_id`, `tenant_id`, and `data` (typed payload).
  - **Schema evolution**: additive, optional fields only within `v1`. Never rename or change the type of an existing field
    without publishing a new major version (`v2`) or dual-writing during transition.
- **Kafka partitioning & consumer rules**:
  - Partition key MUST be the entity whose ordering matters (e.g., `order_id` or `account_id` so all events for one order
    land on the same partition in order).
  - Commit offsets **only after** the consumer has durably processed or persisted the message (`enable.auto.commit = false`
    or manual ack).
- **Transactional Outbox & Idempotent Consumer**:
  - Never publish to Kafka/RabbitMQ inside the middle of an uncommitted DB transaction (dual-write bug). Write the event
    to an `outbox_events` table in the same DB transaction, then relay asynchronously (polling worker or CDC/Debezium).
  - Every consumer tracks processed `event_id`s in an `inbox_processed_events` table (`UNIQUE (consumer_name, event_id)`)
    so redeliveries are safely ignored.

## 2. Enterprise Identity & Access Management (Keycloak, OIDC, OAuth2, SAML, LDAP)

- **OAuth 2.1 / OpenID Connect (OIDC)**:
  - Use **Authorization Code Flow with PKCE (`S256`)** for all browser, SPA, and mobile clients — never Implicit Flow or
    Resource Owner Password Credentials (ROPC).
  - Use **Client Credentials Flow** for machine-to-machine (M2M) service calls with short-lived access tokens.
  - Validate JWTs against the IdP's JWKS endpoint (cached with key-rotation support on unknown `kid`), and strictly check
    `iss` (issuer), `aud` (audience), `exp` (expiration), and `alg` allowlist (`RS256`/`ES256`/`EdDSA`).
- **SAML 2.0 & LDAP / Active Directory**:
  - SAML: enforce XML Signature verification against pinned IdP X.509 certificates, prevent XML External Entity (XXE) and
    XML Signature Wrapping (XSW) attacks, validate `InResponseTo`, `Recipient`, `Audience`, and `NotOnOrAfter`.
  - Map external IdP groups/claims to internal application roles at login via an explicit mapping table; handle immediate
    session revocation when an employee is deactivated in the IdP (SCIM provisioning or short access-token TTL + backchannel logout).

## 3. B2B Webhooks & API Gateways (Kong / Traefik / Envoy)

- **Sending webhooks to partners**:
  - Sign raw request bodies with `HMAC-SHA256(secret, timestamp + "." + raw_body)` in header `X-Webhook-Signature` and
    `X-Webhook-Timestamp`. Support dual active secrets for zero-downtime key rotation.
  - Retry non-2xx responses with exponential backoff (up to 24–72h) and surface delivery logs + manual replay to partners.
- **Receiving webhooks**:
  - Verify HMAC signature using **constant-time comparison** against the **raw unparsed body** and reject timestamps older
    than 5 minutes (replay protection).
  - Deduplicate by provider `event_id`, store raw payload, return `200 OK` quickly, and process heavy work asynchronously.

## 4. ERP, Core Banking & Payment Reconciliation patterns

- **Double-entry immutable ledger** for money/wallet/inventory:
  - Never `UPDATE accounts SET balance = balance - 100` without an immutable `journal_entries` / `ledger_postings` trail
    where `SUM(debits) == SUM(credits)` per transaction.
  - Use `SELECT ... FOR UPDATE` (or optimistic version locking) in a repeatable/consistent order of `account_id`s to prevent deadlocks.
- **Three-way payment reconciliation (H+0 / H+1 Settlement)**:
  - Reconcile **Internal Order State** ↔ **Payment Gateway Webhook/Status** ↔ **Bank Settlement File (CSV/MT940/CAMT.053)**.
  - Flag mismatches into explicit states (`MATCHED`, `AMOUNT_MISMATCH`, `MISSING_IN_INTERNAL`, `MISSING_IN_SETTLEMENT`)
    for finance review; never auto-write-off financial discrepancies silently.

## 5. Anti-patterns

Publishing to Kafka before `COMMIT` (phantom events on DB rollback) · random partition keys breaking entity event order ·
storing money as mutable floats without ledger entries · trusting webhook payloads without raw-body HMAC + timestamp check ·
accepting JWTs without verifying `aud` and `iss`.
