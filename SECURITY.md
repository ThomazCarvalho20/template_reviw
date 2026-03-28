# Politica de Seguranca

Este documento define os requisitos minimos de seguranca para desenvolvimento, revisao e implantacao.

## 1) Objetivo

- Reduzir risco de invasao, quebra de integridade, indisponibilidade e vazamento de dados.
- Garantir que toda mudanca seja validada com foco em abuso e ataque.

## 2) Principios obrigatorios

- Secure by default: toda funcionalidade nasce com controles de seguranca.
- Least privilege: acessos minimos necessarios por usuario, servico e rotina.
- Defense in depth: controles em camadas (entrada, aplicacao, banco e operacao).
- Fail safe: em erro, negar por padrao sem expor detalhes internos.

## 3) Ameacas que devem ser tratadas

- SQL Injection.
- XSS.
- CSRF.
- SSRF.
- Brute force e abuso de endpoint.
- Escalacao de privilegio.
- Bypass de autenticacao/autorizacao.
- Upload de arquivo malicioso.
- Vazamento de segredo e dados sensiveis.
- Negacao de servico por uso excessivo.

## 4) Controles minimos de implementacao

- Validar e sanitizar toda entrada externa.
- Usar consultas parametrizadas no acesso ao banco.
- Aplicar validacao de autorizacao por acao, nao apenas por rota.
- Implementar rate limit e monitoramento para endpoints sensiveis.
- Proteger sessoes/tokens com boas praticas de expiração e revogacao.
- Validar upload por tipo real, extensao, tamanho e conteudo permitido.
- Nao registrar dados sensiveis em log.
- Armazenar segredos somente em variaveis de ambiente/cofre de segredos.

## 5) Regras de banco e views

- Mudanca de schema sem aprovacao explicita: proibido.
- Operacoes de upload/unload/import/export/carga sem aprovacao explicita: proibido.
- Alteracao de views de busca/insercao ja testadas sem aprovacao explicita: proibido.

## 6) Testes de seguranca obrigatorios

- Testes negativos para entradas maliciosas e payloads inesperados.
- Testes de autorizacao (acesso permitido e negado por perfil).
- Testes de tentativa de injecao e bypass.
- Testes de abuso de requisicao quando aplicavel.
- Evidencia dos testes deve acompanhar a PR.

## 7) Resposta a incidente (minimo)

- Registrar e classificar severidade (critica/alta/media/baixa).
- Conter impacto imediatamente.
- Corrigir causa raiz e validar com teste de regressao.
- Documentar linha do tempo e acao preventiva.

## 8) Bloqueio de entrega

- Mudancas sem validacao de seguranca e sem evidencias de teste nao podem ser implantadas.
- Risco critico/alto sem mitigacao validada bloqueia merge e deploy.
