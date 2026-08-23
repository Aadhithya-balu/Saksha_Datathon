"""
Generic CRUD service used by all resource services (crimes, criminals, victims,
officers, FIRs, evidence, locations, reports) to avoid repeating the same
list/get/create/update/delete + pagination/filter/sort logic per module.
"""
from typing import Any, Generic, Type, TypeVar

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException

ModelT = TypeVar("ModelT")


class BaseCRUDService(Generic[ModelT]):
    def __init__(self, model: Type[ModelT]):
        self.model = model

    def get(self, db: Session, obj_id) -> ModelT:
        obj = db.query(self.model).filter(self.model.id == obj_id).first()
        if not obj:
            raise NotFoundException(f"{self.model.__name__} not found")
        return obj

    def list(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
        filters: dict[str, Any] | None = None,
    ) -> dict:
        query = db.query(self.model)

        if filters:
            for field, value in filters.items():
                if value is None:
                    continue
                column = getattr(self.model, field, None)
                if column is None:
                    continue
                if isinstance(value, str):
                    query = query.filter(column.ilike(f"%{value}%"))
                else:
                    query = query.filter(column == value)

        total = query.count()

        if sort_by and hasattr(self.model, sort_by):
            column = getattr(self.model, sort_by)
            query = query.order_by(desc(column) if sort_order == "desc" else asc(column))
        elif hasattr(self.model, "created_at"):
            query = query.order_by(desc(self.model.created_at))

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        results = query.offset((page - 1) * page_size).limit(page_size).all()

        return {"total": total, "page": page, "page_size": page_size, "results": results}

    def create(self, db: Session, data: dict) -> ModelT:
        obj = self.model(**data)
        db.add(obj)
        db.flush()
        return obj

    def update(self, db: Session, obj_id, data: dict) -> ModelT:
        obj = self.get(db, obj_id)
        for field, value in data.items():
            if value is not None:
                setattr(obj, field, value)
        db.add(obj)
        db.flush()
        return obj

    def delete(self, db: Session, obj_id) -> None:
        obj = self.get(db, obj_id)
        db.delete(obj)
        db.flush()
