import torch
from torch.utils.data import TensorDataset

from ml.data import cifar10
from ml.data.split import stratified_split


def test_partitions_follow_the_manifest():
    labels = [c for c in range(5) for _ in range(20)]
    dataset = TensorDataset(torch.arange(100), torch.tensor(labels))
    manifest = stratified_split(labels)

    parts = cifar10.partitions(dataset, manifest)

    assert {k: len(v) for k, v in parts.items()} == {"train": 80, "val": 10, "test": 10}
    # Cada Subset devolve exatamente as amostras dos seus índices.
    assert [int(parts["val"][i][0]) for i in range(10)] == list(manifest.val)


def test_class_names_cover_ten_classes():
    assert len(cifar10.CIFAR10_CLASSES) == 10
