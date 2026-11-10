---
name: shadow-handover
description: Client Delivery, BAST (Berita Acara Serah Terima), Source-Code & Asset Inventory, Secure Credential Transfer, Admin Manual, Operator Manual, Deployment Runbook, User Training Package, and Warranty Checklist. Distinct from /handoff (which is AI agent session context transfer). Trigger with /shadow-handover.
---

# Shadow Handover (`/shadow-handover`) — Client System Delivery, BAST & Operational Independence

> [!IMPORTANT]
> **Distinction of Purpose**:
> - **`/handoff`** = Transfers AI agent session context when conversation memory is full.
> - **`/shadow-handover`** = Transfers the **completed software system, documentation, credentials, and operational ownership** to the client/employer so they can run and maintain the system independently.

---

## 1. The 7 Mandatory Client Handover Deliverables (Gate 8)

When preparing a project for final client handover / **BAST (Berita Acara Serah Terima)**, verify and generate all 7 packages (using `/shadow-doc` for `.docx`/`.xlsx`/`.pdf` outputs):

### 1. Berita Acara Serah Terima (BAST) & Deliverable Checklist
- Formal handover document mapping every contract scope item (KAK/TOR/SPK) to its verified deliverable artifact, UAT sign-off reference (`/shadow-uat`), and repository/archive location.

### 2. Source Code & Technical Asset Inventory
- Clean repository state (`git status` clean, release tag `v1.0.0` created, zero dead files or temporary debug scripts).
- Complete inventory table of:
  - Source code repositories (Frontend, Backend, Mobile, ETL/Warehouse scripts, Infrastructure/Docker configs).
  - Database schema (`schema.dbml`, `ERD.md`, migration files, and reference seed scripts from `/shadow-db` & `/shadow-data`).
  - API specifications (`openapi.yaml` and `postman_collection.json` from `/shadow-api`).
  - Third-party licenses & SBOM (Software Bill of Materials) confirming zero prohibited/unlicensed dependencies.

### 3. Secure Credential & Secret Transfer Protocol
- **NEVER put plain-text production passwords or private keys inside `.docx` reports, Git repos, or unencrypted emails/chats!**
- Deliver a **Credential Inventory Matrix** listing *what* credentials exist (Server SSH, DB Admin, DB Read-Only, Redis, S3/MinIO, SMTP, Payment Gateway, Domain/DNS, SSL) and *where* they are stored (Password Manager Vault / Encrypted `.kdbx` / Secret Manager), along with instructions for the client's IT team to rotate passwords upon receipt.

### 4. System Administrator & DevOps Runbook (`Buku Panduan Administrator / Teknis`)
Step-by-step copy-pasteable guide enabling a new sysadmin/developer to operate the system without the original author:
- Server topology, IP/Port matrix, and firewall rules.
- Fresh installation & deployment commands (`docker compose`, `systemd`, `nginx`, `.env.example` explanation).
- How to check service status, view logs, restart services, run database migrations, and trigger/restore backups (`/shadow-ops` & `/shadow-resilience`).
- Troubleshooting decision tree for common operational issues (`502 Bad Gateway`, disk full, expired SSL, locked user account).

### 5. End-User & Operator Manual (`Buku Panduan Pengguna / Manual Book`)
Task-oriented guide grouped by **User Role** (`Operator`, `Verifikator`, `Pimpinan`, `Admin`):
- Numbered step-by-step workflows accompanied by real annotated application screenshots (`bukti/*.png`).
- FAQ and common validation error explanations in plain Bahasa Indonesia.

### 6. Training & Knowledge Transfer (ToT) Package
- Training agenda, attendance/BA Pelatihan template, and hands-on training scenarios for Operators and IT Administrators.

### 7. Warranty / Masa Pemeliharaan (Garansi) Handover Checklist
- Support escalation contacts, SLA response tiers (`/shadow-maintain`), and scope boundaries distinguishing **Warranty Bug Fixes (Covered)** from **New Feature Requests (Out of Warranty Scope)**.
