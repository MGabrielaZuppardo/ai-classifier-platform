from typing import Protocol
from uuid import UUID

from app.modules.datasets.domain.dataset import Dataset


class DatasetRepository(Protocol):
    """Repositório já restrito a um dono: nenhum método enxerga datasets de outros usuários."""

    def add(self, dataset: Dataset) -> None: ...

    def get(self, dataset_id: UUID) -> Dataset | None: ...

    def get_by_name(self, name: str) -> Dataset | None: ...

    def list_all(self) -> list[Dataset]: ...

    def delete(self, dataset_id: UUID) -> bool: ...
