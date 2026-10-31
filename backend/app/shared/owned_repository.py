from typing import Generic, Protocol, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Mapped, Session


class OwnedModel(Protocol):
    id: Mapped[UUID]
    owner_id: Mapped[UUID]


T = TypeVar("T", bound=OwnedModel)


class CrossOwnerError(Exception):
    """Tentativa de gravar um recurso em nome de outro usuário."""


class OwnedRepository(Generic[T]):  # noqa: UP046
    """Base dos repositórios de recursos que pertencem a um usuário.

    Todas as consultas filtram por `owner_id`, então o código que usa o repositório
    não tem como ler ou alterar um recurso de outra pessoa. Um recurso alheio
    é indistinguível de um inexistente.
    """

    def __init__(self, session: Session, model: type[T], owner_id: UUID) -> None:
        self._session = session
        self._model = model
        self._owner_id = owner_id

    def get(self, entity_id: UUID) -> T | None:
        stmt = select(self._model).where(
            self._model.id == entity_id, self._model.owner_id == self._owner_id
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[T]:
        stmt = select(self._model).where(self._model.owner_id == self._owner_id)
        return list(self._session.execute(stmt).scalars())

    def add(self, entity: T) -> T:
        if entity.owner_id != self._owner_id:
            raise CrossOwnerError("o recurso pertence a outro usuário")
        self._session.add(entity)
        self._session.flush()
        return entity

    def delete(self, entity_id: UUID) -> bool:
        entity = self.get(entity_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.flush()
        return True
