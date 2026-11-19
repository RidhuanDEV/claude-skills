# Stage B — hasil pilot lokal

**19 November 2026 · IMPLEMENTED.** Baseline kode bac8745, kandidat pada working tree. Batch ini menguji keputusan lintas retrieval, authorization, generation dan reviewer dengan data sintetis; fixture mempunyai dua tenant dan dua query bahasa. Unit pada master backlog yang disentuh adalah X01/X02/X06, T09/T19/T01, C06/E01 dan T14. Bukti di bawah berlaku untuk slice pilot. Promosi maturity seluruh unit dan paritas host masih membutuhkan evaluasi tersendiri.

| Kasus | Baseline yang diamati | Bukti kandidat |
| --- | --- | --- |
| Satu ID relevan diambil dua kali | Recall 2,0 dan NDCG 1,6309 | Duplikat memakai posisi ranking semula dan tidak mendapat gain kedua. Query tanpa judgement positif tidak dapat meluluskan gate. |
| RAG menerima sampel kosong | Sampel kosong memperoleh hasil sempurna | Input tanpa bukti mendapat INCOMPLETE. Sampel bertipe mencatat denominator, dukungan per klaim, sitasi, language, dan keputusan abstain/isolation. Dokumen dicabut menggagalkan scoring mandiri. |
| Reviewer meminta only review this API endpoint sambil melarang load test | Router memilih shadow-perf | Mode code_review membatasi izin otomatis ke L0. Pada handoff, inspect lokal diizinkan, load_test ditolak. Lima tugas tetangga mempertahankan fase berbeda. |
| Jawaban menyalin assertion eval pertama | Mendapat 8/8 tanpa mengerjakan tugas | Kasus tanpa oracle terspesialisasi melaporkan manual_review_required dan nol assertion otomatis lulus. Pencocokan kosakata hanya diagnostik. |
| Job lain memiliki container bernama serupa | Pemeriksa lama menemukan tetangga dalam daftar target mock | Repo kanonis, run, ID penuh, label dan ledger harus cocok. Pemeriksa mengonfirmasi ulang status sebelum penghapusan non-forced. Cakupan Docker tanpa ledger dilaporkan NOT_RUN. |

### Hasil pembanding dua indeks

[Input yang dibekukan](../evals/fixtures/search-index-pilot.json) mencakup revisi indeks berbeda, korpus, snapshot ACL, judgement relevansi serta bukti pendukung klaim yang berasal dari reviewer. Jalankan [pembanding](../evals/compare_search_indexes.py) dengan revisi ACL aktual yang diberikan pemilik kebijakan secara independen.

- Fixture sehat memberi ELIGIBLE_FOR_REVIEW. Pada masing-masing segmen, satu pasangan menghasilkan delta NDCG +0,36907, sementara delta recall konteks, integritas sitasi dan dukungan klaim semuanya 0.
- HOLD direproduksi untuk konteks lintas tenant, akses dicabut, label hilang, regresi bahasa ketika rata-rata global naik, bukti klaim yang hanya dinyatakan kandidat, perbedaan snapshot, serta pasangan yang kurang.
- Review adversarial menemukan dua cacat yang sempat lolos pada kandidat pertama. Scorer RAG mandiri menerima dokumen dicabut, dan pembanding gabungan melewatkan penurunan recall konteks bahasa Indonesia dari 1,0 ke 0,5 ketika rata-rata kumpulan masih memenuhi ambang. Keduanya telah diperbaiki dan memperoleh tes regresi.

### Reproduksi dari akar repo

```powershell
python evals/compare_search_indexes.py evals/fixtures/search-index-pilot.json --acl-revision acl-7
python -m unittest discover -s evals -q
python -m unittest discover -s shadow-search/tests -q
python -m unittest discover -s shadow-eval/tests -q
python -m unittest discover -s shadow-quality/tests -q
python shadow-monarch/scripts/skill_router.py --self-test
python shadow-monarch/scripts/execution_approval_gate.py --self-test
python shadow-search/scripts/search_relevance_acl_gate.py --self-test
python shadow-eval/scripts/ai_eval_gate.py --self-test
python shadow-quality/scripts/shadow_gate.py --self-test
python evals/run_evals.py --self-test
python evals/run_evals.py --validate
node --test mcp-servers/shadow-api-mcp/discovery.test.mjs
python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks
```

**Hasil.** Keempat suite unittest lulus masing-masing 13, 9, 6 dan 10 tes. Enam self-test lulus masing-masing 46, 16, 6, 9, 14 dan 49 probe. Struktur 38 kasus eval valid. Semua 38 tes discovery MCP lulus. Gate repo melaporkan nol blocking violation dan recommended_max_readiness IMPLEMENTED karena audit Docker live tidak dijalankan dengan ledger. Tes ownership memakai mock; tidak ada cleanup daemon nyata.

**Batas bukti.** Data kecil ini memeriksa mekanisme keputusan, tanpa estimasi dampak produksi. Pemeriksaan ACL pada trace tidak membuktikan pre-filter sebelum top-K pada engine yang sedang melayani trafik. Ground truth dan judgement klaim membutuhkan reviewer independen; fixture sintetis tidak mengukur faithfulness jawaban produksi. Routing diuji pada CLI lokal, belum pada tiga aplikasi host. Kandidat belum dipasang lintas agent atau dipublikasikan.
