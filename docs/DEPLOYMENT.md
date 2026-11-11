# Deploy do EducaDoc Social

A configuração disponível usa PostgreSQL 16, Gunicorn e WhiteNoise. Os arquivos de execução usam CSS já compilado; não é necessário Node.js no contêiner Python.

## Preparação

1. Copie `.env.production.example` para `.env.production` e preencha valores reais de domínio, chave secreta, banco e SMTP. O exemplo de produção agora é versionável; arquivos com credenciais reais permanecem ignorados.
2. Mantenha `USE_SQLITE=False`, `DB_HOST=db` e `DB_PORT=5432` na rede Compose. `DATABASE_URL` não é interpretada.
3. O `.dockerignore` exclui `.env` e arquivos de ambiente reais. Não acrescente credenciais à imagem ou ao repositório.
4. O CSS compilado acompanha o código em `static/css/tailwind.css`. Não é necessário executar uma compilação frontend para iniciar esta distribuição.
5. Configure proxy reverso com HTTPS. Sirva os arquivos estáticos coletados por WhiteNoise. Mantenha os documentos de mídia fora de rotas públicas; downloads passam pela aplicação.
6. Planeje backup e restauração conjunta de PostgreSQL e mídia, SMTP, monitoramento e armazenamento persistente. Avalie TLS do banco para serviços externos; `DATABASES` não define `sslmode` automaticamente.

## Inicialização autorizada

O entrypoint não executa migrações automaticamente por padrão. Em ambientes administrados por outra pessoa ou em produção, obtenha autorização para a alteração do banco. Após revisar o plano, execute:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d db
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web python manage.py migrate --plan
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml --env-file .env.production up -d web
```

O entrypoint aguarda PostgreSQL por até `DB_WAIT_TIMEOUT_SECONDS` (padrão 60), executa comandos explícitos quando fornecidos e, no início normal do web, coleta estáticos antes de iniciar Gunicorn. `RUN_MIGRATIONS=true` habilita migração automática somente se isso fizer parte da operação aprovada.

Para criar o administrador em uma instalação autorizada:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec web python manage.py createsuperuser
```

Acesse Instituições para cadastrar responsáveis e vínculos. Não há seed de dados acadêmicos nem contas padrão.

## Verificação

Consulte `/healthz/` no endereço final com HTTPS e valide cadastro, confirmação de e-mail real, importação, edição de campos, emissão, download privado e atendimento de solicitações. O endpoint verifica `SELECT 1`; não comprova SMTP, backup ou todos os fluxos.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f web
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f db
```

O volume de mídia deve ser privado. Em desenvolvimento, apenas fotos de perfil continuam com rota de mídia direta; modelos e emissões têm rotas de download autenticadas. Defina a política de entrega de fotos em produção separadamente.

Antes de disponibilizar a instalação, confirme:

- `/healthz/` responde HTTP 200 no endereço final.
- O acesso HTTPS, os hosts e as origens CSRF correspondem ao domínio.
- A conta administradora funciona e o SMTP entrega mensagens reais.
- Importação, preenchimento, download privado e solicitações funcionam.
- Banco e mídia possuem armazenamento persistente e recuperação testada.

Não reverta migrações após uso sem analisar os registros que seriam removidos.
