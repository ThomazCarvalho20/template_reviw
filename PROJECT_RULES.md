# Regras do Projeto

Estas regras sao obrigatorias e valem para qualquer alteracao neste projeto.

## 1) Mudancas de estrutura do banco (schema)

- E proibido alterar a estrutura do banco sem aprovacao previa do responsavel do projeto.
- Isso inclui, sem limitacao:
- criar, alterar ou remover tabelas;
- criar, alterar ou remover colunas;
- alterar tipos, constraints, indices, chaves primarias/estrangeiras;
- renomear objetos de banco.
- Antes de qualquer mudanca estrutural, e obrigatorio:
- apresentar o plano da mudanca;
- explicar impacto e risco;
- aguardar autorizacao explicita.

## 2) Upload/Unload, importacao/exportacao e cargas no banco

- E proibido executar upload, unload, importacao, exportacao, carga ou descarga de dados sem consulta previa.
- Nao executar scripts de carga, restore, dump, seed, ETL ou sincronizacao sem aprovacao explicita.
- Sempre informar antes:
- objetivo da operacao;
- origem/destino dos dados;
- impacto esperado;
- plano de rollback.

## 3) Views de busca/insercao ja criadas e testadas

- E proibido alterar, substituir ou remover qualquer view de busca/insercao que ja esteja criada e testada sem consulta previa.
- Qualquer ajuste em view validada exige:
- justificativa tecnica;
- analise de impacto;
- aprovacao explicita antes da execucao.

## 4) Regra de bloqueio operacional

- Na duvida, nao executar.
- Se a tarefa envolver banco, dados, migracao ou views validadas, pausar e consultar antes de prosseguir.
- Sem aprovacao explicita, nenhuma acao sensivel deve ser realizada.

## 5) Forma de aprovacao

- Aprovacao deve ser objetiva e registrada, contendo:
- escopo da mudanca;
- ambiente (dev/homolog/producao);
- janela de execucao.
- Sem esse registro, considerar a mudanca como nao autorizada.

## 6) Regra obrigatoria de testes antes de implementar

- Toda e qualquer mudanca deve ser testada antes de ser implementada no projeto.
- Nenhuma alteracao pode ser considerada pronta sem evidencia de testes.
- Minimo exigido:
- testes unitarios dos pontos alterados;
- testes de integracao dos fluxos impactados;
- testes de regressao dos cenarios criticos;
- quando aplicavel, testes de seguranca.

## 7) Regra obrigatoria de seguranca

- Toda mudanca deve passar por validacao de seguranca antes da implementacao.
- E obrigatorio avaliar riscos de tentativa de quebra/invasao do sistema, incluindo:
- injecao SQL;
- XSS;
- CSRF;
- SSRF;
- autenticacao e autorizacao indevidas;
- escalacao de privilegio;
- brute force e abuso de endpoints;
- upload malicioso de arquivos;
- exposicao de dados sensiveis em logs/erros.
- Se houver risco relevante sem mitigacao validada, a mudanca nao deve ser implementada.
