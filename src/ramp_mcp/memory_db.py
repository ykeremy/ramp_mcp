import datetime
import json
import sqlite3
import uuid
from typing import Any

from flatten_json import flatten


class MemoryDatabase:
    """
    ephemeral sqlite db in memory to make json array data queryable by an llm
    with simple built-in ETL data pipeline
    """

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._cursor = self.conn.cursor()

        self._table_name_to_temp_data: dict[str, list[dict[str, Any]]] = dict()
        self._table_name_to_cols: dict[str, list[str]] = dict()
        self._table_last_access: dict[str, datetime.datetime] = dict()

    def store_data(self, func_name: str, data: list[dict[str, Any]]) -> str:
        """
        Store response data for processing
        """
        table_name = func_name + "_" + str(uuid.uuid4()).replace("-", "")
        self._table_name_to_temp_data[table_name] = data
        return table_name

    def data_is_processed(self, table_name: str) -> bool:
        """
        Check if a table has been processed
        """
        return table_name not in self._table_name_to_temp_data

    def exists(self, table_name: str) -> bool:
        """
        Check if a table exists
        """
        return table_name in self._table_last_access

    def commit(self, table_name: str) -> None:
        """
        Commit the current transaction
        """
        self.conn.commit()
        self._table_last_access[table_name] = datetime.datetime.now()
        if table_name in self._table_name_to_temp_data:
            del self._table_name_to_temp_data[table_name]

    def create_table_with_cols(
        self,
        table_name: str,
        cols: list[str],
    ) -> None:
        """
        Create a table from a list of columns
        """
        processed_data = self._process_data(
            self._table_name_to_temp_data[table_name], cols
        )
        self._table_name_to_temp_data[table_name] = processed_data

        unique_cols = {key for data in processed_data for key in data.keys()}
        self._table_name_to_cols[table_name] = list(unique_cols)

        column_types = self._infer_column_types(unique_cols, processed_data)

        columns = []
        for key, col_type in column_types.items():
            columns.append(f'"{key}" {col_type}')

        create_table_sql = (
            f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
        )
        self._cursor.execute(create_table_sql)

    def load_data(self, table_name: str) -> None:
        """
        Insert data into table from temp data store
        """
        data = self._table_name_to_temp_data[table_name]
        if not data:
            return

        unique_cols = self._table_name_to_cols[table_name]
        placeholders = ", ".join(["?" for _ in unique_cols])
        columns_str = ", ".join(unique_cols)

        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

        values = [tuple(item.get(col, None) for col in unique_cols) for item in data]
        self._cursor.executemany(insert_sql, values)

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute a SQL query and return results as a list of dicts
        """
        try:
            self._cursor.execute(query)
            rows = self._cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise Exception(f"SQL error: {e}")

    def clear_table(self, table_name: str) -> None:
        """
        Clear a table
        """
        self._cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        if table_name in self._table_name_to_temp_data:
            del self._table_name_to_temp_data[table_name]
        if table_name in self._table_name_to_cols:
            del self._table_name_to_cols[table_name]
        if table_name in self._table_last_access:
            del self._table_last_access[table_name]
        self.conn.commit()

    def _infer_column_types(
        self, cols: list[str], data: list[dict[str, Any]]
    ) -> dict[str, str]:
        """
        Infer column types from data
        """
        column_types = {col: "INTEGER" for col in cols}
        for data in data:
            for key, value in data.items():
                if isinstance(value, str) or value is None:
                    column_types[key] = "TEXT"
                elif isinstance(value, float):
                    column_types[key] = "REAL"

        return column_types

    def _get_value_from_key(
        self,
        data: dict[str, Any],
        key: str,
    ) -> Any:
        """
        Get a value from a potentially nested key
        """
        keys = key.split("__")
        result = data
        for key in keys:
            result = result.get(key)
            if isinstance(result, list):
                # just turn lists into strings
                return json.dumps(result)
            if result is None:
                return None
        return result

    def _get_subset_from_keys(
        self,
        data: dict[str, Any],
        keys: list[str],
    ) -> dict[str, Any]:
        """
        Create a subset of the dict using the given keys,
        including nested keys
        """
        result = {}
        for key in keys:
            value = self._get_value_from_key(data, key)
            if value is not None:
                keys_split = key.split("__")
                current = result
                for sub_key in keys_split[:-1]:
                    if sub_key not in current:
                        current[sub_key] = {}
                    current = current[sub_key]
                current[keys_split[-1]] = value

        return result

    def _process_data(
        self,
        data: list[dict[str, Any]],
        select_keys: list[str],
    ) -> list[dict[str, Any]]:
        """
        Reduces and flattens data to only include select keys
        """
        reduced_data = [self._get_subset_from_keys(item, select_keys) for item in data]
        return [flatten(item, separator="__") for item in reduced_data]
