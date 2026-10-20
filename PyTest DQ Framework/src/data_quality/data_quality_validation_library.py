from __future__ import annotations

from typing import Iterable

import pandas as pd


class DataQualityLibrary:
    """Reusable assertions for data-quality checks in PyTest."""

    @staticmethod
    def _normalize_for_compare(df: pd.DataFrame) -> pd.DataFrame:
        ordered = df.copy()
        for column in ordered.columns:
            if pd.api.types.is_datetime64_any_dtype(ordered[column]):
                ordered[column] = ordered[column].dt.strftime("%Y-%m-%d")
        return ordered.sort_values(by=list(ordered.columns), na_position="last").reset_index(drop=True)

    @staticmethod
    def check_dataset_is_not_empty(df: pd.DataFrame) -> None:
        assert isinstance(df, pd.DataFrame), "Expected a pandas DataFrame."
        assert not df.empty, "Dataset is empty."

    @staticmethod
    def check_count(source_df: pd.DataFrame, target_df: pd.DataFrame) -> None:
        assert len(source_df) == len(target_df), (
            f"Row count mismatch: source={len(source_df)}, target={len(target_df)}"
        )

    @staticmethod
    def check_data_completeness(source_df: pd.DataFrame, target_df: pd.DataFrame) -> None:
        expected = DataQualityLibrary._normalize_for_compare(source_df)
        actual = DataQualityLibrary._normalize_for_compare(target_df)

        expected_columns = list(expected.columns)
        actual_columns = list(actual.columns)
        assert expected_columns == actual_columns, (
            f"Column mismatch: source={expected_columns}, target={actual_columns}"
        )

        pd.testing.assert_frame_equal(expected, actual, check_dtype=False)

    @staticmethod
    def check_duplicates(df: pd.DataFrame, column_names: Iterable[str] | None = None) -> None:
        subset = list(column_names) if column_names else None
        duplicate_rows = df.duplicated(subset=subset, keep=False)
        assert not duplicate_rows.any(), f"Duplicate records found: {df[duplicate_rows].head()}"

    @staticmethod
    def check_not_null_values(df: pd.DataFrame, column_names: Iterable[str]) -> None:
        required_columns = list(column_names)
        missing = [column for column in required_columns if column not in df.columns]
        assert not missing, f"Missing columns in parquet dataset: {missing}"
        null_mask = df[required_columns].isna().any(axis=1)
        assert not null_mask.any(), f"Null values found in required columns: {df.loc[null_mask, required_columns].head()}"
