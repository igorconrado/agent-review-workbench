import json
from collections import Counter
from pathlib import Path

from workbench.policy import Evidence, propose


def test_versioned_dataset_has_balanced_disjoint_partitions():
    cases = json.loads(Path("datasets/operational-v1.json").read_text())
    assert len(cases) == len({case["id"] for case in cases}) == 60
    assert Counter(case["split"] for case in cases) == {"development": 42, "final": 18}
    assert set(Counter(case["category"] for case in cases).values()) == {10}
    for case in cases:
        assert propose(Evidence.model_validate(case["evidence"])).kind == case["expected_action"]
