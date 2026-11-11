# EducaDoc Social

Sistema Django para importar e preencher modelos PDF, DOCX e XLSX, compartilhar documentos e acompanhar solicitações institucionais.

Este repositório contém os arquivos de execução e as instruções de instalação. Credenciais, banco de dados, documentos enviados, backups, testes, relatórios e ferramentas de desenvolvimento ficam fora do Git. A documentação de produção está em [Implantação com Docker](docs/DEPLOYMENT.md).

## O que é necessário

| Item | Finalidade |
| --- | --- |
| Python 3.12 e pip | Executar Django e instalar as dependências |
| PostgreSQL 16 | Banco de dados da aplicação |
| Git ou uma cópia dos arquivos do projeto | Obter o código |
| Ambiente virtual Python | Isolar as dependências instaladas |
| Arquivo `.env` local | Configurar banco, chave secreta, hosts e e-mail |
| Navegador | Acessar o sistema |
| SMTP em produção | Enviar confirmações de conta e convites |
| Docker com Compose, opcional | Executar a implantação em contêineres |

Node.js e npm não são necessários para executar esta distribuição: o CSS compilado já está em `static/css/tailwind.css`.

## Arquivos enviados

- `apps/`: código da aplicação e migrações; os testes são excluídos do envio.
- `config/`: configurações, rotas e inicialização Django.
- `templates/` e `static/`: interface e CSS compilado.
- `manage.py` e `requirements.txt`: comandos Django e dependências de execução.
- `deploy/`, `Dockerfile`, `docker-compose.prod.yml` e `scripts/entrypoint.sh`: implantação.
- `.env.example` e `.env.production.example`: exemplos sem credenciais reais.
- `README.md`, `docs/DEPLOYMENT.md`, `.gitignore` e `.dockerignore`: instruções e seleção de arquivos.

## 1. Preparar o Python

No Linux ou WSL, a partir da raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Windows com PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Preparar um banco PostgreSQL novo

Em uma instalação nova, crie um usuário e um banco pelo pgAdmin ou pelo `psql`. Com uma conta PostgreSQL administradora, este exemplo solicita a senha do usuário de forma interativa:

```text
psql -h localhost -U postgres
CREATE USER educadoc_user;
\password educadoc_user
CREATE DATABASE educadoc_social OWNER educadoc_user;
\q
```

O usuário da aplicação precisa poder criar as tabelas e sequências no banco escolhido. Preserve um banco existente; não execute a criação novamente nem substitua seus dados.

## 3. Configurar o ambiente

Em uma instalação nova, copie o exemplo:

```bash
cp .env.example .env
```

No PowerShell, use `Copy-Item .env.example .env`. Se `.env` já existir, preserve-o e revise os valores necessários.

Configure:

| Variável | Valor ou finalidade |
| --- | --- |
| `USE_SQLITE` | `False` para usar PostgreSQL |
| `DB_NAME` | Nome do banco criado |
| `DB_USER`, `DB_PASSWORD` | Usuário e senha definidos no PostgreSQL |
| `DB_HOST`, `DB_PORT` | Endereço do servidor e porta, normalmente `localhost` e `5432` |
| `DB_SCHEMA` | Vazio para o schema padrão; se informado, esse schema deve existir previamente |
| `SECRET_KEY` | Uma chave própria desta instalação |
| `DJANGO_DEBUG` | `True` no desenvolvimento local; `False` em produção |
| `ALLOWED_HOSTS` | Hosts aceitos, como `localhost,127.0.0.1` |

Gere a chave com:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copie o resultado para `SECRET_KEY` no `.env`. O código lê `DB_*`; `DATABASE_URL` não é utilizada.

Nesta instalação local já migrada, o schema é `educadoc_social`. Uma cópia nova do código não recebe esse banco nem a conta administradora existente. Para criar um schema explícito em outra instalação, o administrador do PostgreSQL pode executar `CREATE SCHEMA educadoc_social AUTHORIZATION educadoc_user;` antes de definir `DB_SCHEMA=educadoc_social`.

## 4. Criar as tabelas e o administrador

Em um banco novo ou numa atualização autorizada, confira o plano e aplique as migrações:

```bash
python manage.py migrate --plan
python manage.py migrate
python manage.py createsuperuser
```

Use o usuário criado para `/admin/`. Para entrar na interface da aplicação, use o e-mail cadastrado. A aplicação exige confirmação de e-mail; no desenvolvimento, o backend de console imprime o link no terminal. Não existe conta ou senha padrão incluída no código.

## 5. Iniciar e conferir

```bash
python manage.py check
python manage.py runserver
```

- Aplicação: `http://127.0.0.1:8000/`
- Administração: `http://127.0.0.1:8000/admin/`
- Conexão com o banco: `http://127.0.0.1:8000/healthz/`

Cadastre instituições e responsáveis, vincule usuários e importe os modelos. A mídia será criada em `media/`, fora do Git.

Para um teste local opcional sem PostgreSQL, defina `USE_SQLITE=True` antes de aplicar as migrações. Isso cria um banco SQLite separado; não transfere dados de PostgreSQL.

## Produção e dados

Siga o [guia de implantação](docs/DEPLOYMENT.md) para HTTPS, SMTP, Gunicorn, volumes e comandos Docker. Banco e mídia precisam de backup próprio: clonar o Git não recupera os dados da instalação. Os downloads de modelos e emissões passam pela aplicação para verificar as permissões.
