"""The identifier router must catch codes and citations and leave ordinary Indonesian text alone."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "identifier_query_router.py"
SPEC = importlib.util.spec_from_file_location("identifier_query_router", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(SCRIPT)
router = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = router
SPEC.loader.exec_module(router)


class IdentifierQueryRouterTests(unittest.TestCase):
    def test_self_test_probes_pass(self) -> None:
        self.assertEqual(router.self_test(), [])

    def test_spellings_of_one_regulation_normalize_to_one_term(self) -> None:
        spellings = ["PP-27/2022", "pp 27/2022", "PP 27 / 2022"]
        terms = {router.route_query(value).normalized for value in spellings}
        self.assertEqual(terms, {("pp272022",)})

    def test_years_dates_and_quantities_are_not_identifiers(self) -> None:
        for query in ("laporan tahun 2022", "rapat tanggal 12/05", "beras 5 kg", "halaman 2"):
            with self.subTest(query=query):
                self.assertEqual(router.route_query(query).identifiers, ())

    def test_negations_stay_in_the_text_branch(self) -> None:
        routed = router.route_query("INV-8841-ID tidak terkirim")
        self.assertEqual(routed.normalized, ("inv8841id",))
        self.assertEqual(routed.text, "tidak terkirim")

    def test_mixed_query_keeps_both_identifiers_in_order(self) -> None:
        routed = router.route_query("bandingkan PP-27/2022 dengan Perpres 46/2025 untuk SKU123")
        self.assertEqual(routed.normalized, ("pp272022", "perpres462025", "sku123"))
        self.assertEqual(routed.text, "bandingkan dengan untuk")


if __name__ == "__main__":
    unittest.main()
