# Estagios para Producao

## Estagio 1 - Governanca e seguranca base

- [x] Regras de contribuicao e bloqueio de mudancas sensiveis.
- [x] CI com gates de checklist e mudancas de banco/views.
- [x] Branch protection com checks obrigatorios.

## Estagio 2 - Produto funcional (MVP)

- [x] Importacao e deteccao de campos para DOCX/XLSX/PDF.
- [x] Preenchimento dinamico por JSON.
- [x] Geracao de arquivo preenchido (DOCX/XLSX/PDF AcroForm).
- [x] Compartilhamento e convite por email.
- [x] Encerramento de template apenas pelo dono.

## Estagio 3 - Controle de acesso e auditoria

- [x] Revogacao de permissao.
- [x] Cancelamento de convite pendente.
- [x] Auditoria por template com historico de eventos.

## Estagio 4 - Pronto para deploy

- [x] Healthcheck (`/healthz/`).
- [x] Configuracao de logs para producao.
- [x] Hardening de cookies/headers/SSL.
- [x] Gunicorn + Whitenoise.
- [x] Dockerfile e `docker-compose.prod.yml`.
- [x] Script de inicializacao com migrate + collectstatic.

## Estagio 5 - Go-live (operacional)

- [ ] Configurar `.env.production` com segredos reais.
- [ ] Validar SMTP real para confirmacao de email.
- [ ] Subir stack e validar `/healthz/`.
- [ ] Criar superusuario em producao.
- [ ] Habilitar backup recorrente do banco.
- [ ] Configurar monitoramento e alertas.
- [ ] Executar checklist final de release.

## Estagio 6 - Pos-go-live

- [ ] Monitorar erros e performance nas primeiras 24h.
- [ ] Ajustar limites (workers, timeout, rate-limit) conforme carga real.
- [ ] Planejar sprint de melhoria continua.
