from __future__ import annotations

import csv
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def path_to_file() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "data" / "data.csv"


@pytest.fixture(scope="session")
def csv_content(path_to_file: Path) -> list[dict[str, str]]:
    with path_to_file.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


@pytest.fixture(scope="session")
def validate_schema():
    def _validate_schema(actual_schema: list[str], expected_schema: list[str]) -> None:
        assert actual_schema == expected_schema, (
            f"Expected schema {expected_schema}, got {actual_schema}"
        )

    return _validate_schema


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if not item.own_markers:
            item.add_marker(pytest.mark.unmarked)
