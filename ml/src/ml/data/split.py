import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

PARTITIONS = ("train", "val", "test")


class InvalidSplitError(ValueError):
    """Razões inválidas, classes com amostras demais de menos, ou partições que se sobrepõem."""


@dataclass(frozen=True)
class SplitManifest:
    """Divisão treino/validação/teste de um dataset, em índices.

    É o registro reprodutível da divisão: guarda a seed e as razões usadas e deve ser salvo
    junto com a versão do dataset e com o experimento.
    """

    seed: int
    ratios: tuple[float, float, float]
    train: tuple[int, ...]
    val: tuple[int, ...]
    test: tuple[int, ...]

    def __post_init__(self) -> None:
        seen: set[int] = set()
        for name in PARTITIONS:
            indices = set(getattr(self, name))
            if len(indices) != len(getattr(self, name)):
                raise InvalidSplitError(f"a partição {name} tem índices repetidos")
            if seen & indices:
                raise InvalidSplitError("as partições treino, validação e teste se sobrepõem")
            seen |= indices

    @property
    def size(self) -> int:
        return len(self.train) + len(self.val) + len(self.test)

    def indices(self, partition: str) -> tuple[int, ...]:
        if partition not in PARTITIONS:
            raise KeyError(partition)
        return getattr(self, partition)  # type: ignore[no-any-return]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "ratios": list(self.ratios),
            "train": list(self.train),
            "val": list(self.val),
            "test": list(self.test),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "SplitManifest":
        data = json.loads(text)
        r = data["ratios"]
        return cls(
            seed=data["seed"],
            ratios=(r[0], r[1], r[2]),
            train=tuple(data["train"]),
            val=tuple(data["val"]),
            test=tuple(data["test"]),
        )

    def fingerprint(self) -> str:
        """SHA-256 do conteúdo: identifica a divisão exata, para citar em resultados."""
        return hashlib.sha256(self.to_json().encode()).hexdigest()


def stratified_split(
    labels: Sequence[int],
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 42,
) -> SplitManifest:
    """Divide os índices mantendo a proporção de cada classe em todas as partições.

    Uma razão positiva garante ao menos uma amostra por classe naquela partição; razão zero
    deixa a partição vazia (útil quando o teste já vem pronto, como no CIFAR-10).
    """
    if any(r < 0 for r in ratios) or abs(sum(ratios) - 1.0) > 1e-9:
        raise InvalidSplitError("as razões devem ser não negativas e somar 1")
    if ratios[0] <= 0:
        raise InvalidSplitError("a razão de treino deve ser positiva")

    y = np.asarray(labels)
    rng = np.random.default_rng(seed)
    parts: dict[str, list[int]] = {name: [] for name in PARTITIONS}
    needed = sum(1 for r in ratios if r > 0)

    for cls in np.unique(y):
        idx = np.flatnonzero(y == cls)
        if len(idx) < needed:
            raise InvalidSplitError(
                f"a classe {cls} tem {len(idx)} amostras; são necessárias ao menos {needed}"
            )
        rng.shuffle(idx)
        n_val = max(1, round(len(idx) * ratios[1])) if ratios[1] > 0 else 0
        n_test = max(1, round(len(idx) * ratios[2])) if ratios[2] > 0 else 0
        parts["val"].extend(idx[:n_val].tolist())
        parts["test"].extend(idx[n_val : n_val + n_test].tolist())
        parts["train"].extend(idx[n_val + n_test :].tolist())

    return SplitManifest(
        seed=seed,
        ratios=ratios,
        train=tuple(sorted(parts["train"])),
        val=tuple(sorted(parts["val"])),
        test=tuple(sorted(parts["test"])),
    )


def class_counts(labels: Sequence[int], manifest: SplitManifest) -> dict[str, dict[int, int]]:
    """Amostras por classe em cada partição, para conferir a estratificação."""
    y = np.asarray(labels)
    return {
        name: {int(c): int((y[list(manifest.indices(name))] == c).sum()) for c in np.unique(y)}
        for name in PARTITIONS
    }


def predefined_test_split(
    train_labels: Sequence[int],
    test_size: int,
    val_fraction: float = 0.1,
    seed: int = 42,
) -> SplitManifest:
    """Divisão para datasets que já trazem um teste oficial (CIFAR-10).

    Os índices valem para a concatenação `treino + teste`: o teste oficial ocupa as últimas
    `test_size` posições e nunca entra na escolha de hiperparâmetros. Só o treino oficial é
    dividido (estratificado) em treino e validação.
    """
    n_train = len(train_labels)
    inner = stratified_split(train_labels, (1.0 - val_fraction, val_fraction, 0.0), seed)
    return SplitManifest(
        seed=seed,
        ratios=(inner.ratios[0], inner.ratios[1], 0.0),
        train=inner.train,
        val=inner.val,
        test=tuple(range(n_train, n_train + test_size)),
    )
