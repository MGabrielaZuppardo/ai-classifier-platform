from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.datasets.domain.dataset import Dataset
from app.modules.datasets.infrastructure.models import DatasetModel
from app.shared.owned_repository import OwnedRepository


def _to_entity(model: DatasetModel) -> Dataset:
    return Dataset(
        id=model.id,
        owner_id=model.owner_id,
        name=model.name,
        description=model.description,
        created_at=model.created_at,
    )


class SqlAlchemyDatasetRepository:
    def __init__(self, session: Session, owner_id: UUID) -> None:
        self._session = session
        self._owner_id = owner_id
        self._owned = OwnedRepository(session, DatasetModel, owner_id)

    def add(self, dataset: Dataset) -> None:
        self._owned.add(
            DatasetModel(
                id=dataset.id,
                owner_id=dataset.owner_id,
                name=dataset.name,
                description=dataset.description,
                created_at=dataset.created_at,
            )
        )

    def get(self, dataset_id: UUID) -> Dataset | None:
        model = self._owned.get(dataset_id)
        return _to_entity(model) if model else None

    def get_by_name(self, name: str) -> Dataset | None:
        model = self._session.execute(
            select(DatasetModel).where(
                DatasetModel.owner_id == self._owner_id, DatasetModel.name == name
            )
        ).scalar_one_or_none()
        return _to_entity(model) if model else None

    def list_all(self) -> list[Dataset]:
        return [_to_entity(m) for m in self._owned.list_all()]

    def delete(self, dataset_id: UUID) -> bool:
        return self._owned.delete(dataset_id)
