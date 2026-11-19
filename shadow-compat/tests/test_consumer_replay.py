"""Fixture of an historical strict desktop client versus a tolerant reader."""
import unittest


def read_v1(page, strict):
    expected = {"rows", "next"}
    if strict and page.keys() != expected:
        raise ValueError("unexpected envelope")
    if "next" not in page:
        raise ValueError("missing cursor")
    return [r["id"] for r in page["rows"]], page["next"]


class ClientReplay(unittest.TestCase):
    def setUp(self):
        self.old = {"rows": [{"id": "9"}, {"id": "2"}], "next": None}

    def test_additive_field_breaks_strict_external_client(self):
        candidate = dict(self.old, count=2)
        self.assertEqual(read_v1(self.old, False), read_v1(candidate, False))
        with self.assertRaises(ValueError):
            read_v1(candidate, True)

    def test_field_shape_acceptance_misses_changed_order(self):
        candidate = dict(self.old, rows=list(reversed(self.old["rows"])))
        old_ids, _ = read_v1(self.old, True)
        new_ids, _ = read_v1(candidate, True)
        self.assertNotEqual(old_ids, new_ids)

    def test_omitted_cursor_is_not_null(self):
        candidate = {"rows": self.old["rows"]}
        with self.assertRaisesRegex(ValueError, "missing cursor"):
            read_v1(candidate, False)
