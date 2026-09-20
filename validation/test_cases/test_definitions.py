"""Test case accessors for golden validation dataset."""
import json
import os

GOLDEN_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "golden_dataset",
    "golden_cases.json",
)


def load_all_test_cases():
    with open(GOLDEN_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_test_cases_by_category(category_code):
    cases = load_all_test_cases()
    return [c for c in cases if c.get("category_code") == category_code]


def get_test_case_by_id(test_id):
    cases = load_all_test_cases()
    for c in cases:
        if c.get("test_id") == test_id:
            return c
    return None
