"""Export expected results from golden validation cases."""
import json
import os
from validation.test_cases.test_definitions import load_all_test_cases

if __name__ == "__main__":
    cases = load_all_test_cases()
    expected = {}
    for c in cases:
        expected[c["test_id"]] = {
            "calc_type": c["calc_type"],
            "methodology": c["methodology"],
            "intermediate": c.get("intermediate_results", {}),
            "expected_final": c.get("expected_final_result", {}),
            "expected_units": c.get("expected_units"),
            "tolerance": c.get("tolerance", 1e-5),
            "is_invalid": c.get("is_invalid", False),
            "expected_error": c.get("expected_error"),
        }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expected_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(expected, f, indent=2)
    print(f"Exported expected results for {len(expected)} cases to {out_path}")
