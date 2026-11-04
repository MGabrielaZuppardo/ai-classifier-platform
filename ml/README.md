# ML

Biblioteca de treino/avaliação (CNN baseline, ResNet-18, métricas, checkpoints), testável sem a API.

## Instalação

O `torch` não está nas dependências do pacote: a variante depende do ambiente. Use um venv próprio e instale o torch **antes** do pacote.

GPU NVIDIA (CUDA 12.6):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.venv/Scripts/python -m pip install -e ".[dev]"
```

Somente CPU (como no CI), troque o índice por `https://download.pytorch.org/whl/cpu`.

## Testes

```bash
pytest
```

## Módulos

- `ml.config`: `TrainingConfig`, hiperparâmetros validados (limites do MVP) e serializáveis em JSON.
- `ml.seed`: `set_seed`, fixa as fontes de aleatoriedade.
- `ml.environment`: `resolve_device` e `collect_environment` (versões e GPU, para registrar com cada experimento).
- `ml.data.split`: `stratified_split`, `predefined_test_split` e `SplitManifest` (índices por partição, seed, razões e `fingerprint` SHA-256, serializável em JSON).
- `ml.data.cifar10`: `load_cifar10` (treino + teste oficiais como um só dataset, teste oficial isolado) e `partitions`.
