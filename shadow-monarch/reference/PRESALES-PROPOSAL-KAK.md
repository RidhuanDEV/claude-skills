# PRESALES-PROPOSAL-KAK — Solutions Consultant, Technical Pre-Sales, TOR/KAK & Server/BoQ Sizing

Use when preparing Technical Proposals, Terms of Reference (TOR) / Kerangka Acuan Kerja (KAK), Bill of Quantities (BoQ) /
RAB IT, Hardware & Cloud Server Sizing calculations, RFP responses, or Proof of Concept (PoC) plans for enterprise and
government projects. Pair with `ARCHITECTURE.md` and `DOCS-PIPELINE.md`.

## 1. TOR / KAK (Kerangka Acuan Kerja) & Technical Proposal structure

Structure formal technical proposals and KAK documents clearly:
1. **Latar Belakang & Tujuan (Background & Objectives)**: current pain points, regulatory/business drivers, measurable
   target outcomes, and alignment with organizational roadmap (e.g., SPBE / Enterprise Architecture).
2. **Ruang Lingkup Pekerjaan (Scope of Work)**:
   - Explicit deliverables per module/phase, user roles covered, integration points (SSO, payment, existing ERP/APIs).
   - **Batasan Pekerjaan (Out of Scope / Assumptions)**: state clearly who provides server infrastructure, third-party
     licenses, SSL certificates, SMS/WhatsApp gateway credits, and legacy data cleansing.
3. **Metodologi & Arsitektur Solusi (Solution Architecture)**:
   - High-level architecture diagram, network & security topology (DMZ vs Private App Zone vs DB Zone), tech stack
     justification, and compliance alignment (UU PDP, ISO 27001, TKDN where applicable).
4. **Jadwal Pelaksanaan & Komposisi Tenaga Ahli (Timeline, WBS & Team Composition)**:
   - Milestone table (`Bulan/Minggu`, `Tahapan`, `Deliverable / Bukti Serah Terima (BAST)`).
   - Tenaga Ahli matrix (`Posisi / Role`, `Kualifikasi Pendidikan/Sertifikasi`, `Pengalaman (Tahun)`, `Jumlah Orang-Bulan (Man-Months)`, `Tanggung Jawab`).
5. **Garansi, Pemeliharaan & Transfer Knowledge (Warranty, SLA & Training)**:
   - Hypercare/warranty period (e.g., 3–12 months bug-fix warranty vs paid CRs), training sessions (Admin, Operator, Technical/DevOps), and full documentation handoff.

## 2. Server Sizing & Capacity Estimation formulas

Never guess server specs without showing the calculation from workload assumptions:
- **Step 1 — Concurrency & RPS (Requests Per Second)**:
  - Given Total Registered Users ($U$), Daily Active Users ($DAU$), Peak Hour Traffic Ratio ($\approx 15\%\text{--}25\%$ of daily requests), and Average Actions per Session ($A$):
    $$\text{Average Peak RPS} = \frac{DAU \times A \times \text{Peak Hour Ratio}}{3600}, \quad \text{Design Peak RPS} = \text{Average Peak RPS} \times \text{Safety Multiplier } (2\times\text{--}3\times)$$
- **Step 2 — Application Server (vCPU & RAM)**:
  - If average handler CPU time is $t_{\text{cpu}}$ seconds (e.g., $15\text{ ms} = 0.015\text{ s}$) and target max CPU utilization is $60\%$:
    $$\text{vCPU Core Count} = \left\lceil \frac{\text{Design Peak RPS} \times t_{\text{cpu}}}{0.60} \right\rceil$$
  - Minimum HA baseline: $\ge 2$ app instances behind a load balancer (`2–4 vCPU, 4–8 GB RAM` per instance for standard stateless web APIs; scale up for JVM/ML workloads).
- **Step 3 — Database Sizing (vCPU, RAM, IOPS, Storage)**:
  - **RAM**: size to hold the active working set + indexes in memory ($\approx 20\%\text{--}30\%$ of hot table/index size, minimum `8–32 GB` for production OLTP).
  - **Storage ($S$)**:
    $$S_{\text{total}} = \left(\text{Row Size} \times \text{Rows/Year} \times \text{Retention Years} \times (1 + \text{Index Overhead } 0.35) \times (1 + \text{WAL/Temp/Headroom } 0.30)\right)$$
  - Separate calculation for **Object Storage (S3/MinIO)** based on average uploaded file size $\times$ documents/day $\times$ retention years.

## 3. BoQ (Bill of Quantities) & RAB IT authoring rules

Divide cost tables into transparent categories:
1. **Biaya Tenaga Ahli (Personnel / Man-Month Rate)**: `Role | Jumlah Orang | Durasi (Bulan) | Rate per OB | Subtotal`.
2. **Biaya Infrastruktur & Lisensi (CAPEX / OPEX per Tahun)**: Compute (Prod + Staging), Managed DB (HA/Replica), Object Storage, Backup Storage, WAF/CDN, Domain/SSL, Monitoring/APM.
3. **Biaya Kegiatan Pendukung (Non-Personnel)**: Penetration Testing (VAPT independent), UAT Workshop, Training & Socialization, Documentation printing/handoff.
- Always state whether prices include or exclude **PPN (11%/12%)** and clarify recurring annual OPEX vs one-time build CAPEX.

## 4. Proof of Concept (PoC) & RFP Evaluation Matrix

- **PoC Charter**: max 2–4 weeks, 3–5 measurable success criteria, representative sample dataset, explicit pass/fail sign-off.
- **Vendor / Technology Scoring Matrix**: weighted table (`Functional Fit 35%`, `Architecture & Security 25%`, `Total Cost of Ownership (3-Yr TCO) 20%`, `Local Support & SLA 10%`, `Track Record 10%`).
