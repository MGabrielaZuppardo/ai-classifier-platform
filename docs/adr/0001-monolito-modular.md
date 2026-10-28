# ADR 0001 — Monólito modular com camadas

**Status:** aceita

**Contexto:** projeto de um time pequeno, com necessidade de testabilidade e baixo custo operacional.

**Decisão:** backend FastAPI único, dividido em módulos (identity, datasets, experiments, models) com camadas domain/application/infrastructure/api. Treinos rodam em workers, nunca em requisições HTTP.

**Consequências:** sem microsserviços nem Kubernetes na v1; fronteiras entre módulos explícitas para permitir extração futura.
