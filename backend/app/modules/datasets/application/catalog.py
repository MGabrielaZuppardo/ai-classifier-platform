from uuid import UUID

from app.modules.datasets.application.ports import DatasetRepository
from app.modules.datasets.domain.dataset import Dataset


class DatasetNotFoundError(Exception):
    """Dataset inexistente ou de outro usuário (os dois casos são indistinguíveis)."""


class DatasetNameTakenError(Exception):
    """O usuário já tem um dataset com esse nome."""


class DatasetCatalog:
    def __init__(self, datasets: DatasetRepository, owner_id: UUID) -> None:
        self._datasets = datasets
        self._owner_id = owner_id

    def create(self, name: str, description: str = "") -> Dataset:
        dataset = Dataset(owner_id=self._owner_id, name=name, description=description)
        if self._datasets.get_by_name(dataset.name) is not None:
            raise DatasetNameTakenError(dataset.name)
        self._datasets.add(dataset)
        return dataset

    def get(self, dataset_id: UUID) -> Dataset:
        dataset = self._datasets.get(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError(str(dataset_id))
        return dataset

    def list_all(self) -> list[Dataset]:
        return self._datasets.list_all()

    def delete(self, dataset_id: UUID) -> None:
        if not self._datasets.delete(dataset_id):
            raise DatasetNotFoundError(str(dataset_id))
