from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


class ParquetReader:
    """Read one or many parquet files as pandas DataFrames."""

    @staticmethod
    def _iter_parquet_files(base_path: str | Path, include_subfolders: bool = True) -> Iterable[Path]:
        root = Path(base_path)
        if root.is_file():
            yield root
            return
        if not root.exists():
            raise FileNotFoundError(f"Parquet path does not exist: {root}")
        if include_subfolders:
            yield from sorted(root.rglob("*.parquet"))
        else:
            yield from sorted(root.glob("*.parquet"))

    @staticmethod
    def process(path: str | Path, include_subfolders: bool = True) -> pd.DataFrame:
        files = list(ParquetReader._iter_parquet_files(path, include_subfolders=include_subfolders))
        if not files:
            raise FileNotFoundError(f"No parquet files found under: {path}")

        frames = [pd.read_parquet(file) for file in files]
        combined = pd.concat(frames, ignore_index=True)
        return combined
