# 01. Search Engine Selection & Indonesian/Multilingual Analyzers

## 1. Purpose & Activation Conditions
Choose the right-sized search engine for corpus scale and query latency, and design accurate lexical analyzers (BM25, Indonesian affix stemming, exact keyword sub-fields, typo fuzziness, and domain synonyms) that excel on exact IDs/regulations as well as natural language. Load when choosing search infrastructure or tuning lexical recall/precision.

## 2. Prerequisites
- Corpus volume estimate, query task mix (exact SKU/pasal lookup vs autocomplete vs semantic Q&A), and multi-tenant isolation model (`03`).

## 3. Technical Principles & Constraints
- **Right-Sized Engine Selection (Avoid Unnecessary Cluster Ops!):**
  - **`< 1M` docs, already on PostgreSQL:** Use **PostgreSQL (`tsvector`/GIN + `pg_trgm` + `pgvector` HNSW)** — zero extra cluster to maintain and atomic transactional consistency with OLTP tables!
  - **Instant Typo-Tolerant Autocomplete (`< 20M` docs):** **Meilisearch** or **Typesense** (out-of-the-box prefix/typo ranking + tenant-scoped API keys).
  - **Enterprise Search, Custom Analyzers, Complex Facets (`> 10M` docs):** **OpenSearch** or **Elasticsearch** (zero-downtime aliases, PIT + `search_after`).
  - **High-Scale Dense/Sparse Vector ANN (`> 10M` chunks):** **Qdrant** or **Milvus** (native HNSW payload pre-filtering on `tenant_id` / `acl_groups`).
- **Dual-Field Lexical Indexing (Recall + Exact Precision Together):**
  - Index EVERY searchable text field with BOTH:
    1. An **analyzed/stemmed field** (captures Indonesian affixes `pengajuan -> aju`, `pembayaran -> bayar`, `menghapus -> hapus` and English inflections), AND
    2. An **exact unstemmed / `keyword` sub-field** boosted `2x–3x` so exact SKUs (`INV-2026-0042`), regulation citations (`Perpres 46/2025`, `Pasal 56`), and acronyms (`UU PDP`, `SNAP BI`, `NIK`) ALWAYS rank `#1`!
- **Safe Fuzziness & Stopword Hygiene:**
  - Enable fuzzy typo tolerance (`AUTO`, edit distance `1–2`) ONLY on tokens `>= 4` characters — fuzzy-matching 2–3 character codes (`VA`, `ID`, `PPN`, `NIK`) creates severe false-positive noise!
  - Audit Indonesian stopwords carefully: overly aggressive stopword lists strip critical negations (`tidak`, `bukan`, `tanpa`) or domain verbs!

## 4. Architecture & Implementation
```json
{
  "settings": {
    "analysis": {
      "char_filter": {
        "strip_code_separators": { "type": "pattern_replace", "pattern": "[^\\p{L}\\p{N}]", "replacement": "" }
      },
      "normalizer": {
        "code_normalizer": { "type": "custom", "char_filter": ["strip_code_separators"], "filter": ["lowercase", "asciifolding"] }
      },
      "filter": {
        "id_stop": { "type": "stop", "stopwords": ["yang", "dan", "di", "ke", "dari", "untuk", "pada", "dengan", "ini", "itu"] },
        "id_stemmer": { "type": "stemmer", "language": "indonesian" },
        "domain_synonyms": {
          "type": "synonym_graph",
          "synonyms": ["ktp, nik", "ppn, pajak pertambahan nilai", "faktur, invoice"]
        }
      },
      "analyzer": {
        "id_search_index": {
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "id_stop", "id_stemmer"]
        },
        "id_search_query": {
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "id_stop", "domain_synonyms", "id_stemmer"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "tenant_id": { "type": "keyword" },
      "doc_code": { "type": "keyword", "normalizer": "code_normalizer" },
      "title": {
        "type": "text",
        "analyzer": "id_search_index",
        "search_analyzer": "id_search_query",
        "fields": { "exact": { "type": "keyword" } }
      }
    }
  }
}
```
Notes on the mapping above:
- `id_stop` is a deliberately short list. It never contains negations (`tidak`, `bukan`, `tanpa`, `belum`) or legal terms (`pasal`, `ayat`), because dropping them changes meaning. Grow it only from measured noise in the held-out set.
- `code_normalizer` maps `PP-27/2022`, `pp 27 2022` and `PP27/2022` to the same `pp272022` term. Index codes into `doc_code`; at query time extract identifier-shaped substrings, normalize them the same way and send a `term` query on `doc_code` with a higher boost than the analyzed `title`/`body` match. Use two grammars, because product codes and legal citations look different:

  ```python
  CODE = re.compile(r"\b(?=[A-Za-z0-9/-]*\d)(?=[A-Za-z0-9/-]*[A-Za-z])[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)+\b|\b[A-Z]{2,}\d+[A-Z0-9]*\b")
  CITE = re.compile(r"(?i)\b(?:uu|pp|perpres|permen\w*|perda|pojk|pasal|ayat)\s*(?:no\.?\s*)?\d+(?:\s*/\s*\d{4})?\b")
  ```

  Probed 2026-11-28. Recall 8/8: `PP-27/2022`, `INV-8841-ID`, `Perpres 46/2025`, `SKU123`, `Pasal 56`, `UU No. 27/2022`, `POJK 11/2022`, and a code inside a sentence. Precision 7/7 with no match: `tahun 2022`, `2022`, `tanggal 12/05`, `ukuran 3 kg`, `halaman 2`, and plain words. A naive `[A-Za-z]{1,6}[-\s]?\d+` failed this test: it matched `tahun 2022`, cut `Perpres` to `erpres` and dropped the `-ID` suffix. Extend the citation prefixes from your corpus, and re-run both probe sets after every change.
- The `indonesian` stemmer is a light Snowball stemmer. Sastrawi is more aggressive and can over-stem names; compare both on the held-out judgments rather than assuming.

PostgreSQL right-sized hybrid lexical + trigram schema (`< 1M` docs). First check which text search configurations the server has (`SELECT cfgname FROM pg_ts_config;`); if `indonesian` is missing, use `simple` plus `pg_trgm`, or install a Sastrawi-based dictionary:
```sql
-- Combined tsvector + exact code + tenant_id leading composite index
ALTER TABLE knowledge_docs ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('indonesian', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('indonesian', COALESCE(body, '')), 'B')
  ) STORED;

CREATE INDEX CONCURRENTLY idx_kdocs_tenant_tsv ON knowledge_docs USING GIN (search_tsv);
CREATE INDEX CONCURRENTLY idx_kdocs_tenant_code ON knowledge_docs (tenant_id, doc_code);
```

## 5. Platform / Vendor Variations
| Engine | Indonesian Stemming Support | Pre-Filter Support |
| :--- | :--- | :--- |
| **PostgreSQL** | `to_tsvector('indonesian', ...)` (or custom Sastrawi dictionary / `simple` + `pg_trgm`) | Native SQL `WHERE tenant_id = $1` |
| **OpenSearch / Elasticsearch** | Built-in `indonesian` analyzer + `synonym_graph` + custom `edge_ngram` | Native `bool.filter` term/terms on `tenant_id` & `acl_groups` |
| **Meilisearch / Typesense** | Language-aware tokenization + typo config (`minWordSizeForTypos`) | Scoped tenant filter expressions + signed search API keys |

## 6. Decision Matrix & Trade-Offs
| Query Type | Pure Dense Vector | Pure Lexical BM25 | Hybrid BM25 + Vector RRF (`02`) |
| :--- | :---: | :---: | :---: |
| Exact SKU / `Perpres 46/2025` / Error Code | **Poor** | **Best** | **Best (boosts exact!)** |
| Paraphrased Conceptual Question (`"aturan transfer data luar negeri"`) | **Best** | Moderate | **Best** |
| Code-Switched ID+EN Query (`"cara handle refund timeout Midtrans"`) | Good | Good | **Best** |

## 7. Real Production Scenario
An Indonesian legal-tech portal relies purely on dense vector embeddings; users searching `"Pasal 46 UU PDP"` get generic privacy policy intros instead of the exact Pasal 46 clause because embeddings smooth over exact numbers. Adding a dual-field BM25 analyzer (`id_search_index` + boosted `exact` subfield for clause numbers) fused with vector search via RRF jumps `MRR@5` on exact regulatory lookups from `0.41` to `0.94`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Indexing synonyms at **index time** without planning full reindex whenever a synonym is added (or expanding multi-word synonyms without `synonym_graph`, breaking phrase positions!).
- **RIGHT:** Apply `synonym_graph` at **query time** (`search_analyzer`) for agility, or reindex cleanly via atomic alias swap (`04`).
- **WRONG:** Modifying live index mappings/analyzers in-place (existing tokens remain tokenized under the old analyzer while new docs use the new one -> silent broken recall!).
- **RIGHT:** Always build `index_v2` and swap the read alias atomically (`04`).

## 9. Testing & Verification
- Test analyzer tokenization explicitly (`POST /_analyze`) on Indonesian affixed words (`pengajuan`, `diproses`, `pembatalan`), negations (`tidak berlaku`), and exact codes (`Perpres 46/2025`, `INV-001`) before indexing.

## 10. Operational Considerations
- Track **Zero-Result Query Rate** (`queries with 0 hits / total queries`) weekly — top zero-result queries immediately reveal missing Indonesian slang/synonyms or broken tokenization!

## 11. Authoritative References
- OpenSearch / Elasticsearch Official Reference — *Text Analysis, Indonesian Analyzer & `synonym_graph`* (`https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html`).
- PostgreSQL Full-Text Search & `pg_trgm` Documentation (`https://www.postgresql.org/docs/current/textsearch.html`).

## 12. Limitations & When NOT to Use
- Built-in rule-based Indonesian stemmers occasionally over-stem rare proper nouns or brand names; always pair stemmed fields with a boosted unstemmed/exact subfield so brand/product names stay crisp.
