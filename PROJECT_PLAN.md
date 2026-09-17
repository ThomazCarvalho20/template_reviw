# Plano do Projeto

## 1) Nome provisório

Template Review

## 2) Finalidade do projeto

Este projeto tera como finalidade construir uma aplicacao web robusta em Django com PostgreSQL, com foco em:

- seguranca desde o inicio;
- qualidade de codigo;
- governanca de mudancas;
- base pronta para evolucao em producao.

## 3) Objetivos principais

- Entregar uma estrutura de projeto segura e escalavel.
- Garantir que toda mudanca passe por testes e validacoes de seguranca.
- Evitar regressao funcional e risco operacional em banco de dados.
- Manter rastreabilidade de decisoes tecnicas e de aprovacoes sensiveis.

## 4) Escopo inicial (MVP tecnico)

- Estrutura inicial Django organizada por apps.
- Integracao com PostgreSQL.
- Configuracoes de ambiente (`dev`, `homolog`, `prod`).
- Autenticacao e controle de acesso por perfil.
- Endpoints e telas iniciais do dominio de negocio (a definir na fase funcional).
- Pipeline CI com lint, testes e seguranca.

## 5) Escopo fora do MVP

- Integracoes externas complexas nao essenciais no inicio.
- Otimizacoes avancadas de performance antes da validacao funcional.
- Recursos sem requisito claro de negocio.

## 6) Stack e arquitetura base

- Backend: Python 3.12 + Django.
- Banco: PostgreSQL.
- Qualidade: `ruff`, `black`, `pytest`.
- Seguranca: `bandit`, `pip-audit`, `detect-secrets`.
- CI/CD: GitHub Actions com branch protection e checks obrigatorios.

Arquitetura prevista:

- separacao por camadas (apresentacao, aplicacao, dominio, persistencia);
- regras de negocio centralizadas;
- acesso ao banco com migracoes versionadas;
- configuracoes sensiveis via variaveis de ambiente.

## 7) Regras obrigatorias de implementacao

- Nenhuma mudanca entra sem teste.
- Toda mudanca passa por checklist de seguranca.
- Mudancas de banco/views sensiveis exigem aprovacao explicita registrada.
- PR obrigatoria com aprovacao antes de merge.
- Sem segredos no repositorio.

## 8) Fases de execucao

1. Fundacao tecnica:
- scaffold Django;
- configuracao de ambientes;
- conexao PostgreSQL;
- padroes de projeto.

2. Fundacao de seguranca:
- hardening inicial do Django;
- politicas de senha e sessao;
- protecoes de entrada e autorizacao.

3. Entrega funcional inicial:
- modelagem inicial de dominio;
- casos de uso principais;
- telas/endpoints do MVP.

4. Validacao e estabilizacao:
- testes de regressao;
- revisao de seguranca;
- ajustes para release.

5. Go-live controlado:
- deploy com checklist;
- monitoramento;
- plano de resposta a incidente.

## 9) Criterios de pronto (Definition of Done)

- Requisito implementado e revisado.
- Testes relevantes passando.
- Sem vulnerabilidade critica/alta sem mitigacao.
- Documentacao minima atualizada.
- Sem impacto sensivel em banco sem aprovacao formal.

## 10) Riscos principais e mitigacao

- Risco: mudancas sensiveis sem controle.
Mitigacao: gates de PR + branch protection + aprovacao obrigatoria.

- Risco: vazamento de segredo.
Mitigacao: `.env`, secret scan, revisao de PR e politica de segredos.

- Risco: regressao funcional.
Mitigacao: testes unitarios/integracao/regressao e bloqueio de merge em falha.

## 11) Proximos passos imediatos

1. Definir dominio funcional e primeiros modulos.
2. Criar scaffold Django com configuracao por ambiente.
3. Criar primeiro app com fluxo completo (model, service, endpoint, teste).
