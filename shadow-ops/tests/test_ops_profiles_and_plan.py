from __future__ import annotations

import unittest


def select_ops_profile(workload_kind: str) -> dict[str, object]:
    if workload_kind == "static_site":
        return {"requires_db_backup": False, "requires_statefulset": False, "components": ["cdn_or_nginx", "tls"]}
    return {"requires_db_backup": True, "requires_statefulset": True, "components": ["reverse_proxy", "app", "db_backup_321", "tls"]}


def detect_circular_dependencies(tasks: dict[str, list[str]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_nodes: list[str] = []

    def dfs(node: str) -> None:
        visiting.add(node)
        for dep in tasks.get(node, []):
            if dep in visiting:
                cycle_nodes.append(f"{node}->{dep}")
            elif dep not in visited:
                dfs(dep)
        visiting.remove(node)
        visited.add(node)

    for task_id in sorted(tasks.keys()):
        if task_id not in visited:
            dfs(task_id)
    return cycle_nodes


class OpsProfileAndSprintPlanTests(unittest.TestCase):
    def test_t10_separates_static_vs_stateful_ops_profiles(self) -> None:
        static_p = select_ops_profile("static_site")
        stateful_p = select_ops_profile("stateful_api")
        self.assertFalse(static_p["requires_db_backup"])
        self.assertTrue(stateful_p["requires_db_backup"])

    def test_t12_detects_circular_task_dependencies_in_headless_batch_plan(self) -> None:
        acyclic = {"T1": [], "T2": ["T1"], "T3": ["T2"]}
        self.assertEqual(detect_circular_dependencies(acyclic), [])

        cyclic = {"T1": ["T3"], "T2": ["T1"], "T3": ["T2"]}
        cycles = detect_circular_dependencies(cyclic)
        self.assertTrue(len(cycles) >= 1)


if __name__ == "__main__":
    unittest.main()
