from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
from robot.api import logger
from robot.api.deco import keyword
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def _convert_column_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
            if pd.api.types.is_float_dtype(df[col]):
                df[col] = df[col].round(2)
        except (ValueError, TypeError):
            pass
    return df


@keyword("Read HTML Table Data")
def read_html_table_data(table_element: Any) -> pd.DataFrame:
    import time
    logger.info("Starting HTML table data extraction...")

    # Case 1 is Plotly SVG Table (contains .y-column elements)
    # Retrying up to 5 times in case client-side JavaScript is still rendering cells
    df = None
    for attempt in range(5):
        y_columns = table_element.find_elements(By.CSS_SELECTOR, ".y-column")
        if y_columns:
            logger.info(f"Detected Plotly table with {len(y_columns)} columns (attempt {attempt + 1}).")
            table_data = {}
            for col_idx, col in enumerate(y_columns):
                # Locate column header
                header_elems = col.find_elements(By.ID, "header")
                if header_elems:
                    header_text = header_elems[0].text.strip()
                else:
                    header_text = f"Column_{col_idx + 1}"

                cell_blocks = col.find_elements(By.CLASS_NAME, "column-cell")
                ordered_cell_values = []

                for cb in cell_blocks:
                    try:
                        gparent = cb.find_element(By.XPATH, "../..")
                        # Exclude the header row container
                        if gparent.get_attribute("id") == "header":
                            continue

                        # Extract vertical translate offsets to maintain correct visual row order
                        gp_tr = gparent.get_attribute("transform") or ""
                        cb_tr = cb.get_attribute("transform") or ""
                        gp_match = re.search(r'translate\(\s*[\d\.\-]+\s*,\s*([\d\.\-]+)\s*\)', gp_tr)
                        cb_match = re.search(r'translate\(\s*[\d\.\-]+\s*,\s*([\d\.\-]+)\s*\)', cb_tr)

                        gp_y = float(gp_match.group(1)) if gp_match else 0.0
                        cb_y = float(cb_match.group(1)) if cb_match else 0.0
                        total_y = gp_y + cb_y

                        text_elem = cb.find_element(By.CLASS_NAME, "cell-text")
                        ordered_cell_values.append((total_y, text_elem.text.strip()))
                    except Exception:
                        continue

                # Sort values by their vertical display position (Y coordinate)
                ordered_cell_values.sort(key=lambda item: item[0])
                column_values = [val for _, val in ordered_cell_values]
                table_data[header_text] = column_values

            lengths = [len(v) for v in table_data.values()]
            if lengths and len(set(lengths)) == 1 and lengths[0] > 0:
                df = pd.DataFrame(table_data)
                break
            time.sleep(1)
        else:
            time.sleep(1)

    # Case 2 is Standard HTML table (<table>, <tr>, <th>, <td>) if not Plotly
    if df is None:
        rows = table_element.find_elements(By.TAG_NAME, "tr")
        if rows:
            logger.info("Extracting standard HTML table...")
            headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]
            start_idx = 1
            if not headers:
                headers = [td.text.strip() for td in rows[0].find_elements(By.TAG_NAME, "td")]
                start_idx = 1

            data = []
            for r in rows[start_idx:]:
                cells = [td.text.strip() for td in r.find_elements(By.TAG_NAME, "td")]
                if cells:
                    data.append(cells)

            df = pd.DataFrame(data, columns=headers if len(headers) == len(data[0]) else None)
        elif y_columns:
            # Fallback if lengths still vary: pad to max length
            max_len = max(len(v) for v in table_data.values()) if table_data else 0
            for k, v in table_data.items():
                if len(v) < max_len:
                    v.extend([""] * (max_len - len(v)))
            df = pd.DataFrame(table_data)
        else:
            raise ValueError("No table structure could be extracted from the located element.")

    df = _convert_column_types(df)
    logger.info(f"Successfully extracted {len(df)} rows from HTML table.")
    logger.info(f"Table columns: {list(df.columns)}")
    return df


@keyword("Read Parquet Dataset")
def read_parquet_dataset(parquet_folder: str, filter_date: str | None = None) -> pd.DataFrame:
    logger.info(f"Reading Parquet dataset from: {parquet_folder}")
    folder_path = Path(parquet_folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Parquet directory not found: {folder_path.resolve()}")

    parquet_files = sorted(folder_path.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No .parquet files found in directory: {folder_path.resolve()}")

    frames = [pd.read_parquet(f) for f in parquet_files]
    df = pd.concat(frames, ignore_index=True)

    # Apply date filtering if provided
    if "visit_date" in df.columns:
        df["visit_date"] = pd.to_datetime(df["visit_date"])
        if filter_date and str(filter_date).strip().lower() not in ("none", "", "null"):
            parsed_date = pd.to_datetime(filter_date)
            logger.info(f"Applying date filter: visit_date >= {parsed_date.strftime('%Y-%m-%d')}")
            df = df[df["visit_date"] >= parsed_date].copy()

        # Sort matching the report generation logic
        sort_cols = [c for c in ["visit_date", "facility_type"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)

        df["visit_date"] = df["visit_date"].dt.strftime("%Y-%m-%d")

    # Drop any partition-only columns generated by directory partitioning
    for col in ["partition_date", "facility_type_partition"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Standardize column names to match HTML report table
    col_mapping = {
        "facility_type": "Facility Type",
        "visit_date": "Visit Date",
        "avg_time_spent": "Average Time Spent"
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
    df = _convert_column_types(df)

    logger.info(f"Successfully loaded {len(df)} rows from Parquet dataset.")
    logger.info(f"Parquet columns: {list(df.columns)}")
    return df


@keyword("Compare DataFrames")
def compare_dataframes(df_actual: pd.DataFrame, df_expected: pd.DataFrame) -> None:
    logger.info("Comparing HTML Table DataFrame with Parquet DataFrame...")
    diff_messages = []

    # 1. Check Column Existence
    actual_cols = list(df_actual.columns)
    expected_cols = list(df_expected.columns)

    if set(actual_cols) != set(expected_cols):
        diff_messages.append(
            f"Column Mismatch!\n"
            f"  HTML Table columns: {actual_cols}\n"
            f"  Parquet dataset columns: {expected_cols}"
        )
        raise AssertionError("\n\n".join(diff_messages))

    # Align column order
    df_expected = df_expected[actual_cols].copy()
    df_actual = df_actual.copy()

    # 2. Check Row Count / Shape
    if df_actual.shape != df_expected.shape:
        diff_messages.append(
            f"Shape Mismatch!\n"
            f"  HTML Table shape: {df_actual.shape} (rows, cols)\n"
            f"  Parquet dataset shape: {df_expected.shape} (rows, cols)"
        )

    # 3. Sort both DataFrames by common columns to ensure fair row-to-row comparison
    sort_keys = [c for c in ["Visit Date", "Facility Type"] if c in df_actual.columns]
    if sort_keys:
        df_actual = df_actual.sort_values(by=sort_keys, ascending=False).reset_index(drop=True)
        df_expected = df_expected.sort_values(by=sort_keys, ascending=False).reset_index(drop=True)
    else:
        df_actual = df_actual.reset_index(drop=True)
        df_expected = df_expected.reset_index(drop=True)

    # 4. Check Value Mismatches
    if df_actual.shape == df_expected.shape:
        # Round float columns for numeric precision
        for col in df_actual.columns:
            if pd.api.types.is_float_dtype(df_actual[col]) or pd.api.types.is_float_dtype(df_expected[col]):
                df_actual[col] = pd.to_numeric(df_actual[col], errors="coerce").round(2)
                df_expected[col] = pd.to_numeric(df_expected[col], errors="coerce").round(2)

        # Compare values
        diff_mask = ~( (df_actual == df_expected) | (df_actual.isna() & df_expected.isna()) )
        if diff_mask.any().any():
            mismatch_rows = df_actual.index[diff_mask.any(axis=1)].tolist()
            mismatch_details = []
            for r in mismatch_rows[:20]:  # Show up to first 20 row differences
                for col in actual_cols:
                    val_act = df_actual.at[r, col]
                    val_exp = df_expected.at[r, col]
                    if val_act != val_exp and not (pd.isna(val_act) and pd.isna(val_exp)):
                        mismatch_details.append(
                            f"  Row {r}, Column '{col}': HTML='{val_act}' vs Parquet='{val_exp}'"
                        )

            diff_summary = "\n".join(mismatch_details)
            diff_messages.append(f"Value Differences Found ({len(mismatch_rows)} differing rows):\n{diff_summary}")

            try:
                pandas_diff = df_actual.compare(df_expected)
                diff_messages.append(f"Pandas diff (self=HTML, other=Parquet):\n{pandas_diff.head(10)}")
            except Exception:
                pass

    if diff_messages:
        error_report = "\n\n" + "=" * 60 + "\nDATA QUALITY VALIDATION FAILED:\n" + "=" * 60 + "\n"
        error_report += "\n\n".join(diff_messages)
        logger.error(error_report)
        raise AssertionError(error_report)

    success_msg = f"SUCCESS: HTML table data and Parquet dataset match exactly! ({len(df_actual)} rows, {len(actual_cols)} columns)"
    logger.info(success_msg)
    print(success_msg)
