import logging

from typing import Any

import psycopg_pool

from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: psycopg_pool.ConnectionPool | None = None


def get_pool() -> psycopg_pool.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg_pool.ConnectionPool(
            settings.DATABASE_URL,
            kwargs={'row_factory': dict_row},
            min_size=2,
            max_size=10,
        )
    return _pool


class DatabaseOperations:
    def _execute(
        self,
        sql: str,
        params: tuple | dict | None = None,
        *,
        fetch: str = 'one',
    ) -> Any:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch == 'all':
                    return cur.fetchall()
                if fetch == 'one':
                    return cur.fetchone()
                return None

    def insert_record(self, table_name: str, data: dict) -> dict:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f'%({k})s' for k in data.keys())
        sql = f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) RETURNING *'  # noqa: S608
        return self._execute(sql, data)

    def get_record_by_id(self, table_name: str, record_id: int) -> dict | None:
        sql = f'SELECT * FROM {table_name} WHERE id = %s'  # noqa: S608
        return self._execute(sql, (record_id,))

    def get_records(
        self,
        table_name: str,
        filters: dict | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        sql = f'SELECT * FROM {table_name}'  # noqa: S608
        params: list = []
        if filters:
            conditions = ' AND '.join(f'{k} = %s' for k in filters.keys())
            sql += f' WHERE {conditions}'
            params = list(filters.values())
        if limit:
            sql += f' LIMIT {limit}'
        result = self._execute(sql, tuple(params) if params else None, fetch='all')
        return result or []

    def get_records_by_ids(
        self, table_name: str, column: str, ids: list[int],
    ) -> list[dict]:
        if not ids:
            return []
        sql = f'SELECT * FROM {table_name} WHERE {column} = ANY(%s)'  # noqa: S608
        result = self._execute(sql, (ids,), fetch='all')
        return result or []

    def update_record(
        self, table_name: str, record_id: int, data: dict,
    ) -> dict | None:
        assignments = ', '.join(f'{k} = %({k})s' for k in data.keys())
        sql = f'UPDATE {table_name} SET {assignments} WHERE id = %(id)s RETURNING *'  # noqa: S608
        return self._execute(sql, {**data, 'id': record_id})

    def delete_record(self, table_name: str, record_id: int) -> dict | None:
        sql = f'DELETE FROM {table_name} WHERE id = %s RETURNING *'  # noqa: S608
        return self._execute(sql, (record_id,))

    def upsert_record(
        self, table_name: str, data: dict, conflict_columns: list[str],
    ) -> dict | None:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f'%({k})s' for k in data.keys())
        conflict = ', '.join(conflict_columns)
        non_conflict_keys = [k for k in data.keys() if k not in conflict_columns]
        if non_conflict_keys:
            updates = ', '.join(f'{k} = EXCLUDED.{k}' for k in non_conflict_keys)
            on_conflict = f'DO UPDATE SET {updates}'
        else:
            on_conflict = 'DO NOTHING'
        sql = (
            f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) '  # noqa: S608
            f'ON CONFLICT ({conflict}) {on_conflict} RETURNING *'
        )
        result = self._execute(sql, data)
        if result is None:
            # ON CONFLICT DO NOTHING fired — no row returned; fetch existing record
            conditions = ' AND '.join(f'{k} = %s' for k in conflict_columns)
            select_sql = f'SELECT * FROM {table_name} WHERE {conditions}'  # noqa: S608
            result = self._execute(select_sql, tuple(data[k] for k in conflict_columns))
        return result


db = DatabaseOperations()
