---
name: generate-parquet-dq-tests
description: >-
  Generates one parquet dataset DQ test module per mapping entry from the project data-mapping document, using the PyTest DQ framework fixtures and data-quality library without copying pipeline SQL.
disable-model-invocation: true
---

# Generate Parquet DQ tests

Complete this skill as Step 2 of the PyTest DQ assignment. Read first:

- `PyTest DQ Framework/docs/test-automation-strategy.md` — Skill contract and test design standard
- `docs/parquet-aggregated-data-mapping.md` — source for expected grain, columns, joins, and aggregate logic

This skill creates dataset-specific Parquet validation modules only after the framework exists. It does not create the framework itself, and it never copies expected SQL from `data_dev/`.

## When this skill applies

Use this skill only when all of the following are true:

- The PyTest DQ Framework already exists and is implemented from the design document.
- The test suite is organized under `PyTest DQ Framework/tests/`.
- The Parquet mapping file exists at `docs/parquet-aggregated-data-mapping.md`.
- The requested output is one test module per dataset in `PyTest DQ Framework/tests/dq checks/parquet_files/`.

Refuse this skill if the user asks for:

- Framework creation or Jenkins config changes.
- `conftest.py`, `pytest.ini`, connectors, or DQ library edits.
- Rewriting expected SQL to make the test pass.
- Copying SQL from `data_dev/queries.py`, `data_dev/src/data/parquet_loader.py`, or any pipeline implementation file.

## Inputs you must have

Before generating a module, confirm all inputs are available:

1. Dataset name and parquet folder path, for example `/parquet_data/<dataset_name>`.
2. The mapping row(s) for that dataset from `docs/parquet-aggregated-data-mapping.md`.
3. The source table, join key, grain, aggregate measure, and not-null columns from that mapping.
4. The project fixture names from the framework: `db_connection`, `parquet_reader`, and `data_quality_library`.

If the mapping is missing or incomplete, stop and ask for the mapping before writing the test module. Do not infer SQL from pipeline code or from the generated parquet preview.

Forbidden sources:

- `data_dev/queries.py`
- `data_dev/src/data/parquet_loader.py`
- any ETL transformation SQL or loader code
- ad-hoc “expected result” SQL created after reading the parquet output

## Hard rules

1. The module path must be `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`.
2. The source data fixture must use PostgreSQL and the target data fixture must read the parquet dataset under `/parquet_data/<dataset_name>` using `include_subfolders=True`.
3. Use the mapping as the source of truth for expected SQL. Do not copy or reuse pipeline SQL from `data_dev/`.
4. The skill itself must never embed concrete expected SQL for the three named datasets.
5. Tests must call framework library methods; they must not contain custom pandas logic in the test body.
6. Markers must be used exactly as required: `@pytest.mark.parquet_data`, a dataset-specific mark, and `@pytest.mark.smoke` only on the empty-check test.
7. Use the mapped output columns as the not-null list for that dataset.
8. Each module must include smoke, completeness, count, uniqueness, and not-null checks.
9. The module must fail for real transformation defects; it must not be an always-pass trivial check.

## Workflow

1. Read the mapping row for the dataset and capture the grain, measure, source table(s), join keys, and output columns.
2. Derive the expected SQL from the mapping only: source tables + join keys + grouping + aggregate expression + alias names.
3. Build a module using the framework fixtures and the library methods.
4. Put the test file in the parquet_files folder with the correct dataset name.
5. Add dataset markers and the smoke marker to the empty-check test only.
6. Check that the check list is complete: smoke, completeness, count, uniqueness, not-null.
7. Do not run the suite unless the user explicitly asks to do so.

## Template

Use the following module skeleton and fill placeholders from the mapping. Do not swap the source and target fixtures.

```python
"""
Description: Data Quality checks for <dataset_name> dataset.
Requirement(s): TICKET-1234
Author(s): <name>
"""

import pytest


@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    -- expected query derived from mapping only
    -- include grain, joins, group by, aggregate, mapped aliases
    """
    return db_connection.get_data_sql(source_query)


@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/<dataset_name>'
    return parquet_reader.process(target_path, include_subfolders=True)


@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.<dataset_name>
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_data_completeness(source_data, target_data, data_quality_library):
    data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_uniqueness(target_data, data_quality_library):
    data_quality_library.check_duplicates(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(target_data, ['<col_1>', '<col_2>', '<col_3>'])
```

## SQL derivation (generic)

Keep this generic and mapping-driven:

- Start from the mapped group-by grain and identify the source tables.
- Join the source tables using the mapping keys or the documented relation between the tables.
- Add only filters that are explicitly stated in the mapping.
- Apply the aggregate expression in the mapping, preserving the alias names used in the parquet output.
- Cast or round only when the mapping says to do so.
- Confirm the final output columns and ordering follow the mapping names.
- Stop once the mapping is represented; do not add ETL-only logic.

## After generation

- Keep the generated tests focused on the mapping and framework contract.
- Do not rewrite expected SQL to force a green run.
- Only run pytest when the user asks for execution, validation, or a CI run.

---

## Skill review (self-check before Step 3)

Reject your own skill if any of these are true:

- [ ] Contains concrete expected SQL for `facility_name_min_time_spent_per_visit_date`, `facility_type_avg_time_spent_per_visit_date`, or `patient_sum_treatment_cost_per_facility_type`
- [ ] Tells the agent to use `data_dev/` or parquet loader SQL
- [ ] Omits completeness, count, uniqueness, or not-null
- [ ] Swaps Postgres vs Parquet fixtures or generates trivial always-pass checks
- [ ] Any section still says `TODO`
