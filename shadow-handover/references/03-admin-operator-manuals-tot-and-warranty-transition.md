# 03. Admin/Operator/User Manuals, Hands-On ToT & Warranty Transition

## 1. Purpose & Activation Conditions
Use this playbook when authoring role-based **Administrator Runbooks** and **End-User Manuals**, designing and verifying **Training of Trainers (ToT)** operator readiness drills, and establishing a crisp **Warranty / Masa Pemeliharaan (Garansi / Harwat)** boundary transitioning operations cleanly to `/shadow-maintain`.

Activate this playbook when:
- Writing `Buku Panduan Administrator / Teknis` and `Buku Panduan Pengguna` (mapped to `/shadow-doc` `templates/16_MANUAL.md`).
- Running the mandatory pre-BAST operator walkthrough where the receiving IT team proves operational independence (`operator_demo_ref`).
- Defining Warranty SLA response tiers and separating covered Warranty Bug Fixes from out-of-warranty Paid Enhancements (`/shadow-pmo`).

## 2. Prerequisites
- Verified source/asset inventory and zero-plaintext Vault Cutover Manifest from [`01-bast-deliverable-inventory-and-receipt-verification.md`](01-bast-deliverable-inventory-and-receipt-verification.md) and [`02-zero-plaintext-vault-cutover-and-access-revocation.md`](02-zero-plaintext-vault-cutover-and-access-revocation.md).
- Working Staging environment seeded with realistic anonymized data for hands-on ToT exercises and clean annotated screenshots (`bukti/*.png`).

## 3. Technical Principles & Constraints
1. **Prove Operational Independence via Live Operator Drills (`operator_demo_ref`)**:
   - Reading slides is NOT knowledge transfer. Before signing final BAST, ask the receiving client administrator/operator to personally execute **4 hands-on drills** in Staging using ONLY the supplied Admin Runbook:
     1. **Clean Health & Log Triage**: Check service health, inspect structured JSON logs by `requestId`, and diagnose a simulated error.
     2. **Backup & Restore Drill**: Restore a backup snapshot from scratch and verify row counts + measured RTO (`/shadow-resilience`).
     3. **Secret Rotation & Safe Restart**: Rotate one non-production secret in the Vault and restart the app cleanly with zero errors.
     4. **Staging Rollback Drill**: Revert a candidate build or toggle a feature flag off safely.
   - Record the actual observed outcome, timestamp, operator name, and any runbook gaps fixed during the drill in `operator_demo_ref`.
2. **Role-Segmented Documentation (Never Mix Sysadmin & End-User Guides)**:
   - **Administrator / DevOps Runbook**: Server topology, IP/port/firewall matrix, clean-checkout setup, `.env.example` variable dictionary, migration/backup/restore commands, and a concrete troubleshooting decision tree (`502 Bad Gateway`, disk full, expired TLS, pool exhaustion, locked account).
   - **End-User & Operator Manual**: Grouped strictly by operational role (`Operator`, `Verifikator`, `Pimpinan`, `Admin`) in clear Bahasa Indonesia / user language with numbered workflows, real annotated screenshots, and plain-language explanations of common validation errors (zero developer stack jargon).
3. **Explicit Warranty (Garansi) vs Out-of-Scope Boundary**:
   - Define exact warranty duration (e.g., 90/180/365 calendar days post-BAST), support escalation contacts, severity SLA matrix (`P0`–`P3` aligned with `/shadow-maintain`), and an unambiguous table distinguishing **Covered Warranty Defects** (deviations from signed SRS/UAT baseline) vs **Out-of-Warranty Requests** (new modules, third-party API changes outside contract, client misconfiguration -> `/shadow-pmo`).
4. **Honest Punch-List Transfer**:
   - Any waived `Minor` (`SEV4`) UAT items remaining at BAST MUST be itemized in an explicit **Open Minor Punch-List** with target closure dates and handed directly into the `/shadow-maintain` backlog.

## 4. Architecture & Implementation
### Mandatory ToT Operator Readiness Drill Scorecard (`operator_demo_ref`)
| Drill ID | Hands-On Task Performed by Client Operator | Runbook Section Tested | Observed Outcome & Metric | Sign-Off |
| :--- | :--- | :--- | :--- | :--- |
| `TOT-01` | Inspect structured JSON logs by `requestId` & verify `/healthz` | Admin Manual §4 | Located simulated `422` & `500` traces in `3m` | `PASS` |
| `TOT-02` | Execute PostgreSQL backup restore to ephemeral Staging instance | Admin Manual §6 | Full restore verified; `RTO = 18m` (`<= 60m` target) | `PASS` |
| `TOT-03` | Rotate SMTP test secret in Vault & reload worker | Admin Manual §5 | Zero dropped jobs; new credential active | `PASS` |
| `TOT-04` | Execute controlled feature-flag disable / rollback in Staging | Admin Manual §7 | Previous behavior restored in `2m` | `PASS` |

### Troubleshooting Decision Tree Snippet (Admin Runbook Standard)
```markdown
### Symptom: Users Receive `502 Bad Gateway` from Nginx
1. Check reverse proxy & upstream status:
   `systemctl status nginx app-api` (or `docker compose ps`)
2. Inspect last 100 structured error lines:
   `journalctl -u app-api -n 100 --no-pager`
3. Decision Branch:
   - **Process exited with `EADDRINUSE` / OOMKilled (`137`)**: Check `dmesg -T | grep -i oom`, verify container memory limit, capture logs BEFORE restarting (`shadow-maintain`).
   - **Process healthy, DB timeout**: Verify PostgreSQL connections (`SELECT count(*) FROM pg_stat_activity;`) and disk space (`df -h`).
   - **TLS cert expired**: Check `openssl s_client -connect app.example.go.id:443 -servername app.example.go.id </dev/null 2>/dev/null | openssl x509 -noout -dates` and renew via Certbot/ACME.
```

### Warranty Scope & Escalation Matrix
| Ticket Category | Covered Under Warranty? | Target SLA & Handling Path |
| :--- | :--- | :--- |
| **Functional / security deviation from signed SRS/UAT baseline** | **YES (Warranty Defect)** | Handled under `/shadow-maintain` (`SEV1 < 15m` ack, `SEV2 < 30m` ack) |
| **Waived Minor (`SEV4`) punch-list item listed on BAST Annex** | **YES (Committed Punch-List)** | Closed within agreed post-BAST remediation window |
| **New report, new role, or uncontracted third-party integration** | **NO (Out of Warranty)** | Logged & routed to `/shadow-pmo` Paid CR governance |
| **Client-side OS/network outage or unapproved manual DB edits** | **NO (Best-Effort Support)** | Advisory assistance; formal incident remediation scoped separately |

## 5. Platform / Vendor Variations
- **Indonesian Public Sector (`BA Pelatihan` & `Manual Book`)**: Include formal **Berita Acara Pelatihan (ToT)** attendance list, role-specific training syllabus, and Bahasa Indonesia screenshots matching the live deployed UI labels cleanly (`templates/16_MANUAL.md`).
- **Automated Video Tutorials (`video-pipeline/` Present Only)**: If the target project maintains a `video-pipeline/` directory, synchronize narrated screen-recorded tutorials cleanly via `/shadow-video`; otherwise keep lightweight screenshot-annotated manuals in `/shadow-doc`.

## 6. Decision Matrix & Trade-Offs
| Knowledge Transfer Style | Operational Resilience | Time Cost | Verdict |
| :--- | :--- | :--- | :--- |
| **Hands-On Staging Drills + Role Manuals (`TOT-01..04`)** | Client can actually restore DB & triage outages independently | Half-day workshop | **Mandatory for BAST** |
| **Slide Deck Presentation Only** | Client remains dependent on vendor for every minor restart | 1–2 hours | **Insufficient — Reject as sole ToT proof** |

## 7. Real Production Scenario
**Context:** During a pre-BAST ToT workshop for a regional healthcare portal, the vendor's Admin Manual looked polished (`85 pages`). However, when the client sysadmin executed `TOT-02` (backup restore from the runbook), the restore script failed because it referenced an undocumented S3 bucket prefix and a hard-coded vendor IAM profile.
**Impact:** Catching and fixing both undocumented dependencies during the hands-on drill prevented a catastrophic inability to recover during a real outage 4 months later, and earned immediate trust from the client's IT director at BAST signing.

## 8. Failure Modes & Edge Cases
- **WRONG (Shipping stale screenshots from prototype builds & copy-pasted generic Linux commands never tested by the client):** Operators get stuck on Step 2 during real incidents and escalate every routine task back to the vendor.
  **RIGHT:** Capture annotated screenshots from the exact release candidate build and verify every runbook command via a hands-on client operator dry-run (`TOT-01..04`).
- **WRONG (Leaving Warranty vs New Enhancement boundaries vague on BAST):** Causes months of friction where clients demand free major features under "garansi".
  **RIGHT:** Attach an explicit Warranty Scope Matrix anchoring covered defects strictly to the signed SRS & `Berita Acara UAT` baseline.

## 9. Testing & Verification
- Verify `operator_demo_ref` documents all 4 executed Staging drills (`TOT-01..04`) with timestamps, observed RTO, and sign-off.
- Validate `16_MANUAL` and `17_HANDOVER` deliverables with `shadow-doc/scripts/doc_scaffold.py validate --doc <file.json> --strict` (zero unresolved `[TBD]` placeholders or leaked secrets).

## 10. Operational Considerations
- Conduct a brief formal **Warranty Kickoff Handoff** transferring the signed BAST annex, open minor punch-list, SLO dashboards (`/shadow-observe`), and escalation runbooks directly to the `/shadow-maintain` Harwat team.

## 11. Authoritative References
- **ISO/IEC/IEEE 26514:2022** — *Systems and software engineering — Design and development of information for users*.
- **Shadow Doc Templates** — `shadow-doc/templates/16_MANUAL.md` & `17_HANDOVER.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-handover` to execute post-launch `SEV1` incident triage or ongoing monthly Harwat cycles — transition live operations to `/shadow-maintain`.
- **Do NOT use** `/shadow-handover` for contractual Paid CR disputes after Go-Live — route to `/shadow-pmo`.
