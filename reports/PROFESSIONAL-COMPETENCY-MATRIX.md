# Matriks kompetensi profesional Shadow Army

Baseline **bac8745** mencakup 38 skill utama dan 17 modul desain yang dipilih. Setiap unit memiliki 20 penilaian baseline dan target. Modul bernama sama menggunakan path yang berbeda. Nilai mengacu pada tugas atau oracle yang dicantumkan, sehingga satu kegagalan dapat dilacak sampai batas klaim yang tepat. [Dasar seleksi](skill-upgrade-plan.md) · [Capstone 38 skill](skill-upgrade-competencies.md) · [Capstone 17 modul](skill-upgrade-design-library.md)

## Cara membaca matriks

| Tingkat | Bukti perilaku yang dipersyaratkan |
| --- | --- |
| L0 | Memahami konsep dasar dan dapat menjelaskan istilah dengan benar pada tugas pengetahuan yang diamati. |
| L1 | Menyelesaikan happy path melalui entrypoint normal pada kasus dengan input valid. |
| L2 | Menyelesaikan happy path serta memvalidasi error atau edge case yang relevan pada dimensi yang sama. |
| L3 | Menghasilkan perubahan brownfield yang andal, cocok dengan kontrak proyek dan telah diverifikasi. |
| L4 | Mempertimbangkan alternatif, menimbang trade-off desain atau operasi dan mempertanggungjawabkan keputusan melalui bukti profesional. |
| L5 | Secara konsisten memenuhi kriteria ahli pada tugas baru yang belum dilihat dan variasi adversarial, dengan batas generalisasi yang dinyatakan. |

Setiap sel memakai **baseline/target**. `1P` mencatat keberhasilan happy path. `2P` juga memiliki pembanding error atau edge pada dimensi yang sama. Huruf `F` adalah hasil gagal pada skenario, terpisah dari skala L0–L5. `FA` menunjukkan counterexample yang dapat diulangi melalui audit A dan `FP` menunjukkan probe lokal yang gagal memenuhi oracle yang ditetapkan. `US` berarti panduan terkait tersedia dalam kontrak S dan performa belum diukur. `U!` berarti temuan A memberi alasan khusus menahan klaim. `U` berarti bukti yang ada tidak mencukupi. Dimensi arsitektur perangkat lunak untuk instrumen riset/visual mandiri diberi `NA` karena desain sistem produksi dimiliki engineer terkait. Arsitektur studi tetap dinilai melalui keputusan, riset dan integrasi.

Target L4 berlaku untuk tiga kompetensi pemilik yang disebut pada register. Target L3 berlaku pada dimensi yang dicakup prosedur atau temuan lain. Pada dimensi pendukung, target L2 berarti skill harus mengenali dan memberi rujukan yang tepat pada kasus rutin serta pada input keliru atau kondisi batas. Target adalah usulan perencanaan. Jangan rata-ratakan kegagalan, unknown dan NA. Bukti tertulis saja tidak memberikan poin kompetensi. Belum ada bukti produksi atau parity langsung tiga host di baseline ini.

## Kamus dimensi

**DK** Domain Expertise · **PU** Problem Understanding · **CT** Context Awareness · **DJ** Decision Making · **AR** Architecture

**IM** Implementation · **SE** Security · **PF** Performance · **RL** Reliability · **SC** Scalability

**MT** Maintainability · **TS** Testing · **RS** Research · **TL** Tool Usage · **IG** Integration

**EC** Edge Cases · **FR** Failure Recovery · **DC** Documentation · **AD** Adaptability · **PR** Production Readiness

## Domain Expertise hingga Architecture

| Unit | DK | PU | CT | DJ | AR |
| --- | --- | --- | --- | --- | --- |
| [antislop](#e-antislop) | US/3 | US/3 | U!/4 | U!/4 | U/2 |
| [context7](#e-context7) | US/3 | US/3 | U!/4 | U/2 | U/2 |
| [handoff](#e-handoff) | US/3 | US/3 | US/4 | US/3 | U/2 |
| [shadow-accessibility](#e-shadow-accessibility) | US/3 | US/4 | U/2 | US/3 | U/2 |
| [shadow-architect](#e-shadow-architect) | US/3 | US/3 | US/4 | U!/4 | US/4 |
| [shadow-auth](#e-shadow-auth) | US/3 | U/2 | US/3 | US/3 | US/3 |
| [shadow-bootstrap](#e-shadow-bootstrap) | US/3 | U/2 | U!/4 | U!/3 | US/3 |
| [shadow-browser](#e-shadow-browser) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [shadow-cache](#e-shadow-cache) | US/3 | U/2 | U/2 | US/3 | US/3 |
| [shadow-compat](#e-shadow-compat) | US/3 | US/3 | U!/4 | US/3 | US/3 |
| [shadow-data](#e-shadow-data) | US/3 | U/2 | US/3 | US/3 | US/3 |
| [shadow-db](#e-shadow-db) | US/3 | U/2 | US/3 | US/3 | US/3 |
| [shadow-design](#e-shadow-design) | US/3 | US/3 | US/4 | US/3 | US/3 |
| [shadow-discovery](#e-shadow-discovery) | US/3 | US/4 | US/3 | U!/4 | U/2 |
| [shadow-doc](#e-shadow-doc) | US/3 | US/3 | US/4 | U!/4 | US/3 |
| [shadow-eval](#e-shadow-eval) | US/4 | US/3 | U/2 | US/3 | U/2 |
| [shadow-finops](#e-shadow-finops) | US/3 | US/3 | US/4 | US/4 | U/2 |
| [shadow-git](#e-shadow-git) | US/3 | U/2 | 1P/4 | US/3 | U/2 |
| [shadow-grc](#e-shadow-grc) | US/3 | US/3 | U!/4 | US/3 | U/2 |
| [shadow-handover](#e-shadow-handover) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [shadow-integrate](#e-shadow-integrate) | US/3 | U/2 | US/4 | US/3 | US/3 |
| [shadow-maintain](#e-shadow-maintain) | US/3 | US/3 | US/3 | US/4 | U/2 |
| [shadow-mobile](#e-shadow-mobile) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [shadow-monarch](#e-shadow-monarch) | US/3 | US/4 | US/3 | US/4 | U/2 |
| [shadow-ops](#e-shadow-ops) | US/3 | U/2 | US/4 | US/3 | US/3 |
| [shadow-perf](#e-shadow-perf) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [shadow-plan](#e-shadow-plan) | US/3 | US/4 | US/3 | US/4 | U/2 |
| [shadow-privacy](#e-shadow-privacy) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [shadow-quality](#e-shadow-quality) | US/3 | U/2 | US/3 | US/3 | U/2 |
| [shadow-realtime](#e-shadow-realtime) | US/3 | U/2 | U/2 | US/3 | US/3 |
| [shadow-refactor](#e-shadow-refactor) | US/3 | U/2 | FA/4 | US/3 | US/3 |
| [shadow-release](#e-shadow-release) | US/3 | U/2 | US/4 | US/3 | U/2 |
| [shadow-resilience](#e-shadow-resilience) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-search](#e-shadow-search) | US/4 | US/3 | US/3 | US/3 | US/3 |
| [shadow-sec](#e-shadow-sec) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [shadow-supplychain](#e-shadow-supplychain) | US/3 | U/2 | US/3 | US/3 | U/2 |
| [shadow-test](#e-shadow-test) | US/3 | US/3 | US/4 | US/3 | U/2 |
| [shadow-uat](#e-shadow-uat) | US/3 | US/4 | US/3 | US/3 | U/2 |
| [D01](#e-d01) | US/3 | US/4 | US/3 | US/3 | US/3 |
| [D02](#e-d02) | US/3 | US/4 | U!/4 | US/4 | U/2 |
| [D03](#e-d03) | US/3 | US/3 | US/3 | US/4 | U/2 |
| [D04](#e-d04) | US/3 | US/4 | US/3 | US/3 | NA |
| [D05](#e-d05) | US/3 | US/4 | US/3 | US/3 | NA |
| [D06](#e-d06) | US/3 | US/3 | US/4 | US/3 | NA |
| [D07](#e-d07) | US/3 | US/4 | US/3 | US/3 | NA |
| [D08](#e-d08) | US/3 | US/4 | US/3 | US/3 | NA |
| [D09](#e-d09) | US/3 | US/4 | US/3 | US/3 | NA |
| [D10](#e-d10) | US/3 | US/3 | U!/4 | US/4 | U/2 |
| [D11](#e-d11) | US/3 | US/4 | U/2 | U!/4 | NA |
| [D12](#e-d12) | US/3 | US/3 | U!/4 | US/3 | U/2 |
| [D13](#e-d13) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D14](#e-d14) | U/2 | U/4 | U/2 | U/2 | U/2 |
| [D15](#e-d15) | U/2 | U/2 | U/4 | U/2 | U/2 |
| [D16](#e-d16) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [D17](#e-d17) | US/3 | US/3 | US/3 | US/3 | U/2 |

## Implementation hingga Scalability

| Unit | IM | SE | PF | RL | SC |
| --- | --- | --- | --- | --- | --- |
| [antislop](#e-antislop) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [context7](#e-context7) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [handoff](#e-handoff) | U/2 | U/2 | U/2 | US/3 | U/2 |
| [shadow-accessibility](#e-shadow-accessibility) | U!/3 | U/2 | U/2 | U/2 | U/2 |
| [shadow-architect](#e-shadow-architect) | U/2 | U/2 | U/2 | US/3 | US/3 |
| [shadow-auth](#e-shadow-auth) | US/3 | US/4 | U/2 | US/3 | U/2 |
| [shadow-bootstrap](#e-shadow-bootstrap) | US/4 | U/2 | U/2 | US/3 | U/2 |
| [shadow-browser](#e-shadow-browser) | US/3 | U/2 | US/3 | US/3 | U/2 |
| [shadow-cache](#e-shadow-cache) | US/3 | US/4 | US/3 | US/4 | US/3 |
| [shadow-compat](#e-shadow-compat) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [shadow-data](#e-shadow-data) | US/3 | US/3 | US/3 | US/4 | US/3 |
| [shadow-db](#e-shadow-db) | US/4 | US/3 | US/3 | US/3 | US/3 |
| [shadow-design](#e-shadow-design) | US/3 | U/2 | U/2 | US/3 | U/2 |
| [shadow-discovery](#e-shadow-discovery) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [shadow-doc](#e-shadow-doc) | US/4 | U/2 | U/2 | U/2 | U/2 |
| [shadow-eval](#e-shadow-eval) | U/2 | US/3 | U/2 | US/3 | U/2 |
| [shadow-finops](#e-shadow-finops) | U/2 | U/2 | US/3 | U/2 | US/3 |
| [shadow-git](#e-shadow-git) | US/3 | U/2 | U/2 | US/3 | U/2 |
| [shadow-grc](#e-shadow-grc) | U/2 | US/3 | U/2 | U/2 | U/2 |
| [shadow-handover](#e-shadow-handover) | U/2 | US/3 | U/2 | US/3 | U/2 |
| [shadow-integrate](#e-shadow-integrate) | US/3 | US/3 | U/2 | US/4 | U/2 |
| [shadow-maintain](#e-shadow-maintain) | U/2 | U/2 | U/2 | US/3 | U/2 |
| [shadow-mobile](#e-shadow-mobile) | US/3 | U!/4 | US/3 | US/3 | U/2 |
| [shadow-monarch](#e-shadow-monarch) | US/3 | US/3 | U/2 | U/2 | U/2 |
| [shadow-ops](#e-shadow-ops) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-perf](#e-shadow-perf) | FA/4 | U/2 | US/4 | US/3 | US/3 |
| [shadow-plan](#e-shadow-plan) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [shadow-privacy](#e-shadow-privacy) | U/2 | US/4 | U/2 | U/2 | U/2 |
| [shadow-quality](#e-shadow-quality) | US/3 | FA/4 | U/2 | U/2 | U/2 |
| [shadow-realtime](#e-shadow-realtime) | US/3 | US/4 | US/3 | US/4 | US/3 |
| [shadow-refactor](#e-shadow-refactor) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [shadow-release](#e-shadow-release) | US/3 | US/3 | U/2 | US/3 | U/2 |
| [shadow-resilience](#e-shadow-resilience) | US/3 | U/2 | US/3 | US/4 | U/2 |
| [shadow-search](#e-shadow-search) | US/3 | 2P/4 | US/3 | U/2 | US/3 |
| [shadow-sec](#e-shadow-sec) | U/2 | US/4 | U/2 | U/2 | U/2 |
| [shadow-supplychain](#e-shadow-supplychain) | US/3 | U!/4 | U/2 | US/3 | U/2 |
| [shadow-test](#e-shadow-test) | US/3 | U/2 | U/2 | US/3 | U/2 |
| [shadow-uat](#e-shadow-uat) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D01](#e-d01) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [D02](#e-d02) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D03](#e-d03) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [D04](#e-d04) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D05](#e-d05) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D06](#e-d06) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D07](#e-d07) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D08](#e-d08) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D09](#e-d09) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D10](#e-d10) | US/3 | U/2 | US/4 | U/2 | U/2 |
| [D11](#e-d11) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D12](#e-d12) | US/3 | US/4 | U/2 | U/2 | U/2 |
| [D13](#e-d13) | FP/3 | U/4 | U/2 | U/2 | U/2 |
| [D14](#e-d14) | FP/3 | U/2 | U/2 | U/2 | U/2 |
| [D15](#e-d15) | FP/3 | U/2 | U/2 | U/2 | U/2 |
| [D16](#e-d16) | US/3 | U!/4 | U/2 | U/2 | U/2 |
| [D17](#e-d17) | US/3 | U!/4 | U/2 | U/2 | U/2 |

## Maintainability hingga Integration

| Unit | MT | TS | RS | TL | IG |
| --- | --- | --- | --- | --- | --- |
| [antislop](#e-antislop) | US/3 | US/3 | U/2 | U/2 | US/3 |
| [context7](#e-context7) | U/2 | U/2 | U!/4 | U!/3 | U/2 |
| [handoff](#e-handoff) | US/3 | U/2 | U/2 | US/3 | U!/4 |
| [shadow-accessibility](#e-shadow-accessibility) | U/2 | US/4 | U/2 | US/3 | US/3 |
| [shadow-architect](#e-shadow-architect) | US/3 | U/2 | U/2 | U/2 | U/2 |
| [shadow-auth](#e-shadow-auth) | U/2 | U!/4 | U/2 | U/2 | US/3 |
| [shadow-bootstrap](#e-shadow-bootstrap) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-browser](#e-shadow-browser) | U/2 | U!/4 | U/2 | US/4 | US/3 |
| [shadow-cache](#e-shadow-cache) | US/3 | U/2 | U/2 | U/2 | US/3 |
| [shadow-compat](#e-shadow-compat) | US/3 | US/4 | US/3 | US/3 | US/3 |
| [shadow-data](#e-shadow-data) | US/3 | US/3 | U/2 | U/2 | US/3 |
| [shadow-db](#e-shadow-db) | US/3 | U/4 | U/2 | US/3 | US/3 |
| [shadow-design](#e-shadow-design) | US/3 | US/3 | US/3 | U/2 | US/4 |
| [shadow-discovery](#e-shadow-discovery) | U/2 | US/3 | US/4 | U/2 | US/3 |
| [shadow-doc](#e-shadow-doc) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-eval](#e-shadow-eval) | U/2 | FA/4 | U/2 | 1P/3 | US/3 |
| [shadow-finops](#e-shadow-finops) | U/2 | US/3 | U/2 | 1P/3 | U/2 |
| [shadow-git](#e-shadow-git) | US/3 | US/3 | U/2 | FA/4 | US/4 |
| [shadow-grc](#e-shadow-grc) | U/2 | 2P/4 | US/3 | 1P/3 | US/3 |
| [shadow-handover](#e-shadow-handover) | US/3 | U/2 | U/2 | U/2 | US/4 |
| [shadow-integrate](#e-shadow-integrate) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-maintain](#e-shadow-maintain) | US/3 | US/3 | U/2 | U/2 | US/3 |
| [shadow-mobile](#e-shadow-mobile) | U/2 | US/4 | U/2 | 1P/3 | US/3 |
| [shadow-monarch](#e-shadow-monarch) | US/3 | US/3 | U/2 | 1P/3 | FA/4 |
| [shadow-ops](#e-shadow-ops) | US/3 | U/2 | U/2 | US/3 | US/3 |
| [shadow-perf](#e-shadow-perf) | U/2 | FA/4 | U/2 | US/3 | US/3 |
| [shadow-plan](#e-shadow-plan) | US/3 | US/3 | U/2 | U/2 | US/3 |
| [shadow-privacy](#e-shadow-privacy) | U/2 | US/4 | US/3 | 1P/3 | US/3 |
| [shadow-quality](#e-shadow-quality) | US/3 | US/4 | U/2 | US/3 | US/3 |
| [shadow-realtime](#e-shadow-realtime) | U/2 | U!/3 | U/2 | 1P/3 | US/3 |
| [shadow-refactor](#e-shadow-refactor) | US/4 | US/4 | U/2 | 1P/3 | US/3 |
| [shadow-release](#e-shadow-release) | U/2 | US/3 | U/2 | US/3 | US/3 |
| [shadow-resilience](#e-shadow-resilience) | U/2 | US/4 | U/2 | US/3 | US/3 |
| [shadow-search](#e-shadow-search) | U/2 | FA/4 | U/2 | 1P/3 | US/3 |
| [shadow-sec](#e-shadow-sec) | U/2 | US/4 | U!/4 | US/3 | US/3 |
| [shadow-supplychain](#e-shadow-supplychain) | US/3 | US/4 | U/2 | 1P/3 | US/3 |
| [shadow-test](#e-shadow-test) | US/3 | US/4 | U/2 | US/3 | US/3 |
| [shadow-uat](#e-shadow-uat) | U/2 | US/4 | U/2 | US/3 | US/3 |
| [D01](#e-d01) | US/3 | US/3 | US/3 | U/2 | FP/4 |
| [D02](#e-d02) | U/2 | U/2 | US/3 | U/2 | US/3 |
| [D03](#e-d03) | US/3 | U/2 | U/2 | U/2 | US/4 |
| [D04](#e-d04) | U/2 | U/2 | US/4 | U/2 | FP/4 |
| [D05](#e-d05) | U/2 | U/2 | US/4 | U/2 | FP/4 |
| [D06](#e-d06) | U/2 | U/2 | US/4 | U/2 | FP/4 |
| [D07](#e-d07) | U/2 | U/2 | US/4 | U/2 | FP/4 |
| [D08](#e-d08) | U/2 | US/3 | US/4 | U/2 | FP/4 |
| [D09](#e-d09) | U/2 | US/3 | US/4 | U/2 | FP/4 |
| [D10](#e-d10) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D11](#e-d11) | U/2 | US/4 | U/2 | U/2 | U/2 |
| [D12](#e-d12) | U/2 | U/2 | U/2 | U/2 | US/4 |
| [D13](#e-d13) | U/2 | U/4 | U/2 | US/3 | U/4 |
| [D14](#e-d14) | U/2 | U/4 | U/2 | US/3 | U/4 |
| [D15](#e-d15) | U/2 | U/2 | U/2 | US/3 | U/4 |
| [D16](#e-d16) | U/2 | U/2 | US/3 | US/3 | US/4 |
| [D17](#e-d17) | U/2 | U/2 | U/2 | US/3 | US/4 |

## Edge Cases hingga Production Readiness

| Unit | EC | FR | DC | AD | PR |
| --- | --- | --- | --- | --- | --- |
| [antislop](#e-antislop) | US/3 | U/2 | US/3 | US/4 | U/2 |
| [context7](#e-context7) | U/2 | U/2 | U/2 | U!/4 | U/2 |
| [handoff](#e-handoff) | US/3 | US/4 | US/3 | U!/3 | U/2 |
| [shadow-accessibility](#e-shadow-accessibility) | US/4 | U/2 | US/3 | U!/3 | U/2 |
| [shadow-architect](#e-shadow-architect) | U/2 | U/2 | US/3 | US/3 | U/2 |
| [shadow-auth](#e-shadow-auth) | US/4 | US/3 | US/3 | U/2 | U/2 |
| [shadow-bootstrap](#e-shadow-bootstrap) | U/2 | U/2 | US/3 | U!/4 | U/2 |
| [shadow-browser](#e-shadow-browser) | US/4 | U/2 | US/3 | U/2 | U/2 |
| [shadow-cache](#e-shadow-cache) | U!/4 | US/3 | U/2 | U/2 | U/2 |
| [shadow-compat](#e-shadow-compat) | US/3 | U/2 | US/3 | US/4 | US/3 |
| [shadow-data](#e-shadow-data) | US/4 | U!/4 | US/3 | U/2 | US/3 |
| [shadow-db](#e-shadow-db) | US/3 | US/4 | US/3 | US/3 | U!/3 |
| [shadow-design](#e-shadow-design) | US/3 | US/3 | US/3 | U!/4 | U/2 |
| [shadow-discovery](#e-shadow-discovery) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [shadow-doc](#e-shadow-doc) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-eval](#e-shadow-eval) | FA/4 | U/2 | US/3 | U/2 | U/2 |
| [shadow-finops](#e-shadow-finops) | 2P/3 | U/2 | US/3 | U!/4 | U/2 |
| [shadow-git](#e-shadow-git) | US/3 | US/3 | US/3 | US/3 | US/3 |
| [shadow-grc](#e-shadow-grc) | US/3 | U/2 | US/4 | U/2 | U/2 |
| [shadow-handover](#e-shadow-handover) | U/2 | US/4 | US/4 | U!/3 | US/3 |
| [shadow-integrate](#e-shadow-integrate) | US/4 | US/3 | US/3 | U!/3 | U/2 |
| [shadow-maintain](#e-shadow-maintain) | US/3 | U!/4 | US/3 | U/2 | US/4 |
| [shadow-mobile](#e-shadow-mobile) | FA/3 | US/3 | U/2 | US/4 | US/3 |
| [shadow-monarch](#e-shadow-monarch) | US/3 | US/3 | US/3 | US/3 | U/2 |
| [shadow-ops](#e-shadow-ops) | US/3 | US/4 | US/3 | U!/4 | US/3 |
| [shadow-perf](#e-shadow-perf) | US/3 | U/2 | US/3 | U/2 | US/3 |
| [shadow-plan](#e-shadow-plan) | US/3 | U/2 | US/3 | U!/4 | U/2 |
| [shadow-privacy](#e-shadow-privacy) | 2P/3 | U/2 | US/4 | U/2 | U!/3 |
| [shadow-quality](#e-shadow-quality) | US/4 | US/3 | US/3 | U/2 | U/2 |
| [shadow-realtime](#e-shadow-realtime) | FA/3 | US/4 | U/2 | U/2 | U/2 |
| [shadow-refactor](#e-shadow-refactor) | US/3 | US/3 | US/3 | U/2 | U/2 |
| [shadow-release](#e-shadow-release) | US/3 | US/4 | US/3 | U!/3 | US/4 |
| [shadow-resilience](#e-shadow-resilience) | US/3 | U!/4 | US/3 | U/2 | US/3 |
| [shadow-search](#e-shadow-search) | FA/3 | U/2 | US/3 | U/2 | U/2 |
| [shadow-sec](#e-shadow-sec) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [shadow-supplychain](#e-shadow-supplychain) | FA/4 | US/3 | US/3 | U/2 | U/2 |
| [shadow-test](#e-shadow-test) | US/3 | US/3 | US/3 | U!/4 | U/2 |
| [shadow-uat](#e-shadow-uat) | US/3 | U/2 | US/3 | U!/4 | US/3 |
| [D01](#e-d01) | US/4 | US/3 | US/3 | US/3 | U/2 |
| [D02](#e-d02) | U/2 | U/2 | US/3 | U/2 | U/2 |
| [D03](#e-d03) | US/3 | US/3 | FP/4 | U/2 | U/2 |
| [D04](#e-d04) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D05](#e-d05) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D06](#e-d06) | U/2 | U/2 | US/3 | U/2 | U/2 |
| [D07](#e-d07) | U/2 | U/2 | US/3 | U/2 | U/2 |
| [D08](#e-d08) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D09](#e-d09) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D10](#e-d10) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D11](#e-d11) | US/3 | U/2 | US/3 | U/2 | U/2 |
| [D12](#e-d12) | US/3 | US/3 | US/3 | U/2 | U/2 |
| [D13](#e-d13) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D14](#e-d14) | U/2 | U/2 | U/2 | U/2 | U/2 |
| [D15](#e-d15) | U/2 | U/2 | U/4 | U/2 | U/2 |
| [D16](#e-d16) | US/4 | U/2 | US/3 | U/2 | U/2 |
| [D17](#e-d17) | US/4 | US/3 | US/3 | U/2 | U/2 |

## Register bukti, pemilik dan target

Setiap sel mewarisi sumber pada unit yang sama. S menunjuk berkas otoritatif; A menunjuk temuan dan reproduksi; P menunjukkan hasil probe lokal. ID D01–D17 cocok dengan nomor pada backlog desain. Tingkat unknown menunjukkan kebutuhan pengukuran spesifik, termasuk bila satu suite alat berhasil tetapi kualitas keputusan agen belum diuji.

<a id="e-antislop"></a>

### antislop

**Owner:** Lead UI reviewer dan design-system owner. **Target L4:** Context Awareness, Decision Making, Adaptability.

**A.** Bagian Two Usage Modes memeriksa sesi dan preferensi lintas proyek. Saat berkas preferensi hilang, proses berhenti untuk menanyakan mode bahkan pada review baca-saja. Instruksi Monarch telah menetapkan `during`. [S · antislop/SKILL.md](../antislop/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-context7"></a>

### context7

**Owner:** Library maintainer dan research engineer. **Target L4:** Context Awareness, Research, Adaptability.

**A.** Empat langkah Workflow berakhir dengan penerapan sintaks terkini. Tidak ada langkah eksplisit untuk mengekstrak versi lockfile atau menangani hasil untuk major berbeda. [S · context7/SKILL.md](../context7/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-handoff"></a>

### handoff

**Owner:** Configuration manager dan penerima shift. **Target L4:** Context Awareness, Integration, Failure Recovery.

**A.** Kontrak merge memelihara readiness terendah dan memberi peringatan konflik, tetapi fallback save menyebut path drive D pada mesin penulis. [S · handoff/SKILL.md](../handoff/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-accessibility"></a>

### shadow-accessibility

**Owner:** Accessibility engineer dan assistive-technology tester. **Target L4:** Problem Understanding, Testing, Edge Cases.

**A.** Pilar formulir mewajibkan `<label htmlFor>` untuk setiap input. Aturan React yang spesifik terlalu sempit untuk kontrol native dengan label pembungkus dan proyek HTML non-React. [S · shadow-accessibility/SKILL.md](../shadow-accessibility/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-architect"></a>

### shadow-architect

**Owner:** Staff architect dan service owner. **Target L4:** Context Awareness, Decision Making, Architecture.

**A.** Persyaratan Mandatory Architecture Deliverables dan gate menuju plan/bootstrap tidak membedakan pertanyaan desain satu modul dari desain aplikasi penuh secara operasional. [S · shadow-architect/SKILL.md](../shadow-architect/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-auth"></a>

### shadow-auth

**Owner:** IAM engineer dan API owner. **Target L4:** Security, Testing, Edge Cases.

**A.** Bagian Policy Test Matrix menyebut 403/404 juga untuk pemanggil tanpa autentikasi. Aturan literal bisa mengubah respons 401 yang sudah menjadi kontrak endpoint. [S · shadow-auth/SKILL.md](../shadow-auth/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-bootstrap"></a>

### shadow-bootstrap

**Owner:** Platform engineer dan developer experience lead. **Target L4:** Context Awareness, Implementation, Adaptability.

**A.** Delapan pilar wajib menggabungkan OpenAPI, DB/ORM, health probe DB+Redis, Compose dan struktur direktori tertentu. Proyek CLI offline dan situs statis juga masuk cakupan deskripsi greenfield. [S · shadow-bootstrap/SKILL.md](../shadow-bootstrap/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-browser"></a>

### shadow-browser

**Owner:** Web QA engineer dan browser specialist. **Target L4:** Tool Usage, Testing, Edge Cases.

**A.** Bagian Console & Network meminta pelaporan semua 4xx/5xx. Tanpa oracle per skenario, respons valid pada alur login gagal dapat dibaca sebagai regresi. [S · shadow-browser/SKILL.md](../shadow-browser/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-cache"></a>

### shadow-cache

**Owner:** Distributed systems engineer dan frontend platform owner. **Target L4:** Security, Reliability, Edge Cases.

**A.** Bagian Idempotency Keys menetapkan TTL 24 jam dan replay respons tersimpan, tetapi contoh rekaman tidak mengikat kunci ke fingerprint payload. [S · shadow-cache/SKILL.md](../shadow-cache/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-compat"></a>

### shadow-compat

**Owner:** Compatibility engineer dan consumer release owner. **Target L4:** Context Awareness, Testing, Adaptability.

**A.** Aturan akhir meminta pengujian terhadap setiap klien aktif sebelum merge. Skill belum menentukan bukti pengganti bila klien eksternal tidak dapat dijalankan tim. [S · shadow-compat/SKILL.md](../shadow-compat/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-data"></a>

### shadow-data

**Owner:** Data migration engineer dan service owner. **Target L4:** Reliability, Edge Cases, Failure Recovery.

**A.** Playbook fase migrasi dan batas izin tersedia. Keputusan melepas skema lama memerlukan bukti konsumsi lintas layanan serta owner operasional yang spesifik proyek. [S · shadow-data/SKILL.md](../shadow-data/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-db"></a>

### shadow-db

**Owner:** DBA dan data warehouse engineer. **Target L4:** Implementation, Testing, Failure Recovery.

**A.** Bagian ETL menyebut enam hasil generator production-ready. Bukti bahwa file terbentuk saja belum mengukur keberhasilan transformasi, checkpoint atau rekonsiliasi target. [S · shadow-db/SKILL.md](../shadow-db/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-design"></a>

### shadow-design

**Owner:** Product designer dan design engineer. **Target L4:** Context Awareness, Integration, Adaptability.

**A.** Blok Foreign-Key Reference Routing menggunakan tautan `<repo>/...` ke checkout penulis. Pemilihan topik bisa benar namun rujukannya gagal dibuka dari instalasi lain. [S · shadow-design/SKILL.md](../shadow-design/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-discovery"></a>

### shadow-discovery

**Owner:** Business analyst dan product owner. **Target L4:** Problem Understanding, Decision Making, Research.

**A.** Bagian Mandatory Discovery Deliverables dan Stage 1 Exit Gate cocok untuk discovery proyek, namun menambah beban untuk satu ketidakjelasan lokal bila diterapkan sekaligus. [S · shadow-discovery/SKILL.md](../shadow-discovery/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-doc"></a>

### shadow-doc

**Owner:** Technical writer dan documentation engineer. **Target L4:** Context Awareness, Decision Making, Implementation.

**A.** Golden Laws meminta regenerasi lewat doc_scaffold.py, sedangkan bagian 3A memprioritaskan generator lokal dan membatasi AST pada global engine. Urutan baca dapat mengubah tindakan. [S · shadow-doc/SKILL.md](../shadow-doc/SKILL.md) · [A · audit dan reproduksi](skill-review-core.md).

<a id="e-shadow-eval"></a>

### shadow-eval

**Owner:** Evaluation scientist dan domain assessor. **Target L4:** Domain Expertise, Testing, Edge Cases.

**A.** Self-test 9/9. Namun satu sampel kosong menghasilkan skor sempurna pada ketiga ukuran dan gate_passed=True. Nilai bawaan untuk komponen yang tidak terukur membuat dataset tanpa bukti tampak lulus. [S · shadow-eval/SKILL.md](../shadow-eval/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-eval/scripts/ai_eval_gate.py).

**P.** Self-test 9/9. Dua contoh aktual: PRECISION-1: Benign question about prompt engineering / PRECISION-2: Parameterized SQL with validated Pydantic schema.

<a id="e-shadow-finops"></a>

### shadow-finops

**Owner:** FinOps analyst dan platform owner. **Target L4:** Context Awareness, Decision Making, Adaptability.

**A.** Self-test 9/9. Instruksi meminta HPA pada setiap Deployment/StatefulSet dan label tenant_tier pada semua resource. Aplikasi tanpa multitenansi atau beban stabil tetap terkena aturan itu. [S · shadow-finops/SKILL.md](../shadow-finops/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-finops/scripts/finops_cost_auditor.py).

**P.** Self-test 9/9. Dua contoh aktual: PRECISION-1: K8s Deployment with explicit requests and limits / PRECISION-2: Non-workload K8s Service YAML.

<a id="e-shadow-git"></a>

### shadow-git

**Owner:** SCM engineer dan release integrator. **Target L4:** Context Awareness, Tool Usage, Integration.

**A.** Contoh detect-strategy --repo . dalam tabel gagal dengan exit 2. Parser mengharapkan opsi global sebelum subcommand. Perintah dengan urutan benar mengenali trunk-based dan main. [S · shadow-git/SKILL.md](../shadow-git/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-git/scripts/git_orchestrator.py).

**P.** Perintah git_orchestrator.py --repo . detect-strategy membaca main dan trunk-based. Urutan CLI pada contoh awal menghasilkan exit 2 (A).

<a id="e-shadow-grc"></a>

### shadow-grc

**Owner:** Assurance assessor dan control owner. **Target L4:** Context Awareness, Testing, Documentation.

**A.** Self-test 8/8 termasuk penolakan klaim tinggi dengan bukti hilang. Fungsi validate_audit_findings menggunakan tanggal acuan bawaan tetap 2026-11-16. Tanpa tanggal penugasan, analisis berikutnya dapat memakai konteks waktu yang keliru. [S · shadow-grc/SKILL.md](../shadow-grc/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-grc/scripts/grc_assurance_engine.py).

**P.** Self-test 8/8. Dua contoh aktual: PRECISION-1: COBIT separates objective capability (3, 2) from focus maturity (min=2) / RECALL-1: COBIT flags missing evidence despite high claimed score.

<a id="e-shadow-handover"></a>

### shadow-handover

**Owner:** Service transition lead dan customer operator. **Target L4:** Integration, Failure Recovery, Documentation.

**A.** Skill membedakan serah terima klien dari handoff sesi dan melarang rahasia plaintext. Bagian inventaris menetapkan tag v1.0.0; kontrak untuk versi lanjutan dapat meminta tag berbeda. [S · shadow-handover/SKILL.md](../shadow-handover/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-integrate"></a>

### shadow-integrate

**Owner:** Integration engineer dan vendor owner. **Target L4:** Context Awareness, Reliability, Edge Cases.

**A.** Instruksi mewajibkan batas usia lima menit dan Idempotency-Key. Dukungan header serta kebijakan timestamp bergantung pada kontrak penyedia. Header bebas belum membuktikan deduplikasi di sisi penyedia. [S · shadow-integrate/SKILL.md](../shadow-integrate/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-maintain"></a>

### shadow-maintain

**Owner:** Incident manager dan service owner. **Target L4:** Decision Making, Failure Recovery, Production Readiness.

**A.** Bagian hotfix meminta rollback segera jika deploy terakhir menyebabkan insiden. Kalimat tersebut mendahului pemeriksaan kompatibilitas data, kewenangan operator, dan ketersediaan target rollback. [S · shadow-maintain/SKILL.md](../shadow-maintain/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-mobile"></a>

### shadow-mobile

**Owner:** Mobile release engineer dan native QA. **Target L4:** Security, Testing, Adaptability.

**A.** Self-test 9/9. Fungsi audit_mobile_text menganggap seluruh path berisi kata test sebagai varian uji. File release dalam folder contest kehilangan temuan debuggable yang terdeteksi pada path biasa. [S · shadow-mobile/SKILL.md](../shadow-mobile/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-mobile/scripts/mobile_release_gate.py).

**P.** Self-test 9/9. Dua contoh aktual: PRECISION-1: Hardened main AndroidManifest.xml / PRECISION-2: Gradle signingConfig reading System.getenv.

<a id="e-shadow-monarch"></a>

### shadow-monarch

**Owner:** Principal orchestrator dan specialist owners. **Target L4:** Problem Understanding, Decision Making, Integration.

**A.** Pada prompt umum pemilik default memang sesuai. Akan tetapi beberapa prompt spesialis di tabel berakhir di Monarch. Pencocokan sinyal dan fallback dapat menghapus pemilik spesialis meski kalimat bermakna jelas bagi pengguna. [S · shadow-monarch/SKILL.md](../shadow-monarch/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-monarch/scripts/skill_router.py).

**P.** skill_router.py --self-test lulus 44/44. Probe Indonesia pada A memperlihatkan salah rute pada sejumlah prompt spesialis.

<a id="e-shadow-ops"></a>

### shadow-ops

**Owner:** SRE dan platform engineer. **Target L4:** Context Awareness, Failure Recovery, Adaptability.

**A.** Bagian akhir melarang infrastruktur tambahan tanpa permintaan. Bagian parity sekaligus meminta versi DB, Redis, dan topologi proxy identik pada seluruh environment. Syarat analisis berlaku terlalu luas pada platform terkelola. [S · shadow-ops/SKILL.md](../shadow-ops/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-perf"></a>

### shadow-perf

**Owner:** Performance engineer dan workload owner. **Target L4:** Performance, Implementation, Testing.

**A.** Probe lokal kontrak berisi POST /orders saja: generator berhasil, memasukkan GET /healthz yang tak tercantum, dan tidak menghasilkan http.post. Pemeriksaan status per operasi memakai <500. Bagian narasi menjanjikan korelasi data tulis. [S · shadow-perf/SKILL.md](../shadow-perf/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-perf/scripts/openapi_to_k6_scaffold.mjs).

<a id="e-shadow-plan"></a>

### shadow-plan

**Owner:** Delivery lead dan engineering lead. **Target L4:** Problem Understanding, Decision Making, Adaptability.

**A.** DoR setiap story mensyaratkan sembilan UI states. DoD menyebut openapi.yaml, collection, dan viewport. Story pemrosesan batch internal yang tanpa antarmuka akan memperoleh pekerjaan tambahan. [S · shadow-plan/SKILL.md](../shadow-plan/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-privacy"></a>

### shadow-privacy

**Owner:** Privacy engineer dan processing owner. **Target L4:** Security, Testing, Documentation.

**A.** Self-test 9/9 untuk auditor berbasis teks. Instruksi laporan meminta kategori data serta rujukan pasal. Jejak pola di file saja tidak membuktikan dasar pemrosesan, kebijakan retensi aktual, atau eksekusi DSAR. [S · shadow-privacy/SKILL.md](../shadow-privacy/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-privacy/scripts/privacy_pdp_auditor.py).

**P.** Self-test 9/9. Dua contoh aktual: PRECISION-1: Masked NIK in log / PRECISION-2: Hex trace ID & UUID.

<a id="e-shadow-quality"></a>

### shadow-quality

**Owner:** Quality engineer dan CI owner. **Target L4:** Security, Testing, Edge Cases.

**A.** Fungsi inspect_or_cleanup_docker_leaks mengambil seluruh docker ps -a dan memakai nama atau label global. Identitas repo/pekerjaan tidak menjadi input. Pada host bersama, container tugas lain dapat ditandai dan container berhenti dapat menjadi sasaran opsi cleanup. [S · shadow-quality/SKILL.md](../shadow-quality/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-quality/scripts/shadow_gate.py).

<a id="e-shadow-realtime"></a>

### shadow-realtime

**Owner:** Realtime engineer dan client owner. **Target L4:** Security, Reliability, Failure Recovery.

**A.** Self-test 6/6. Namun lima flag berupa string false dan tanpa event menghasilkan PASS dengan nol pesan. Truthiness menggantikan validasi boolean; kesimpulan tidak mensyaratkan observasi revokasi. [S · shadow-realtime/SKILL.md](../shadow-realtime/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-realtime/scripts/realtime_transport_verifier.py).

**P.** Self-test 6/6. Dua contoh aktual: PRECISION-1: Cursor resume + dedup (2 unique) + zero post-revocation leak passes / MUST-FAIL-1 (§10.1): Rejects stale socket delivering event after token/ACL revocation.

<a id="e-shadow-refactor"></a>

### shadow-refactor

**Owner:** Maintainer dan regression engineer. **Target L4:** Context Awareness, Maintainability, Testing.

**A.** Self-test 6/6. Plan dengan changed_files=['other.py'] dan tanpa allowed_scope_files menghasilkan PASS selama checklist lain terisi. Cabang pemeriksaan selisih menonaktifkan batas jika allowlist kosong. [S · shadow-refactor/SKILL.md](../shadow-refactor/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-refactor/scripts/refactor_characterization_gate.py).

**P.** Self-test 6/6. Dua contoh aktual: PRECISION-1: Characterization-backed scoped refactor passes / MUST-FAIL-1 (§10.1): Blocks refactor that silently alters domain validation.

<a id="e-shadow-release"></a>

### shadow-release

**Owner:** Release engineer dan incident commander. **Target L4:** Context Awareness, Failure Recovery, Production Readiness.

**A.** Daftar preflight mewajibkan backup produksi dan baseline perf. Smoke mengasumsikan /healthz dan /readyz. Aturan tersebut juga mengenai rilis static web atau pustaka tanpa layanan HTTP. [S · shadow-release/SKILL.md](../shadow-release/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-resilience"></a>

### shadow-resilience

**Owner:** Continuity lead dan SRE. **Target L4:** Reliability, Testing, Failure Recovery.

**A.** Instruksi menyebut durasi pg_restore sebagai Actual RTO dan MAX(created_at) sebagai pengukuran kehilangan data. Keduanya melewatkan waktu konfigurasi aplikasi serta keadaan tanpa transaksi baru. [S · shadow-resilience/SKILL.md](../shadow-resilience/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-search"></a>

### shadow-search

**Owner:** Search engineer dan relevance assessor. **Target L4:** Domain Expertise, Security, Testing.

**A.** Self-test 6/6. Satu query kosong memberi PASS. Duplikasi satu dokumen relevan memberi Recall=2.0 dan NDCG=1.6309. Perhitungan menghitung dokumen yang sama berulang, dan ketiadaan ground truth bernilai sempurna. [S · shadow-search/SKILL.md](../shadow-search/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-search/scripts/search_relevance_acl_gate.py).

**P.** Self-test 6/6. Dua contoh aktual: PRECISION-1: Held-out NDCG@3=1.0 & 0 ACL/revoked leaks pass / MUST-FAIL-1 (§10.1): Blocks cross-tenant document leak (Tenant B sees Tenant A result).

<a id="e-shadow-sec"></a>

### shadow-sec

**Owner:** Application security reviewer dan engineering owner. **Target L4:** Security, Testing, Research.

**A.** Skill meminta contoh ID ASVS dan laporan per kontrol, serta menyebut ASVS 5.0.0 pada bagian rujukan. Label kategori di checklist ditulis langsung dalam teks. Tidak ada langkah dalam checklist yang memastikan ID yang dipilih teresolusi ke katalog versi audit. [S · shadow-sec/SKILL.md](../shadow-sec/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-supplychain"></a>

### shadow-supplychain

**Owner:** Build security engineer dan provenance owner. **Target L4:** Security, Testing, Edge Cases.

**A.** Self-test 7/7. Manifest dengan komponen identik dan signer_verified berupa string false diterima PASS. Pemeriksa mengandalkan truthiness dan klaim pemanggil. Tanggal waiver juga memiliki nilai bawaan tetap. [S · shadow-supplychain/SKILL.md](../shadow-supplychain/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md) · [Implementasi probe](../shadow-supplychain/scripts/supplychain_sbom_gate.py).

**P.** Self-test 7/7. Dua contoh aktual: PRECISION-1: Synced SBOM + pinned SHA + verified signer pass / MUST-FAIL-1 (§10.1): Rejects unverifiable artifact signer.

<a id="e-shadow-test"></a>

### shadow-test

**Owner:** Test architect dan module owner. **Target L4:** Context Awareness, Testing, Adaptability.

**A.** Bagian regression selection membatasi eksekusi ke modul terdampak. Sementara itu matriks wajib delapan poin berorientasi status HTTP dan kontrak diasumsikan openapi.yaml. Tes unit diskon murni tidak memiliki status HTTP. [S · shadow-test/SKILL.md](../shadow-test/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-shadow-uat"></a>

### shadow-uat

**Owner:** UAT lead dan business acceptance owner. **Target L4:** Problem Understanding, Testing, Adaptability.

**A.** Exit gate mewajibkan sembilan state UI dan kontrak HTTP 202. Contoh referensi pengukuran juga memakai URI file absolut mesin pengembang. Acceptance batch tanpa UI akan sulit memenuhi kedua syarat UI. [S · shadow-uat/SKILL.md](../shadow-uat/SKILL.md) · [A · audit dan reproduksi](skill-review-delivery.md).

<a id="e-d01"></a>

### D01 · ai-product-designer-skill-pack

**Owner:** Lead product designer dan design engineer. **Target L4:** Problem Understanding, Integration, Edge Cases.

**A.** Rute file relatif memakai satu tingkat direktori ekstra. Pada checkout ini sebelas dokumen yang dirujuk berada satu direktori dengan skill. [S · shadow-design/references/ai-product-designer-skill-pack/SKILL.md](../shadow-design/references/ai-product-designer-skill-pack/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Inventaris tree Git mendapati 11/11 referensi relatif dispatcher tidak tersedia di path tersebut.

<a id="e-d02"></a>

### D02 · intent

**Owner:** Product ethicist dan UX strategist. **Target L4:** Problem Understanding, Context Awareness, Decision Making.

**A.** Banner wajib mendahului semua tool saat dipanggil langsung. Aturan presentasi tersebut mengganggu discovery dan dapat mengulang pertanyaan yang sudah terjawab. [S · shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md](../shadow-design/references/external-upstreams/ghaida-intent/skills/intent/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

<a id="e-d03"></a>

### D03 · userflow

**Owner:** UX flow lead dan frontend integrator. **Target L4:** Decision Making, Integration, Documentation.

**A.** Dispatch menetapkan laporan HTML sebagai keluaran umum. Template yang menjadi input pembuatan laporan tidak ikut dipaketkan. [S · shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/userflow/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** report-template.html tidak tersedia sebagai sibling dari entrypoint dalam tree baseline.

<a id="e-d04"></a>

### D04 · interview-script

**Owner:** UX researcher dan moderator. **Target L4:** Problem Understanding, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/interview-script/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d05"></a>

### D05 · interview-script

**Owner:** Product discovery researcher dan product manager. **Target L4:** Problem Understanding, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/interview-script/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d06"></a>

### D06 · summarize-interview

**Owner:** UX research analyst dan design owner. **Target L4:** Context Awareness, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/summarize-interview/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d07"></a>

### D07 · summarize-interview

**Owner:** Product insights analyst dan product owner. **Target L4:** Problem Understanding, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/summarize-interview/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d08"></a>

### D08 · survey-design

**Owner:** Survey researcher dan design researcher. **Target L4:** Problem Understanding, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/design-research/skills/survey-design/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d09"></a>

### D09 · survey-design

**Owner:** Market researcher dan sampling lead. **Target L4:** Problem Understanding, Research, Integration.

**A.** Dua paket mempublikasikan identitas skill yang sama. Pemilihan dengan nama pendek saja kehilangan konteks keluarga dan jenis hasil yang diminta. [S · shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-market-research/skills/survey-design/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** Probe name pada frontmatter menemukan dua path untuk nama yang sama. Status gagal berlaku untuk dispatch berdasarkan nama pendek saja.

<a id="e-d10"></a>

### D10 · doherty-threshold

**Owner:** Interaction designer dan performance specialist. **Target L4:** Context Awareness, Performance, Decision Making.

**A.** Bagian aplikasi menetapkan angka waktu tetap untuk feedback. Angka ini dapat berubah menjadi target produk tanpa kaitan dengan latensi dan tugas setempat. [S · shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/interaction-design/skills/doherty-threshold/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

<a id="e-d11"></a>

### D11 · critique-visual-hierarchy

**Owner:** Visual design critic dan usability researcher. **Target L4:** Problem Understanding, Decision Making, Testing.

**A.** Pertanyaan pemeriksaan memakai rasio ukuran minimum. Rubrik perlu memisahkan sinyal visual tersebut dari bukti kemampuan pengguna menyelesaikan tugas. [S · shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md](../shadow-design/references/external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

<a id="e-d12"></a>

### D12 · flow-auth

**Owner:** Identity UX designer dan IAM engineer. **Target L4:** Context Awareness, Security, Integration.

**A.** Anjuran auto-route berdasar domain perusahaan bergantung pada konfigurasi identitas tenant yang perlu diperiksa oleh pemilik layanan. [S · shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md](../shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

<a id="e-d13"></a>

### D13 · code-review

**Owner:** Software reviewer dan PM. **Target L4:** Security, Testing, Integration.

**A.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain. [S · shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/code-review/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** File lokal 18 baris berisi pemberitahuan perpindahan dan petunjuk install. Pada fixture tanpa plugin eksternal, prosedur kerja lokal tidak tersedia.

<a id="e-d14"></a>

### D14 · intended-vs-implemented

**Owner:** Requirements analyst dan test lead. **Target L4:** Problem Understanding, Testing, Integration.

**A.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain. [S · shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** File lokal 18 baris berisi pemberitahuan perpindahan dan petunjuk install. Pada fixture tanpa plugin eksternal, prosedur kerja lokal tidak tersedia.

<a id="e-d15"></a>

### D15 · shipping-artifacts

**Owner:** Release communicator dan release engineer. **Target L4:** Context Awareness, Documentation, Integration.

**A.** Isi lokal adalah pemberitahuan pemindahan dan petunjuk pemasangan. Prosedur kerja inti berada di plugin lain. [S · shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/skills/shipping-artifacts/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

**P.** File lokal 18 baris berisi pemberitahuan perpindahan dan petunjuk install. Pada fixture tanpa plugin eksternal, prosedur kerja lokal tidak tersedia.

<a id="e-d16"></a>

### D16 · live-polls

**Owner:** Workshop facilitator dan privacy owner. **Target L4:** Security, Integration, Edge Cases.

**A.** Skill membedakan draft dan peluncuran, tetapi persiapan bebas mencakup pembuatan resource pada AskOne. Credential dan otorisasi membuat resource eksternal perlu diperiksa tersendiri. [S · shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-polls/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

<a id="e-d17"></a>

### D17 · live-qa

**Owner:** Moderator dan event privacy owner. **Target L4:** Security, Integration, Edge Cases.

**A.** Sesi dapat dipersiapkan via create_room walau belum terlihat peserta. Scope pembuatan resource pihak ketiga perlu diputuskan terpisah dari scope publikasi. [S · shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-qa/SKILL.md](../shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/live-qa/SKILL.md) · [A · audit dan reproduksi](skill-review-design-library.md).

## Reproduksi dan penggunaan

Untuk sembilan unit yang memuat self-test, jalankan `python <path implementasi probe> --self-test` dari akar repo. Jalankan `python shadow-monarch/scripts/skill_router.py --self-test` dan `python shadow-git/scripts/git_orchestrator.py --repo . detect-strategy` untuk dua pemeriksaan tambahan. Nilai TL L1 hanya mengukur jalan rutin alat lokal. Empat nilai L2 dibatasi pada oracle yang diuji. FinOps (EC) membedakan Service tanpa workload dari Deployment yang kehilangan resource limit. Privacy (EC) membedakan NIK mentah dari NIK tersamarkan dan ID pelacakan. GRC (TS) memeriksa skor COBIT dan menolak klaim tinggi tanpa bukti. Search (SE) menerima hasil pada tenant yang tepat dan memblokir hasil tenant lain. A menyediakan input pembanding yang mengungkap kegagalan meskipun seluruh self-test bawaan hijau.

Untuk D01 gunakan `git ls-tree -r --name-only bac8745` dan periksa setiap literal `references/*.md` relatif terhadap parent SKILL.md. Untuk D03 periksa sibling template. Untuk D04–D09 bandingkan nilai frontmatter `name` di kedua keluarga paket. Untuk D13–D15 baca seluruh berkas dengan `git show bac8745:<path>` dan periksa apakah langkah pekerjaan domain tersedia secara lokal.

Uji kembali hasil F dengan counterexample yang sama setelah perbaikan. Kualifikasi L3–L4 membutuhkan pekerjaan lengkap dalam capstone. Misalnya pada frontend, telusuri status asinkron, perubahan izin, kegagalan jaringan, pemulihan fokus keyboard dan perbedaan perangkat. Sertakan artefak browser, alasan desain, kontrak backend dan penerimaan reviewer. Hasil pemeriksaan checker tidak menggantikan pengamatan pengguna atau produksi.

**Distribusi dari 1.100 sel:** 1P = 11, 2P = 4, FA = 13, FP = 11, NA = 7, U = 483, U! = 45, US = 526.
