from sqlalchemy import select
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, model):
        self.model = model

    def list(self, db: Session, *, limit: int = 100, offset: int = 0):
        stmt = select(self.model).offset(offset).limit(limit)
        return db.execute(stmt).scalars().all()

    def get(self, db: Session, object_id):
        return db.get(self.model, object_id)

    def create(self, db: Session, **kwargs):
        instance = self.model(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
