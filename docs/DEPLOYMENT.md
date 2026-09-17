# Deploy em Producao

## 1) Preparacao

1. Copie `.env.production.example` para `.env.production`.
2. Preencha segredos reais (`SECRET_KEY`, `DB_PASSWORD`, SMTP).
3. Ajuste dominio em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.

## 2) Subir stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## 3) Verificacoes

1. Healthcheck:

```bash
curl -f http://localhost:8000/healthz/
```

2. Logs da aplicacao:

```bash
docker compose -f docker-compose.prod.yml logs -f web
```

3. Logs do banco:

```bash
docker compose -f docker-compose.prod.yml logs -f db
```

## 4) Comandos uteis

- Reaplicar migrations manualmente:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
```

- Criar superusuario:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

- Coletar estaticos:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## 5) Recomendacoes obrigatorias antes do go-live

- Ativar HTTPS no proxy reverso da infraestrutura.
- Configurar backup automatico do PostgreSQL.
- Monitorar disponibilidade do endpoint `/healthz/`.
- Garantir acesso administrativo com senha forte e email verificado.
