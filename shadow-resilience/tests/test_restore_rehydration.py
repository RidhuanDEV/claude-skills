from __future__ import annotations

import copy
import unittest


class RestoreRehydrationTests(unittest.TestCase):
    def test_e08_restore_replays_tombstones_preserves_legal_hold_and_rebuilds_cache_and_search(self) -> None:
        # 1. Pre-erasure snapshot taken at T0
        db_t0 = {
            "u-erase": {"tenant": "t1", "name": "Budi Erasure", "legal_hold": False},
            "u-hold": {"tenant": "t1", "name": "Sari LegalHold", "legal_hold": True},
            "u-keep": {"tenant": "t1", "name": "Andi Active", "legal_hold": False},
        }
        snapshot_t0 = copy.deepcopy(db_t0)

        # 2. Post-snapshot erasure request arrives at T1 for u-erase and u-hold
        tombstone_log: list[dict[str, object]] = [
            {"version": 2, "user_id": "u-erase", "action": "ERASE"},
            {"version": 3, "user_id": "u-hold", "action": "ERASE"},
        ]

        # 3. Disaster occurs -> restore from T0 snapshot (which temporarily resurrects erased data!)
        restored_db = copy.deepcopy(snapshot_t0)
        stale_cache = {"u-erase": "cached-budi", "u-hold": "cached-sari", "u-keep": "cached-andi"}
        search_index = {uid: rec["name"] for uid, rec in restored_db.items()}

        # 4. Replay versioned tombstones respecting legal holds, invalidate cache, rebuild search
        erased_ids: set[str] = set()
        blocked_legal_hold: set[str] = set()
        for entry in sorted(tombstone_log, key=lambda item: int(item["version"])):
            uid = str(entry["user_id"])
            rec = restored_db.get(uid)
            if not rec:
                continue
            if rec["legal_hold"]:
                blocked_legal_hold.add(uid)
            else:
                del restored_db[uid]
                stale_cache.pop(uid, None)
                erased_ids.add(uid)

        # Rebuild search index from post-tombstone authoritative DB
        search_index = {uid: rec["name"] for uid, rec in restored_db.items()}

        self.assertIn("u-erase", erased_ids)
        self.assertNotIn("u-erase", restored_db)
        self.assertNotIn("u-erase", stale_cache)
        self.assertNotIn("u-erase", search_index)

        self.assertIn("u-hold", blocked_legal_hold)
        self.assertIn("u-hold", restored_db)
        self.assertIn("u-hold", search_index)
        self.assertIn("u-keep", search_index)


if __name__ == "__main__":
    unittest.main()
