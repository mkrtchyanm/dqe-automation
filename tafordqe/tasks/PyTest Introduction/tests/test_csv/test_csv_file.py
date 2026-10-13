from __future__ import annotations

import re
from collections import Counter

import pytest

EXPECTED_SCHEMA = ["id","name","age","email","is_active"]
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def test_csv_file_is_not_empty(csv_content: list[dict[str, str]]) -> None:
    assert len(csv_content) > 0, "The CSV file is empty"


@pytest.mark.validate_csv
def test_csv_schema_is_valid(
    csv_content: list[dict[str, str]], validate_schema
) -> None:
    actual_schema = list(csv_content[0].keys()) if csv_content else []
    validate_schema(actual_schema, EXPECTED_SCHEMA)


@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age validation is intentionally skipped for this exercise(mentioned in the task that we need to use skip marker)")
def test_age_column_contains_valid_values(csv_content: list[dict[str, str]]) -> None:
    for row in csv_content:
        age = int(row["age"])
        assert 0 <= age <= 100, (
            f"Expected age between 0 and 100, got {age} for row id={row['id']}"
        )


@pytest.mark.validate_csv
def test_email_column_contains_valid_email_addresses(
    csv_content: list[dict[str, str]]
) -> None:
    for row in csv_content:
        assert EMAIL_PATTERN.match(row["email"]), (
            f"Expected a valid email address for row id={row['id']}, got {row['email']}"
        )


@pytest.mark.validate_csv
@pytest.mark.xfail(reason="The CSV contains a known duplicate row(besides that we  need to use this marker)")
def test_csv_contains_no_duplicate_rows(csv_content: list[dict[str, str]]) -> None:
    row_values = [tuple(row[column] for column in EXPECTED_SCHEMA) for row in csv_content]
    duplicates = [row for row, count in Counter(row_values).items() if count > 1]
    assert not duplicates, f"Expected no duplicate rows, found duplicates: {duplicates}"


@pytest.mark.validate_csv
@pytest.mark.parametrize(
    "row_id, expected_is_active",
    [(1, "False"), (2, "True")], # the id=2 has FALSE in the CSV file I didnt change it to TRUE because our intend is to test the csv and find the issues not fix the issues
)
def test_is_active_matches_expected_value(
    csv_content: list[dict[str, str]], row_id: int, expected_is_active: str
) -> None:
    row = next((item for item in csv_content if item["id"] == str(row_id)), None)
    assert row is not None, f"Expected to find a row with id={row_id}"
    assert row["is_active"] == expected_is_active, (
        f"Expected is_active for id={row_id} to be {expected_is_active}, got {row['is_active']}"
    )


@pytest.mark.validate_csv
def test_is_active_for_id_2_matches_expected_value(
    csv_content: list[dict[str, str]]
) -> None:
    row = next((item for item in csv_content if item["id"] == "2"), None)
    assert row is not None, "Expected to find a row with id=2"
    assert row["is_active"] == "True", (
        f"Expected is_active for id=2 to be True, got {row['is_active']}"
    )
