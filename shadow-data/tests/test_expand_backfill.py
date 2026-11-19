"""Exercise one additive SQLite migration with mixed-version writers."""
import sqlite3
import unittest


class ExpandBackfill(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE orders(id INTEGER PRIMARY KEY, cents INTEGER NOT NULL);
            INSERT INTO orders VALUES (1, 10), (2, 20), (3, 30);
            ALTER TABLE orders ADD COLUMN minor_units INTEGER;
            CREATE TABLE checkpoint(last_id INTEGER NOT NULL);
            INSERT INTO checkpoint VALUES (0);
        """)

    def batch(self, interrupt=False):
        with self.db:
            pos, = self.db.execute("SELECT last_id FROM checkpoint").fetchone()
            ids = self.db.execute("SELECT id FROM orders WHERE id>? ORDER BY id LIMIT 2", (pos,)).fetchall()
            for key in ids:
                self.db.execute("UPDATE orders SET minor_units=cents WHERE id=?", key)
            if interrupt:
                raise RuntimeError("worker lost")
            if ids:
                self.db.execute("UPDATE checkpoint SET last_id=?", ids[-1])
        return len(ids)

    def mismatch(self):
        return self.db.execute("SELECT id FROM orders WHERE minor_units IS NOT cents ORDER BY id").fetchall()

    def test_interrupted_batch_is_replayable(self):
        with self.assertRaises(RuntimeError):
            self.batch(interrupt=True)
        self.assertEqual(self.mismatch(), [(1,), (2,), (3,)])
        self.assertEqual([self.batch(), self.batch(), self.batch()], [2, 1, 0])
        self.assertEqual(self.mismatch(), [])

    def test_high_water_mark_misses_legacy_writer(self):
        self.batch()
        self.db.execute("UPDATE orders SET cents=12 WHERE id=1")
        self.batch()
        self.assertEqual(self.batch(), 0)
        self.assertEqual(self.mismatch(), [(1,)])
        # Install a compatibility writer before reconciliation and the read switch.
        self.db.executescript("""
            CREATE TRIGGER sync_old_writer AFTER UPDATE OF cents ON orders
            BEGIN UPDATE orders SET minor_units=NEW.cents WHERE id=NEW.id; END;
            UPDATE orders SET minor_units=cents WHERE minor_units IS NOT cents;
            UPDATE orders SET cents=13 WHERE id=1;
        """)
        self.assertEqual(self.mismatch(), [])
