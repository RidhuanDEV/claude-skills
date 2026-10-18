# sub-RAG-VECTOR-KNOWLEDGE — Advanced RAG, Hybrid Search, Reranking, Vector DBs & GraphRAG

Use when designing, building, tuning, or evaluating Retrieval-Augmented Generation (RAG) pipelines, document ingestion
engines, vector databases (`pgvector`, Qdrant, Milvus, Weaviate, Pinecone), hybrid search, cross-encoder rerankers, or
GraphRAG / Knowledge Graph systems. Pair with `AI-LLM.md` for generation and `sub-VISION-OCR-MEDIA.md` for scanned PDFs.

## 1. Document ingestion & layout-aware parsing

Most RAG failures start with bad parsing and naive chunking:
- **Layout-aware parsing over raw text dumps**:
  - Parse PDFs, DOCX, PPTX, and HTML into structured Markdown/AST preserving **heading hierarchies (`#`, `##`, `###`),
    tables, lists, and page numbers** (use tools like `Docling`, `Marker`, `Unstructured`, `PyMuPDF4LLM`, or Vision-LLM layout parsers).
  - **Tables**: never split a table row across chunks or flatten a table into space-separated words. Convert tables into
    clean Markdown tables or structured JSON/HTML with column headers repeated in every chunk slice, plus a natural-language summary of the table for dense embedding.
- **Ingestion lifecycle & idempotency**:
  - Hash every source document (`content_sha256`) and chunk (`chunk_id = deterministic_hash(doc_id +version + chunk_index)`).
  - When a document is updated or deleted, atomically delete or mark obsolete its old vector chunks so stale/revoked policies are never retrieved.
  - Store mandatory metadata on every chunk: `doc_id`, `tenant_id`, `access_roles`, `source_uri`, `title`, `section_path`
    (e.g., `"HR Policy > Leave > Maternity Leave"`), `page_number`, `updated_at`, `embedding_model_id`.

## 2. Chunking & Contextual Retrieval strategies

- **Structure-aware semantic chunking**:
  - Split by Markdown headings and paragraphs first, targeting `300–600 tokens` per chunk with `10%–15%` overlap.
  - Never split mid-sentence, mid-code-block, or mid-table-row.
- **Contextual Retrieval (Anthropic pattern — eliminates orphan chunks)**:
  - A chunk saying *"The penalty is 5% per month"* is useless without knowing *which* contract or article it belongs to.
  - Always prepend the **Document Title + Section Hierarchy** (and optionally a 2-sentence LLM-generated contextual summary
    of where the chunk sits in the document) to the chunk text **before** generating both the dense embedding and BM25 index.
- **Parent-Child (Small-to-Big) Retrieval**:
  - Index smaller, focused child chunks (`150–250 tokens`) or hypothetical questions for high-precision vector matching,
    but link them to a larger **Parent Chunk / Full Section (`800–1,500 tokens`)** that is returned to the LLM for complete context.

## 3. Embeddings & Vector Database indexing at scale

- **Embedding discipline**:
  - Pin one exact `embedding_model_id` and dimension per vector index. Mixing embeddings from different models in the same space is invalid.
  - Normalize vectors (`L2` normalization) when using Cosine Similarity so inner-product (`<#>`) and cosine distance (`<=>`) are equivalent and faster.
  - Consider **multilingual models** (`BGE-M3`, `multilingual-e5-large`, `Cohere embed-multilingual-v3`, `text-embedding-3-large`)
    when queries and documents mix **Bahasa Indonesia and English**.
- **Vector DB selection & tuning**:
  - **`pgvector` (PostgreSQL)**: default choice up to ~5M–10M vectors when already running Postgres (transactional consistency with relational metadata + RBAC).
    - Use **HNSW** (`USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`).
    - Enable **`hnsw.iterative_scan = relaxed_order`** (pgvector 0.8+) whenever combining `WHERE tenant_id = ...` filters with `ORDER BY embedding <=> $1 LIMIT K`, preventing under-fetching when filters are selective!
    - Use `halfvec` (`float16`) or binary quantization to cut index RAM by 50%+.
  - **Dedicated Vector DBs (`Qdrant`, `Milvus`, `Weaviate`)**: use for 10M–1B+ vectors, multi-vector (`ColBERT`), native sparse+dense hybrid, or high-QPS low-latency separation.
    - In **Qdrant**: create explicit **Payload Indexes** (`keyword`, `integer`, `datetime`, `tenant: true`) on all filter fields *before* inserting vectors, and enable `scalar` (`int8`) or `binary` quantization in RAM with raw vectors on disk.

## 4. Hybrid Retrieval, Query Transformation & Reranking pipeline

Never rely on raw top-$K$ vector similarity alone in production:
```text
User Query → Query Analysis / Rewrite → Parallel [Dense Vector Top-50 + BM25/Sparse Top-50] (Pre-Filtered by Tenant/RBAC)
           → Reciprocal Rank Fusion (RRF) → Cross-Encoder Reranker (Top-50 → Top-8) → Context Assembly + Citations → LLM
```
1. **Pre-filtering by Security/Tenant (Mandatory)**: apply `tenant_id`, `access_roles`, and `status = 'PUBLISHED'` filters
   **inside** both the vector query and BM25 query — never filter after retrieval or after generation.
2. **Query Transformation**:
   - Conversational history condensation: rewrite follow-up questions (*"berapa dendanya?"*) into standalone search queries
     (*"berapa denda keterlambatan pembayaran pajak PBB di Perda X?"*).
   - Extract structured metadata filters (dates, document types, department codes) from the query when applicable.
   - Use **Multi-Query** or **HyDE (Hypothetical Document Embeddings)** when user queries are very short or abstract.
3. **Hybrid Search (Dense + Lexical BM25/Sparse)**:
   - Vector search captures semantic synonyms; **BM25 / Sparse (`SPLADE` / `BGE-M3` sparse / Postgres `tsvector`)** captures
     exact product SKUs, error codes (`ERR_4091`), legal article numbers (*Pasal 27 Ayat 2*), and proper nouns.
   - Combine results with **Reciprocal Rank Fusion (RRF)**:
     $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + \text{rank}_m(d)} \quad (k = 60)$$
4. **Cross-Encoder Reranking (Highest ROI quality boost)**:
   - Pass the top 30–50 fused candidates into a **Cross-Encoder Reranker** (`bge-reranker-v2-m3`, `Cohere Rerank v3.5`,
     `Jina Reranker`, or `FlashRank`) and keep the top 5–10 chunks above a minimum relevance threshold.

## 5. GraphRAG & Agentic / Corrective RAG

- **When to add GraphRAG (`Neo4j` / Property Graph + Vector)**:
  - Standard vector RAG fails on multi-hop relational questions (*"Which vendors share directors with companies sanctioned in 2025?"* or global corpus synthesis).
  - Extract typed **Entities** and **Relationships** (`(Person)-[:DIRECTOR_OF]->(Company)`) linked back to source `chunk_id`s, and combine Cypher/graph traversal with vector retrieval.
- **Agentic / Corrective RAG (CRAG)**:
  - Grade retrieved chunks for relevance before generation. If relevance is low or ambiguous, rewrite the query, broaden search filters, or return a deterministic *"Information not found in verified documents"* response rather than hallucinating.

## 6. Grounded generation & RAG evaluation (`RAGAS` / `DeepEval`)

- **Citation contract**: assign each retrieved chunk a reference ID (`[Doc-1, p.4]`) in the prompt; require the LLM to cite
  `[Doc-1, p.4]` inline for every factual claim and forbid using outside pre-trained knowledge when answering closed-domain questions.
- **Evaluate the 4 RAG Triad metrics separately in CI**:
  1. **Context Recall** & **Context Precision** (`Recall@K`, `MRR`, `NDCG@K` — pure retrieval test, fast and cheap).
  2. **Faithfulness / Groundedness** (does every claim in the answer follow strictly from the retrieved chunks?).
  3. **Answer Relevance** (did it actually answer the user's question?).
