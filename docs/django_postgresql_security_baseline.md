# Baseline de Seguranca Django + PostgreSQL (Producao)

## Django (obrigatorio)

- `DEBUG = False`
- `ALLOWED_HOSTS` restrito aos dominios reais
- `SECRET_KEY` apenas por variavel de ambiente
- `CSRF_TRUSTED_ORIGINS` configurado para dominios HTTPS
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_HSTS_SECONDS = 31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SECURE_PROXY_SSL_HEADER` configurado quando houver proxy/load balancer
- `X_FRAME_OPTIONS = "DENY"`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_REFERRER_POLICY = "same-origin"`

## PostgreSQL (obrigatorio)

- Usuario da aplicacao sem privilegios de superuser
- Banco com principio de menor privilegio por schema/tabela
- Conexao via TLS quando fora de rede privada confiavel
- Backup automatico com teste de restore recorrente
- Migracoes versionadas e revisadas por PR
- Nao executar alteracoes manuais em producao sem migracao auditavel

## CI/CD (obrigatorio)

- Lint (`ruff`) e format check (`black`) em toda PR
- SAST com `bandit`
- Auditoria de dependencias com `pip-audit`
- Secret scan em todo push/PR
- `python manage.py check --deploy` antes de deploy
- Bloqueio de merge sem checks de governanca e seguranca

## Operacao

- Logs sem dados sensiveis (PII, tokens, senhas)
- Monitoramento de erro, latencia e disponibilidade
- Alertas de falha de autenticacao e picos anormais
- Plano de resposta a incidente testado
