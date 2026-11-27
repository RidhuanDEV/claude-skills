# Third-party notices

Original Shadow Army content is MIT-licensed (see [LICENSE](LICENSE)). The files below come from other projects and keep their own licenses. **The repository's MIT grant does not cover them.**

| Location | Upstream | License | Provenance |
| --- | --- | --- | --- |
| `shadow-ops/references/vendor/OWASP_*_Cheat_Sheet.md` (5 files) | [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) | **CC BY-SA 4.0**: attribution and share-alike; adaptations must stay CC BY-SA 4.0 | [VENDOR.json](shadow-ops/references/vendor/VENDOR.json) · [LICENSES.md](shadow-ops/references/vendor/LICENSES.md) |
| `shadow-ops/references/vendor/H5BP_nginx_*.conf` (3 files) | [h5bp/server-configs-nginx](https://github.com/h5bp/server-configs-nginx) | MIT, Copyright (c) H5BP | same as above |
| `shadow-test/references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md` | [goldbergyoni/javascript-testing-best-practices](https://github.com/goldbergyoni/javascript-testing-best-practices) | MIT, Copyright (c) 2019 Yoni Goldberg | [VENDOR.json](shadow-test/references/vendor/VENDOR.json) · [LICENSES.md](shadow-test/references/vendor/LICENSES.md) |
| `shadow-design/references/external-upstreams/*` | ghaida/intent (CC0 1.0), jpoindexter/ux-flow-skills, phuryn/pm-skills, Owl-Listener/designer-skills (MIT) | as listed in each `LICENSE.txt` | [UPSTREAM_PROVENANCE.json](shadow-design/UPSTREAM_PROVENANCE.json) |
| `antislop-human`, `antislop-ui` (web-quality components) | [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) | MIT | `LICENSE-web-quality-skills` in each folder |

## Open item

The primary `shadow-design` reference pack (`ai-product-designer-skill-pack`) was imported from a local folder. `UPSTREAM_PROVENANCE.json` records it as vendor-authored but names no license.

**Decision (2026-11-28):** until its owner documents a license, or confirms that it is original work of the repository owner, the pack is treated as **internal use only**. It is excluded from the MIT grant and must not be redistributed or published with this repository. When a license is confirmed, record it here and in `UPSTREAM_PROVENANCE.json`.

Upstream revisions of the `shadow-ops` and `shadow-test` vendor files were not recorded when the files were vendored. `VENDOR.json` pins the current SHA-256, and `evals/test_vendor_provenance.py` fails if a file changes without its lock being updated.
