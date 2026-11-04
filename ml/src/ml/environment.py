import platform
from typing import Any

import numpy as np
import torch
import torchvision


def resolve_device(requested: str = "auto") -> torch.device:
    """`auto` usa a GPU CUDA quando existe; `cuda` sem GPU é erro, não um fallback silencioso."""
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA solicitado, mas nenhuma GPU está disponível")
    if requested not in ("cpu", "cuda"):
        raise ValueError(f"dispositivo desconhecido: {requested!r}")
    return torch.device(requested)


def collect_environment() -> dict[str, Any]:
    """Versões e hardware para registrar com cada experimento (reprodutibilidade)."""
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "numpy": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        info["gpu_name"] = props.name
        info["gpu_memory_mb"] = props.total_memory // (1024 * 1024)
    return info
