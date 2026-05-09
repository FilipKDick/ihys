from typing import ClassVar

from pydantic import BaseModel

from app.db.connection import db


class DataBaseModel(BaseModel):
    __tablename__: ClassVar[str]
    __unique_fields__: ClassVar[list[str]] = []

    def save(self):
        saved_data = db.upsert_record(
            self.__tablename__,
            self.model_dump(exclude_unset=True),
            conflict_columns=self.__unique_fields__,
        )
        return self.__class__(**saved_data)

    def exists(self):
        fields = {field: getattr(self, field) for field in self.__unique_fields__}
        records = db.get_records(self.__tablename__, fields, limit=1)
        return len(records) > 0
