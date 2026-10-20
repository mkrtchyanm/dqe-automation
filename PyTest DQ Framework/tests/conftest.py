from __future__ import annotations

import os

import pytest

from src.connectors.file_system.parquet_reader import ParquetReader
from src.connectors.postgres.postgres_connector import PostgresConnectorContextManager
from src.data_quality.data_quality_validation_library import DataQualityLibrary


def pytest_addoption(parser):
    parser.addoption("--db_host", action="store", default=os.getenv("DB_HOST", "localhost"), help="Database host")
    parser.addoption("--db_port", action="store", default=os.getenv("DB_PORT", "5434"), help="Database port")
    parser.addoption("--db_name", action="store", default=os.getenv("DB_NAME", "mydatabase"), help="Database name")
    parser.addoption("--db_user", action="store", default=os.getenv("DB_USER", "myuser"), help="Database user")
    parser.addoption("--db_password", action="store", default=os.getenv("DB_PASSWORD", "mypassword"), help="Database password")


@pytest.fixture(scope="session")
def db_connection(request):
    db_host = request.config.getoption("--db_host")
    db_port = int(request.config.getoption("--db_port"))
    db_name = request.config.getoption("--db_name")
    db_user = request.config.getoption("--db_user")
    db_password = request.config.getoption("--db_password")

    try:
        with PostgresConnectorContextManager(
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
        ) as connector:
            yield connector
    except Exception as exc:  # pragma: no cover - fixture fails cleanly on setup issues
        pytest.fail(f"Failed to initialize PostgreSQL connection: {exc}")


@pytest.fixture(scope="session")
def parquet_reader():
    return ParquetReader


@pytest.fixture(scope="session")
def data_quality_library():
    return DataQualityLibrary
...
