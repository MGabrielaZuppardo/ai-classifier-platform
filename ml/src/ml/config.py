import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MODEL_NAMES = ("cnn_baseline", "resnet18")
OPTIMIZERS = ("adamw", "sgd")

MAX_EPOCHS = 50
MAX_BATCH_SIZE = 256
MAX_REPETITIONS = 5


class InvalidConfigError(ValueError):
    """Configuração de treino fora dos limites aceitos."""


@dataclass(frozen=True)
class TrainingConfig:
    """Hiperparâmetros de um experimento. É sempre salvo junto com os resultados."""

    model: Literal["cnn_baseline", "resnet18"] = "resnet18"
    pretrained: bool = True
    # Fine-tuning por padrão; False congela o backbone e treina só a nova cabeça.
    fine_tune: bool = True
    seed: int = 42
    epochs: int = 20
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-2
    optimizer: Literal["adamw", "sgd"] = "adamw"
    early_stopping_patience: int = 5
    mixed_precision: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.model not in MODEL_NAMES:
            raise InvalidConfigError(f"modelo desconhecido: {self.model!r}")
        if self.optimizer not in OPTIMIZERS:
            raise InvalidConfigError(f"otimizador desconhecido: {self.optimizer!r}")
        if not 1 <= self.epochs <= MAX_EPOCHS:
            raise InvalidConfigError(f"epochs deve estar entre 1 e {MAX_EPOCHS}")
        if not 1 <= self.batch_size <= MAX_BATCH_SIZE:
            raise InvalidConfigError(f"batch_size deve estar entre 1 e {MAX_BATCH_SIZE}")
        if self.learning_rate <= 0:
            raise InvalidConfigError("learning_rate deve ser positivo")
        if self.weight_decay < 0:
            raise InvalidConfigError("weight_decay não pode ser negativo")
        if self.early_stopping_patience < 0:
            raise InvalidConfigError("early_stopping_patience não pode ser negativo")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingConfig":
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise InvalidConfigError(f"campos desconhecidos: {sorted(unknown)}")
        return cls(**data)

    @classmethod
    def from_json(cls, text: str) -> "TrainingConfig":
        return cls.from_dict(json.loads(text))
