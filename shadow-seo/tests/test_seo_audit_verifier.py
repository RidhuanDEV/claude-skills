from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import seo_audit_verifier as seo


class SeoAuditVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = seo.run_self_test()
        self.assertTrue(res["all_passed"], json.dumps(res, indent=2))

    def test_staging_without_noindex_is_flagged(self) -> None:
        res = seo.validate_ssr_seo_page(
            {
                "url": "https://staging.example.com/",
                "environment": "staging",
                "has_noindex": False,
                "title": "Staging Site Home Page Title",
                "meta_description": "Staging site description that is long enough to satisfy length check.",
                "canonical_url": "https://staging.example.com/",
                "h1_count": 1,
                "valid_jsonld_count": 1,
            }
        )
        self.assertFalse(res["passed"])
        self.assertTrue(any("non-production host" in e for e in res["errors"]))

    def test_valid_production_page_passes(self) -> None:
        res = seo.validate_ssr_seo_page(
            {
                "url": "https://example.com/id/produk",
                "environment": "production",
                "has_noindex": False,
                "title": "Katalog Produk Enterprise Terlengkap",
                "meta_description": "Jelajahi katalog produk enterprise bergaransi resmi dengan pengiriman nasional.",
                "canonical_url": "https://example.com/id/produk",
                "h1_count": 1,
                "valid_jsonld_count": 2,
            }
        )
        self.assertTrue(res["passed"], res["errors"])


if __name__ == "__main__":
    unittest.main()
