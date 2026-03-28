## Resumo da mudanca

<!-- Descreva objetivo, impacto e escopo -->

## Evidencias de teste (obrigatorio)

- [ ] Testes unitarios executados
- [ ] Testes de integracao executados
- [ ] Testes de regressao executados
- [ ] Testes negativos executados
- [ ] Evidencias anexadas (logs, prints, relatorios)

## Checklist de seguranca (obrigatorio)

- [ ] Entradas validadas e sanitizadas
- [ ] Protecao contra SQL Injection
- [ ] Protecao contra XSS/CSRF (quando aplicavel)
- [ ] Autenticacao/autorizacao revisadas
- [ ] Sem segredo hardcoded
- [ ] Sem vazamento de dados sensiveis em logs/erros
- [ ] Dependencias revisadas

## Banco e views (obrigatorio)

- [ ] Nao ha mudanca de schema
- [ ] Nao ha upload/unload/import/export/carga
- [ ] Nao ha alteracao de view de busca/insercao ja testada

Se houver qualquer mudanca sensivel de banco/views:

`DB_APPROVAL: YES`
`DB_APPROVER: <nome>`
`DB_SCOPE: <escopo>`
`DB_ENV: <ambiente>`
`DB_WINDOW: <janela>`
