
from __future__ import annotations

import os
from typing import Any, Optional

import pandas as pd
import psycopg2


class PostgresConnectorContextManager:
    """Context manager for PostgreSQL connectivity used in DQ checks."""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5434,
        db_name: str = "mydatabase",
        db_user: str = "myuser",
        db_password: str = "mypassword",
    ):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.connection = None

    def __enter__(self):
        self.connection = psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )
        self.connection.autocommit = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def get_data_sql(self, sql: str, params: Optional[dict[str, Any]] = None) -> pd.DataFrame:
        if self.connection is None:
            raise RuntimeError("PostgreSQL connection is not open.")
        return pd.read_sql_query(sql, self.connection, params=params)

    def execute(self, sql: str, params: Optional[dict[str, Any]] = None) -> list[tuple]:
        if self.connection is None:
            raise RuntimeError("PostgreSQL connection is not open.")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params or {})
            return cursor.fetchall()


def get_postgres_connection_from_env() -> PostgresConnectorContextManager:
    return PostgresConnectorContextManager(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5434")),
        db_name=os.getenv("DB_NAME", "mydatabase"),
        db_user=os.getenv("DB_USER", "myuser"),
        db_password=os.getenv("DB_PASSWORD", "mypassword"),
    )


