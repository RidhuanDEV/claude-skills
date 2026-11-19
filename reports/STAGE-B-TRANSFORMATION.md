# Stage B — bukti implementasi lokal

Revisi pembanding `bac8745`. Kandidat adalah working tree. Matriks kompetensi dan backlog tetap menjadi indeks sasaran. Hanya perilaku yang diuji di bawah mendapat bukti eksekusi.

| Area | Perilaku yang diperiksa | Cara mengulang di akar repo |
| --- | --- | --- |
| Routing | Permintaan bootstrap CLI kini memilih pemilik yang sesuai. Kontrol Bootstrap CSS tetap memilih Monarch. Baseline 1/2, kandidat 2/2. | `python evals/compare_bootstrap_routing.py --baseline bac8745` |
| Sumber pengetahuan | Unduhan yang ditolak dan manifest rusak mempertahankan arsip lama. Perubahan digest memblokir penggunaan pin. | `python -m unittest discover -s shadow-doc/tests -v` |
| Integrasi | Keputusan setelah timeout mempertimbangkan identitas provider, kunci permintaan dan jendela replay. | `python shadow-integrate/scripts/reconcile_unknown.py --self-test` |
| Browser dan data | Pembanding browser menilai observasi terhadap skenario. Ekspor ETL melaporkan potensi kehilangan presisi dan metadata kunci. | `python -m unittest discover -s shadow-browser/tests -v` dan `node --test mcp-servers/shadow-db-mcp/etl.test.mjs` |
| Performa dan recovery | Compiler skenario memilih operasi aktual. Diagnosis membedakan tekanan generator dan layanan. Evaluator pemulihan memakai checkpoint serta observasi alur bisnis. | `node --test shadow-perf/tests/scaffold.test.mjs` dan `python -m unittest discover -s shadow-resilience/tests -v` |
| Realtime dan supply chain | Fixture replay mencakup pencabutan akses. Pembanding supply chain menghitung digest lokal dan memeriksa bukti independen yang diberikan. | Jalankan unittest discovery pada `shadow-realtime/tests` dan `shadow-supplychain/tests`. |
| Desain | Resolusi metode, 11 chapter portabel, collision UX vs PM, Doherty/202, dan workshop snapshot/moderasi diuji lokal. | `python -m unittest discover -s shadow-design/tests -v` |
| Refactor & Git | Perubahan file tanpa daftar cakupan gagal; worktree advance, semantic event order, dan rounding diuji lokal. | `python shadow-refactor/scripts/refactor_characterization_gate.py --self-test` dan `python -m unittest discover -s shadow-git/tests -v` |
| Orchestration, Handoff & Core | `skill_router.py` (T09/X04/negation guard), `execution_approval_gate.py` (stale SHA/host drift), `shadow-handoff-mcp` (branch/HEAD drift, legacy snapshot, scope propagation), serta acceptance suites per skill (`C01`–`C15`, `T02`–`T23`, `E02`–`E15`). | `node --test mcp-servers/shadow-handoff-mcp/handoff.test.mjs` dan `python -m unittest discover -s evals -v` |

## Reproduksi suite lokal

PowerShell dari akar repo. Setiap perintah keluar bila suite gagal.

```powershell
$dirs = @('evals') + @(Get-ChildItem -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'tests\test_*.py') } | ForEach-Object { Join-Path $_.Name 'tests' })
foreach ($dir in $dirs) {
    python -m unittest discover -s $dir -v
    if ($LASTEXITCODE) { throw "Suite gagal di $dir" }
}
node --test mcp-servers/shadow-handoff-mcp/handoff.test.mjs
node --test mcp-servers/shadow-db-mcp/etl.test.mjs
node --test mcp-servers/shadow-api-mcp/discovery.test.mjs
node --test shadow-perf/tests/scaffold.test.mjs
if ($LASTEXITCODE) { throw 'Suite Node gagal' }
python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks
```

## Batas kualifikasi

Seluruh suite deterministik lokal lulus (**127/127 Python unittest**, **56/56 Node tests**, **9/9 self-test/gate scripts**; `VERIFIED-LOCAL` untuk cakupan fixture lokal). Kepemilikan resource Docker berstatus `NOT_RUN` bila tidak menjalankan container Docker. Belum tersedia holdout independen dari reviewer eksternal. Evaluasi model live lintas Codex, Gemini, Antigravity dan Claude, variasi antar-run, deployment, browser pengguna nyata, transfer operasional, dan restore layanan nyata diuji pada fase berikutnya melalui monorepo uji `testing-skills-be-fe-other`.
