import os
import random

import numpy as np
import torch


def set_seed(seed: int, *, deterministic: bool = True) -> None:
    """Fixa todas as fontes de aleatoriedade usadas no treino.

    Com `deterministic=True` o cuDNN passa a escolher algoritmos determinísticos,
    ao custo de alguma velocidade. Mesmo assim, resultados em GPUs ou versões
    diferentes do PyTorch podem divergir; por isso a versão vai no registro do ambiente.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.backends.cudnn.deterministic = deterministic
    torch.backends.cudnn.benchmark = not deterministic
