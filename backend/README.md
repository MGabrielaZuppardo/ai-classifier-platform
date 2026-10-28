# Backend

Monólito modular FastAPI. Cada módulo em `app/modules/<nome>` segue camadas inspiradas em Clean Architecture:

- `domain/`: entidades e regras de negócio, sem dependência de framework.
- `application/`: casos de uso e portas (interfaces).
- `infrastructure/`: SQLAlchemy, storage, filas (implementam as portas).
- `api/`: routers e schemas Pydantic.

Dependência sempre de fora para dentro: `api` → `application` → `domain`.

## Comandos

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
ruff check . && ruff format --check .
pytest                      # todos
pytest tests/unit/test_health.py::test_health_returns_ok   # um teste
```
