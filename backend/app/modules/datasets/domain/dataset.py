from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000


class InvalidDatasetError(ValueError):
    """Nome ou descrição fora das regras do dataset."""


@dataclass(frozen=True)
class Dataset:
    """Registro de um dataset de um usuário. Os arquivos e versões entram em etapas seguintes."""

    owner_id: UUID
    name: str
    description: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise InvalidDatasetError("o nome do dataset não pode ser vazio")
        if len(name) > MAX_NAME_LENGTH:
            raise InvalidDatasetError(f"o nome aceita no máximo {MAX_NAME_LENGTH} caracteres")
        if len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise InvalidDatasetError(
                f"a descrição aceita no máximo {MAX_DESCRIPTION_LENGTH} caracteres"
            )
        object.__setattr__(self, "name", name)
