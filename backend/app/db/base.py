from pydantic import BaseModel

from app.db.connection import db


class DataBaseModel(BaseModel):
    __tablename__: str
    __unique_fields__: list[str] = []

    def save(self):
        saved_data = db.upsert_record(
            self.__tablename__,
            self.model_dump(exclude_unset=True),
            conflict_columns=self.__unique_fields__,
        )
        return self.__class__(**saved_data)