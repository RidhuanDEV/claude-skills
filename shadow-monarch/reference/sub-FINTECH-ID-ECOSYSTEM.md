# sub-FINTECH-ID-ECOSYSTEM — SNAP BI, TTE BSrE/e-Meterai, SatuSehat FHIR/BPJS, Tax & Inventory Rules

Use when integrating Indonesian payment/banking APIs (SNAP BI, QRIS, Virtual Account, Disbursement), Digital Signatures
(TTE BSrE / PSrE: Privy, Vida, Peruri) & e-Meterai, Healthcare bridging (SatuSehat HL7 FHIR, BPJS VClaim/Antrean), or
implementing Indonesian tax (PPN, PPh) and e-commerce inventory reservation state machines.

## 1. SNAP BI (Standar Nasional Open API Pembayaran Bank Indonesia) rules

- **Authentication & Signature two-step flow**:
  1. **Access Token B2B (`/openapi/v1.0/access-token/b2b`)**:
     - String to sign: `<Client_ID>|<X-TIMESTAMP>` (ISO-8601 with timezone offset, e.g., `2026-10-18T21:00:00+07:00`).
     - Sign with partner's **RSA-2048 Private Key (`SHA256withRSA`)**, encode Base64 in `X-SIGNATURE`.
  2. **Transactional Service Call (VA, QRIS, Transfer/Disbursement)**:
     - Minify the JSON request body (no extra whitespace), compute lowercase hex `SHA-256(minified_body)`.
     - String to sign: `<HTTP_METHOD>:<RELATIVE_PATH>:<ACCESS_TOKEN>:<LOWERCASE_HEX_SHA256_BODY>:<X-TIMESTAMP>`.
     - Compute `HMAC-SHA512(client_secret, string_to_sign)` encoded as Base64 in `X-SIGNATURE`.
- **Mandatory headers & idempotency**:
  - `Authorization: Bearer <token>`, `X-TIMESTAMP`, `X-PARTNER-ID`, `X-EXTERNAL-ID` (unique numeric/string reference per
    calendar day — enforces idempotency; never reuse `X-EXTERNAL-ID` on the same day for a different transaction), `CHANNEL-ID`.
- **Status inquiry before retry**: if a Transfer/Disbursement call times out (`504` / network error), **NEVER blindly retry
  the transfer with a new `X-EXTERNAL-ID`**. Always call the **Transaction Status Inquiry** endpoint first to check whether
  the bank already processed it.

## 2. TTE (Tanda Tangan Elektronik BSrE / PSrE) & e-Meterai rules

- **PDF Signing (PAdES / BSrE / Privy / Vida / Peruri)**:
  - Never modify a PDF's byte stream after a cryptographic signature is applied (invalidates the earlier signature). For
    multi-signer workflows, use **PDF Incremental Updates** or sequential signing via the PSrE API.
  - Anchor tag placement: place unique invisible or replaceable anchor strings (e.g., `$tte_approver_1$` or `#emeterai_box#`)
    in the source template so the generator/PSrE places the QR code or e-Meterai stamp at exact coordinates without overlapping text.
  - Store the signed PDF in immutable object storage alongside its SHA-256 checksum, signer NIK/certificate serial, and signing timestamp.
- **e-Meterai (Peruri) serial allocation**:
  - Requesting a serial number (`SN`) consumes quota/balance immediately. Persist the returned `SN` and stamp image in a durable
    DB transaction *before* stamping the PDF so failed PDF renders can retry stamping with the **same already-allocated `SN`**.

## 3. Healthcare Bridging: BPJS (VClaim / Antrean / PCare) & SatuSehat (HL7 FHIR R4)

- **BPJS TrustMark / VClaim / Antrean signature & decryption**:
  - Headers: `X-cons-id`, `X-timestamp` (Unix epoch seconds in UTC: $\text{floor}(\text{now\_ms}/1000)$),
    `X-signature` ($\text{Base64}(\text{HMAC-SHA256}(\text{consId} + "\&" + \text{timestamp}, \text{secretKey}))$), `user_key`.
  - Response payload decryption: key = `SHA256(consId + secretKey + timestamp)` (32 bytes), IV = first 16 bytes of key,
    decrypt `AES-256-CBC`, then decompress with **`LZString.decompressFromEncodedURIComponent`**.
- **Kemenkes SatuSehat (HL7 FHIR R4)**:
  - Map internal master data to standard terminologies: **IHS Number** (`Patient`, `Practitioner`), **ICD-10** (`Condition`),
    **ICD-9-CM** (`Procedure`), **LOINC** (`Observation`), **KFA — Kamus Farmasi & Alat Kesehatan** (`Medication`).
  - Send resources in causal order (`Encounter` created first → obtain `Encounter.id` → attach to `Condition`, `Observation`, `MedicationRequest`).

## 4. Indonesian Tax (PPN & PPh) & E-Commerce Inventory State Machine

- **Tax calculation & rounding**:
  - Calculate **DPP (Dasar Pengenaan Pajak)**, **PPN** (support configurable effective rate / DPP Nilai Lain `11/12 × 12%` per regulation effective date), and **PPh 21 / PPh 23 (2%)** using exact `Decimal` or integer Rupiah — never float math.
  - Apply a single consistent rounding policy (`ROUND_HALF_UP` or `FLOOR` per DJP e-Faktur rules) at the line-item and invoice summary level so `SUM(line_totals)` matches header total.
- **Inventory Reservation State Machine**:
  - Track three explicit stock buckets per SKU: `on_hand`, `reserved` (locked at checkout with TTL, e.g., 15m), and `available = on_hand - reserved`.
  - Transitions: `Checkout → reserve stock (atomic WHERE available >= qty)` · `Payment Success → deduct on_hand & reserved` · `Payment Expired/Cancelled → release reserved back to available`.
