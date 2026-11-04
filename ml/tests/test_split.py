import numpy as np
import pytest

from ml.data.split import (
    InvalidSplitError,
    SplitManifest,
    class_counts,
    predefined_test_split,
    stratified_split,
)

LABELS = [c for c in range(10) for _ in range(100)]  # 10 classes, 100 amostras cada


def test_partitions_are_disjoint_and_cover_the_dataset():
    manifest = stratified_split(LABELS)

    all_indices = [*manifest.train, *manifest.val, *manifest.test]
    assert sorted(all_indices) == list(range(len(LABELS)))


def test_default_ratios_give_80_10_10_per_class():
    manifest = stratified_split(LABELS)

    for partition, expected in (("train", 80), ("val", 10), ("test", 10)):
        counts = class_counts(LABELS, manifest)[partition]
        assert set(counts.values()) == {expected}


def test_stratification_holds_for_imbalanced_classes():
    labels = [0] * 900 + [1] * 100
    manifest = stratified_split(labels)

    counts = class_counts(labels, manifest)
    assert counts["train"] == {0: 720, 1: 80}
    assert counts["val"] == {0: 90, 1: 10}
    assert counts["test"] == {0: 90, 1: 10}


def test_same_seed_gives_the_same_split_and_other_seed_differs():
    assert stratified_split(LABELS, seed=1) == stratified_split(LABELS, seed=1)
    assert stratified_split(LABELS, seed=1) != stratified_split(LABELS, seed=2)


def test_positive_ratio_guarantees_every_class_in_every_partition():
    labels = [0] * 50 + [1] * 3
    manifest = stratified_split(labels, (0.8, 0.1, 0.1))

    for partition in ("train", "val", "test"):
        assert set(class_counts(labels, manifest)[partition]) == {0, 1}
        assert all(v >= 1 for v in class_counts(labels, manifest)[partition].values())


def test_class_too_small_for_the_requested_partitions_is_rejected():
    with pytest.raises(InvalidSplitError, match="classe 1"):
        stratified_split([0] * 50 + [1] * 2, (0.8, 0.1, 0.1))


def test_zero_ratio_leaves_the_partition_empty():
    manifest = stratified_split(LABELS, (0.9, 0.1, 0.0))

    assert manifest.test == ()
    assert len(manifest.val) == 100


@pytest.mark.parametrize("ratios", [(0.5, 0.5, 0.5), (0.8, 0.3, -0.1), (0.0, 0.5, 0.5)])
def test_invalid_ratios_are_rejected(ratios: tuple[float, float, float]):
    with pytest.raises(InvalidSplitError):
        stratified_split(LABELS, ratios)


def test_overlapping_partitions_are_rejected():
    with pytest.raises(InvalidSplitError, match="sobrep"):
        SplitManifest(seed=1, ratios=(0.8, 0.1, 0.1), train=(1, 2), val=(2,), test=(3,))


def test_json_roundtrip_and_fingerprint():
    manifest = stratified_split(LABELS)

    restored = SplitManifest.from_json(manifest.to_json())

    assert restored == manifest
    assert restored.fingerprint() == manifest.fingerprint()
    assert stratified_split(LABELS, seed=2).fingerprint() != manifest.fingerprint()


def test_predefined_test_split_keeps_the_official_test_set_apart():
    train_labels = [c for c in range(10) for _ in range(100)]
    manifest = predefined_test_split(train_labels, test_size=200)

    assert manifest.test == tuple(range(1000, 1200))
    assert max(manifest.train + manifest.val) < 1000
    assert len(manifest.val) == 100
    assert set(class_counts(train_labels + [0] * 200, manifest)["val"].values()) == {10}
    assert np.all(np.diff(manifest.test) == 1)
