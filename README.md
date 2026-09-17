# Template Review

Sistema web para importacao de templates (`PDF`, `DOCX`, `XLSX`) e preenchimento dinamico de campos detectados via JSON.

## Stack

- Python
- Django
- PostgreSQL
- Tailwind CSS

## Execucao local

1. Criar ambiente virtual e instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Ajustar variaveis de ambiente a partir de `.env.example`.

3. Aplicar migracoes e criar usuario admin:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

4. Rodar servidor:

```bash
python manage.py runserver
```

## Funcionalidades iniciais

- Upload de template por tipo de arquivo.
- Deteccao de campos baseada em placeholders/estrutura do arquivo.
- Formulario dinamico com base no JSON de campos.
- Geracao de arquivo preenchido (DOCX/XLSX) e preenchimento de PDF com campos AcroForm.
- Cadastro/login com verificacao de e-mail (`django-allauth`).
- Compartilhamento de template por e-mail para usuarios ja cadastrados.
- Convite por e-mail com link de aceite para acesso ao template.
- Controle de encerramento de template apenas pelo dono.
- Layout base com menu lateral e cabecalho fixos.

## Fluxo de autenticacao

- Cadastro: `/accounts/signup/`
- Login: `/accounts/login/`
- Confirmacao de e-mail: `/accounts/email/`

Para ambiente local, o `EMAIL_BACKEND` padrao e `console`, entao o link de confirmacao aparece no terminal do `runserver`.

## Producao

Arquivos de deploy:

- `Dockerfile`
- `docker-compose.prod.yml`
- `scripts/entrypoint.sh`
- `deploy/gunicorn.conf.py`
- `.env.production.example`

Documentacao:

- `docs/DEPLOYMENT.md`
- `docs/PRODUCTION_STAGES.md`
- `docs/RELEASE_CHECKLIST.md`

Comando de subida:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
