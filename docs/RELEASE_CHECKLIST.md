# Release Checklist

## Pre-release

- [ ] Todos os testes passando (`python manage.py test -v 2`).
- [ ] Nenhuma vulnerabilidade critica/alta pendente no CI.
- [ ] Migrations revisadas e aprovadas.
- [ ] Variaveis de producao revisadas no `.env.production`.
- [ ] Dominios corretos em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.

## Deploy

- [ ] Build de imagem concluido sem erro.
- [ ] Containers `db` e `web` saudaveis.
- [ ] `migrate` aplicado com sucesso.
- [ ] `collectstatic` aplicado com sucesso.
- [ ] Endpoint `/healthz/` respondendo 200.

## Pos-deploy

- [ ] Login e cadastro funcionando.
- [ ] Confirmacao de email funcionando em SMTP real.
- [ ] Upload + preenchimento + download funcionando.
- [ ] Compartilhamento/convite e auditoria funcionando.
- [ ] Logs sem erro critico.
