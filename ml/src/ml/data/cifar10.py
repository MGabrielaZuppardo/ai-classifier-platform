from collections.abc import Callable
from pathlib import Path
from typing import Any

from torch.utils.data import ConcatDataset, Dataset, Subset
from torchvision.datasets import CIFAR10

from ml.data.split import PARTITIONS, SplitManifest, predefined_test_split

CIFAR10_CLASSES = (
    "airplane",
    "automobile",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
)


def load_cifar10(
    root: str | Path, *, download: bool = False, transform: Callable[..., Any] | None = None
) -> tuple[ConcatDataset[Any], SplitManifest]:
    """Carrega o CIFAR-10 como `treino oficial + teste oficial` e devolve o manifesto da divisão.

    O teste oficial (10 mil imagens) vira a partição de teste; o treino oficial (50 mil) é
    dividido em treino e validação. O `transform` vale para todas as partições, então não
    inclua augmentation aqui: ela entra só no treino, em etapa posterior.
    """
    train = CIFAR10(str(root), train=True, download=download, transform=transform)
    test = CIFAR10(str(root), train=False, download=download, transform=transform)
    manifest = predefined_test_split(train.targets, test_size=len(test))
    return ConcatDataset([train, test]), manifest


def partitions(dataset: Dataset[Any], manifest: SplitManifest) -> dict[str, Subset[Any]]:
    """Subconjuntos `train`, `val` e `test` do dataset, segundo o manifesto."""
    return {name: Subset(dataset, list(manifest.indices(name))) for name in PARTITIONS}
