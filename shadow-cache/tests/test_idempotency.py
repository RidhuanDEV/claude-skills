"""Executable SQLite reference for transactional, tenant-scoped idempotency."""
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path


class IdempotencyCases(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.path = Path(root.name) / "orders.db"
        db = sqlite3.connect(self.path)
        self.addCleanup(db.close)
        db.executescript("""
            CREATE TABLE orders (id INTEGER PRIMARY KEY, amount INTEGER);
            CREATE TABLE receipts (tenant TEXT, principal TEXT, token TEXT, digest TEXT, order_id INTEGER,
                                   PRIMARY KEY (tenant, principal, token));
        """)
        self.db = db

    def order(self, amount=100, tenant="A", principal="P", allowed=True, abort=False):
        if not allowed:
            return "forbidden", None
        # The operation owns this table. The amount is the sole validated business input.
        digest = sha256(json.dumps({"amount": amount}).encode()).hexdigest()
        db = sqlite3.connect(self.path)
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                key = (tenant, principal, "retry-key")
                row = db.execute("SELECT digest, order_id FROM receipts WHERE tenant=? AND principal=? AND token=?", key).fetchone()
                if row:
                    return ("replayed", row[1]) if row[0] == digest else ("conflict", None)
                order_id = db.execute("INSERT INTO orders (amount) VALUES (?)", (amount,)).lastrowid
                if abort:
                    raise RuntimeError("interrupted before receipt")
                db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?)", (*key, digest, order_id))
                return "created", order_id
        finally:
            db.close()

    def test_concurrent_retry_commits_once(self):
        barrier = threading.Barrier(2)
        def submit():
            barrier.wait(timeout=3)
            return self.order()
        with ThreadPoolExecutor(2) as executor:
            futures = [executor.submit(submit) for _ in range(2)]
            results = sorted(f.result() for f in futures)
        self.assertEqual(results, [("created", 1), ("replayed", 1)])
        self.assertEqual(self.db.execute("SELECT count(*) FROM orders").fetchone(), (1,))

    def test_changed_payload_and_authority(self):
        self.order()
        self.assertEqual(self.order(amount=101), ("conflict", None))
        self.assertEqual(self.order(allowed=False), ("forbidden", None))
        self.assertEqual(self.order(tenant="B"), ("created", 2))
        self.assertEqual(self.order(principal="Q"), ("created", 3))

    def test_interruption_before_commit_and_lost_reply_after_commit(self):
        with self.assertRaises(RuntimeError):
            self.order(abort=True)
        self.assertEqual(self.db.execute("SELECT count(*) FROM orders").fetchone(), (0,))
        self.order()
        self.assertEqual(self.order(), ("replayed", 1))
