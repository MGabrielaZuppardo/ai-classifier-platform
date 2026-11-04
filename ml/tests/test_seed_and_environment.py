import random

import numpy as np
import pytest
import torch

from ml.environment import collect_environment, resolve_device
from ml.seed import set_seed


def _draw() -> tuple[float, float, float]:
    return random.random(), float(np.random.rand()), float(torch.rand(1))


def test_same_seed_gives_the_same_draws():
    set_seed(123)
    first = _draw()
    set_seed(123)

    assert _draw() == first


def test_different_seeds_give_different_draws():
    set_seed(1)
    first = _draw()
    set_seed(2)

    assert _draw() != first


def test_environment_records_library_versions():
    info = collect_environment()

    assert info["torch"] == torch.__version__
    assert {"python", "torchvision", "numpy", "cuda_available"} <= set(info)


def test_cpu_device_is_always_available():
    assert resolve_device("cpu").type == "cpu"


def test_auto_device_matches_cuda_availability():
    expected = "cuda" if torch.cuda.is_available() else "cpu"

    assert resolve_device("auto").type == expected


def test_unknown_device_is_rejected():
    with pytest.raises(ValueError, match="desconhecido"):
        resolve_device("tpu")
