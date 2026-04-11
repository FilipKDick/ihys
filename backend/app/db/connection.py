from supabase import create_client, Client
from app.core.config import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Main Supabase client for server-side operations
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)


class DatabaseOperations:
    @staticmethod
    def insert_record(table_name: str, data: dict):
        result = supabase.table(table_name).insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_record_by_id(table_name: str, record_id: int):
        result = supabase.table(table_name).select("*").eq("id", record_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_records(table_name: str, filters: dict | None = None, limit: int | None = None):
        query = supabase.table(table_name).select("*")

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data

    @staticmethod
    def get_records_by_ids(table_name: str, column: str, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        result = supabase.table(table_name).select('*').in_(column, ids).execute()
        return result.data or []

    @staticmethod
    def update_record(table_name: str, record_id: int, data: dict):
        result = supabase.table(table_name).update(data).eq("id", record_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def delete_record(table_name: str, record_id: int):
        result = supabase.table(table_name).delete().eq("id", record_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def upsert_record(table_name: str, data: dict, conflict_columns: list[str]):
        logger.info(f"🔍 Upserting into {table_name}: {data}")
        logger.info(f"🔍 Conflict columns: {conflict_columns}")
        try:
            result = supabase.table(table_name).upsert(
                data,
                on_conflict=','.join(conflict_columns)
            ).execute()
            logger.info(f"✅ Successfully upserted into {table_name}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Upsert failed for {table_name}: {e}")
            logger.error(f"📋 Data that failed: {data}")
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            logger.error(f"🔍 Full error: {str(e)}")
            raise

# Alias for easier imports
db = DatabaseOperations()
