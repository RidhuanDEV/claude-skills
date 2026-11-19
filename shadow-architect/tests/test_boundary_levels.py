from __future__ import annotations

import unittest


def recommend_architecture_topology(
    *,
    team_count: int,
    independent_scaling_proven: bool,
    shared_acid_transactions: bool,
    regulatory_isolation_required: bool,
) -> dict[str, object]:
    if not independent_scaling_proven and not regulatory_isolation_required and team_count <= 3:
        return {
            "topology": "modular_monolith",
            "rejected": ["microservices"],
            "reason": "Single deployable unit with strict module boundaries avoids distributed transaction overhead.",
        }
    if shared_acid_transactions and not regulatory_isolation_required:
        return {
            "topology": "modular_monolith_with_worker",
            "rejected": ["microservices"],
            "reason": "Keep ACID write invariants inside one transactional store; isolate only async workers.",
        }
    return {
        "topology": "bounded_split_services",
        "rejected": [],
        "reason": "Proven independent scaling or regulatory isolation justifies split deployment.",
    }


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_c05_prefers_modular_monolith_before_split_deployment(self) -> None:
        small = recommend_architecture_topology(
            team_count=2,
            independent_scaling_proven=False,
            shared_acid_transactions=True,
            regulatory_isolation_required=False,
        )
        self.assertEqual(small["topology"], "modular_monolith")
        self.assertIn("microservices", small["rejected"])

        regulated = recommend_architecture_topology(
            team_count=6,
            independent_scaling_proven=True,
            shared_acid_transactions=False,
            regulatory_isolation_required=True,
        )
        self.assertEqual(regulated["topology"], "bounded_split_services")


if __name__ == "__main__":
    unittest.main()
