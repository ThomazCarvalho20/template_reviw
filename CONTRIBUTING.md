# Contribuicao e Implementacao Segura

Este documento define o processo obrigatorio para qualquer mudanca no projeto.

## 1) Principios obrigatorios

- Qualidade e seguranca sao requisitos de entrega, nao opcional.
- Nenhuma mudanca entra sem teste.
- Nenhuma mudanca entra sem validacao de seguranca.
- Regras de banco e views do `PROJECT_RULES.md` sao mandatarias.

## 2) Fluxo obrigatorio de mudanca

1. Definir escopo da mudanca.
2. Avaliar impacto tecnico e de seguranca.
3. Implementar em branch dedicada.
4. Executar testes obrigatorios.
5. Executar checklist de seguranca.
6. Abrir PR com evidencias.
7. Aguardar aprovacao para merge/implantacao.

## 3) Checklist obrigatorio de testes (PR)

- [ ] Testes unitarios dos componentes alterados.
- [ ] Testes de integracao dos fluxos impactados.
- [ ] Testes de regressao dos fluxos criticos.
- [ ] Testes negativos (entradas invalidas e comportamento de erro).
- [ ] Evidencias anexadas (logs, resultados, cenarios testados).
- [ ] Sem testes quebrados apos a mudanca.

## 4) Checklist obrigatorio de seguranca (PR)

- [ ] Validacao e sanitizacao de entradas do usuario.
- [ ] Protecao contra injecao SQL (queries parametrizadas, sem concatenacao insegura).
- [ ] Protecao contra XSS (escape/output encoding adequado).
- [ ] Protecao contra CSRF quando aplicavel.
- [ ] Validacao de autenticacao/autorizacao por rota/acao.
- [ ] Controle de rate limit e bloqueio contra brute force onde necessario.
- [ ] Upload de arquivos validado (tipo, tamanho, extensao e conteudo).
- [ ] Segredos fora do codigo (sem senha/token hardcoded).
- [ ] Logs sem expor dados sensiveis.
- [ ] Mensagens de erro sem vazamento de detalhes internos.
- [ ] Dependencias revisadas e sem vulnerabilidade critica conhecida.

## 5) Regras obrigatorias para tentativas de ataque/quebra

- Toda funcionalidade nova ou alterada deve prever abuso intencional.
- Devem existir testes para cenarios de quebra, incluindo:
- entradas maliciosas;
- repeticao excessiva de requisicoes;
- payloads inesperados;
- tentativa de acesso sem permissao.
- Mudanca sem mitigacao para risco critico/alto nao pode ser aprovada.

## 6) Regras de banco, dados e views (bloqueio)

- E proibido alterar schema do banco sem aprovacao explicita.
- E proibido executar upload/unload/import/export/carga de dados sem aprovacao explicita.
- E proibido alterar view de busca/insercao ja criada e testada sem aprovacao explicita.

## 7) Criterios de bloqueio de merge

- PR deve ser bloqueada quando:
- faltar evidencia de testes;
- faltar checklist de seguranca;
- houver falha de teste;
- houver risco de seguranca sem mitigacao;
- houver acao sensivel de banco sem aprovacao registrada.

## 8) Evidencias minimas na PR

- Resumo tecnico da mudanca.
- Riscos identificados e mitigacoes.
- Lista de testes executados e resultado.
- Impacto em banco/views/dados (quando houver).
- Registro de aprovacao para acoes sensiveis.
