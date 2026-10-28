# Infra

Configurações de ambiente e deploy.

## Desenvolvimento local

```bash
docker compose -f infra/docker-compose.yml up --build
```

Sobe PostgreSQL, Redis e a API (`http://localhost:8000/health`). A API só inicia depois que o banco e o Redis estão saudáveis.

As credenciais do compose são apenas para desenvolvimento. Em produção, os segredos vêm do ambiente e nunca do repositório.
