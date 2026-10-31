from uuid import UUID, uuid4

import pytest
from sqlalchemy import String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.shared.owned_repository import CrossOwnerError, OwnedRepository

pytestmark = pytest.mark.integration


class _TestBase(DeclarativeBase):
    pass


class Note(_TestBase):
    """Recurso fictício com dono, só para exercitar a base do repositório."""

    __tablename__ = "test_notes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    title: Mapped[str] = mapped_column(String(50))


@pytest.fixture
def session(db_session: Session) -> Session:
    # DDL transacional no PostgreSQL: a tabela some com o rollback do teste.
    _TestBase.metadata.create_all(db_session.connection())
    return db_session


ALICE = uuid4()
BOB = uuid4()


def _note(owner: UUID, title: str = "n") -> Note:
    return Note(id=uuid4(), owner_id=owner, title=title)


def test_owner_reads_own_resource(session: Session):
    alice = OwnedRepository(session, Note, ALICE)
    note = alice.add(_note(ALICE, "minha"))

    found = alice.get(note.id)

    assert found is not None
    assert found.title == "minha"


def test_other_user_cannot_read_resource(session: Session):
    note = OwnedRepository(session, Note, ALICE).add(_note(ALICE))

    assert OwnedRepository(session, Note, BOB).get(note.id) is None


def test_listing_returns_only_own_resources(session: Session):
    alice = OwnedRepository(session, Note, ALICE)
    bob = OwnedRepository(session, Note, BOB)
    alice.add(_note(ALICE, "a1"))
    alice.add(_note(ALICE, "a2"))
    bob.add(_note(BOB, "b1"))

    assert {n.title for n in alice.list_all()} == {"a1", "a2"}
    assert {n.title for n in bob.list_all()} == {"b1"}


def test_other_user_cannot_delete_resource(session: Session):
    note = OwnedRepository(session, Note, ALICE).add(_note(ALICE))

    assert OwnedRepository(session, Note, BOB).delete(note.id) is False
    assert OwnedRepository(session, Note, ALICE).get(note.id) is not None


def test_owner_can_delete_own_resource(session: Session):
    alice = OwnedRepository(session, Note, ALICE)
    note = alice.add(_note(ALICE))

    assert alice.delete(note.id) is True
    assert alice.get(note.id) is None


def test_cannot_add_resource_on_behalf_of_another_user(session: Session):
    with pytest.raises(CrossOwnerError):
        OwnedRepository(session, Note, BOB).add(_note(ALICE))
