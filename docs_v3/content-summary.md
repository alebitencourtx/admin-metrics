## O que é e para que serve

O **Admin Metrics** acompanha os oito reportes Santander que publicam o endpoint Admin do Open Finance. A cada hora, consulta somente `GET /open-banking/admin/v2/metrics`, preserva o corpo com SHA-256, normaliza as métricas declaradas, calcula sinais explicáveis e publica dashboard, manual e Parquet.

Responde a três perguntas: **o que exige atenção agora**, **qual endpoint concentra o problema** e **o que o observador conseguiu medir**. Não mede diretamente serviços de clientes; mede a resposta do Admin e os agregados declarados.

| Item | Resumo |
|---|---|
| Origens | Oito hosts Santander em catálogo fechado; Nissan e Renault são fontes distintas. |
| Cadência | Cron `17 * * * *` UTC; agenda do GitHub é *best effort*. |
| Entrega | Dashboard, `dashboard.json`, Parquet e manuais. |
| Grão | Observação = execução × reporte × endpoint; incidente = entidade × regra. |
| Janelas | Painel 72 h; estado 30 dias; bronze de dois ciclos; duas Releases aprovadas. |
| Snapshot local | 2026-11-10T18:37:28Z, oito fontes HTTP 200, 276 identidades; não é telemetria ao vivo. |

> Regra de negócio: o painel usa um ciclo completo e um único dia de referência por recorte. Se a tentativa atual não renova esse conjunto, os KPIs continuam rotulados como **DADOS ANTERIORES**, e a saúde da coleta reflete apenas a tentativa recente.

## Como usar o painel

O seletor **Reporte** é global: altera panorama, incidentes, tendências, endpoints, coleta, execuções e qualidade. O filtro usa o último ciclo válido daquele recorte, sem misturar fontes de ciclos ou dias diferentes.

| Seção | Use para |
|---|---|
| 01 · Panorama | KPIs, top cinco erros e cartões por fonte. |
| 02 · Incidentes | Severidade, evidência, confirmação e recuperação. |
| 03 · Tendências | Taxa de erro, média ou chamadas ao longo de 72 h. |
| 04 · Endpoints | Buscar sem acento, filtrar, ordenar e abrir o detalhe. |
| 05 · Saúde da coleta | HTTP, cobertura, identidades e duração do Admin. |
| 06 · Execuções | Matriz de 12 extrações por página e tentativas. |
| 07 · Qualidade | Flags de contrato e estados de delta. |
| 08 · Metodologia | Limiares e limites. |

Separe **última tentativa**, **último dado válido** e **dia de referência**. Uma tentativa vazia não renova os dados válidos; após duas horas sem panorama, o navegador marca os dados como desatualizados.

> Exemplo prático: com seis fontes válidas e duas vazias, a saúde fica `partial`. O panorama `all` pode continuar no último ciclo completo, enquanto o recorte de uma fonte saudável avança para o ciclo novo. O agregado não soma os dois.

O detalhe do endpoint separa as **observações próprias** do **histórico D−n declarado pelo banco** (`previousDays`); a visualização mostra D−1 a D−3. As duas séries não devem ser somadas.

> Atenção: HTTP 200 confirma a resposta, não a existência de métricas. `data_status=empty` significa resposta vazia; `invalid_report`, reporte inválido ou incompleto.

## Como os dados são formados

O pipeline roda em runner temporário. O estado é restaurado de uma Release aprovada, a coleta produz bronze, a análise aplica regras, o build materializa Arrow/DuckDB/Parquet e o site é publicado. Sem estado aprovado, o primeiro ciclo faz bootstrap.

```solution
{
  "title": "Fluxo resumido: coleta, análise e entrega",
  "cols": 4,
  "colWidth": 226,
  "colGap": 52,
  "inputs": { "label": "ENTRADAS" },
  "zones": [
    { "id": "s1", "title": "1 · AQUISIÇÃO", "subtitle": "catálogo fechado e bronze", "variant": "warm", "row": 0, "colStart": 1, "colSpan": 3 },
    { "id": "s2", "title": "2 · ANÁLISE E ENTREGA", "subtitle": "regras, estado e Pages", "variant": "cool", "row": 1, "colStart": 1, "colSpan": 3 }
  ],
  "nodes": [
    { "id": "admin", "col": 0, "row": 0, "shape": "cylinder", "role": "regulator", "title": "8 reportes Admin", "lines": ["`/open-banking/admin/v2/metrics`", "somente HTTPS"] },
    { "id": "collect", "col": 1, "row": 0, "step": 1, "role": "step", "title": "Coletar", "lines": ["4 simultâneas", "retry e paginação limitados"] },
    { "id": "bronze", "col": 2, "row": 0, "shape": "cylinder", "role": "analytical", "title": "Bronze SHA-256", "lines": ["corpo exato", "dois ciclos no pacote"] },
    { "id": "state", "col": 3, "row": 0, "shape": "cylinder", "role": "analytical", "title": "Estado 30 dias", "lines": ["`state.json`", "histórico e incidentes"] },
    { "id": "rules", "col": 0, "row": 1, "role": "regulator", "title": "Catálogo e regras", "lines": ["`reporters.json`", "`rules.json`"] },
    { "id": "analyze", "col": 1, "row": 1, "step": 2, "role": "step", "title": "Normalizar e avaliar", "lines": ["nulos explícitos", "deltas e incidentes"] },
    { "id": "gold", "col": 2, "row": 1, "shape": "cylinder", "role": "output", "title": "Gold", "lines": ["Arrow → DuckDB", "Parquet Zstandard"] },
    { "id": "pages", "col": 3, "row": 1, "role": "output", "title": "Pages", "lines": ["dashboard + manuais", "`dashboard.json`"] }
  ],
  "edges": [
    { "from": "admin", "to": "collect" },
    { "from": "rules", "to": "collect", "style": "dashed", "label": "catálogo" },
    { "from": "collect", "to": "bronze", "label": "hash" },
    { "from": "bronze", "to": "analyze", "fromSide": "bottom", "toSide": "top" },
    { "from": "rules", "to": "analyze", "style": "dashed", "label": "limiares" },
    { "from": "analyze", "to": "state", "fromSide": "top", "toSide": "bottom", "label": "estado" },
    { "from": "analyze", "to": "gold" },
    { "from": "gold", "to": "pages", "label": "artefatos" }
  ],
  "legend": [
    { "type": "box", "role": "regulator", "label": "Entradas" },
    { "type": "box", "role": "analytical", "label": "Bronze e estado" },
    { "type": "box", "role": "step", "label": "Etapas" },
    { "type": "box", "role": "output", "label": "Entrega" }
  ],
  "note": "O estado só é gravado após o build completo. O restore verifica checksum, manifesto e limites antes de alterar o destino."
}
```

```schema
{
  "title": "Entidades essenciais do estado e das projeções",
  "cols": 3,
  "colGap": 100,
  "rowGap": 56,
  "entities": [
    {
      "id": "runs",
      "name": "runs",
      "kind": "json",
      "grain": "1 run = 1 ciclo",
      "col": 0,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "name": "observed_at", "type": "utc" },
        { "name": "model_version", "type": "int" },
        { "name": "collection_health", "type": "object" }
      ]
    },
    {
      "id": "observations",
      "name": "observations",
      "kind": "table",
      "grain": "1 linha = run × reporter × endpoint",
      "col": 1,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "key": "FK", "name": "reporter_id", "type": "string" },
        { "name": "day", "type": "date" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" }
      ]
    },
    {
      "id": "incidents",
      "name": "incidents",
      "kind": "json",
      "grain": "1 ocorrência = entidade × regra",
      "col": 2,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "id", "type": "string" },
        { "name": "entity_id", "type": "string" },
        { "name": "rule", "type": "enum" },
        { "name": "status", "type": "enum" },
        { "name": "recovery_samples", "type": "int" }
      ]
    },
    {
      "id": "current",
      "name": "current_rows",
      "kind": "mart",
      "grain": "1 linha = último contexto por endpoint",
      "col": 1,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "name": "fresh", "type": "bool" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64?" },
        { "name": "mean_ms", "type": "int64?" }
      ]
    }
  ],
  "relations": [
    { "from": "runs", "to": "observations", "fromCard": "1", "toCard": "1..N", "label": "normaliza" },
    { "from": "observations", "to": "current", "kind": "lineage", "label": "último contexto" },
    { "from": "observations", "to": "incidents", "kind": "lineage", "label": "entity_id + regra" }
  ],
  "note": "Relações tracejadas são linhagem/identidade lógica, não FK SQL. O estado bruto aninhado permanece no JSON."
}
```

> Regra de negócio: `entity_id = SHA-256(reporter_id + endpoint)[:24]`. O mesmo endpoint em reportes diferentes é uma entidade diferente. `fresh` significa “mesma execução do último ciclo”, não idade do relógio.

## Regras, sinais e qualidade

- **Taxa de erro** = `100 × errors ÷ calls` somente com `calls > 0` e `0 ≤ errors ≤ calls`; caso contrário, nula.
- **Taxa de rejeição** = `100 × rejections ÷ calls` sob os mesmos critérios, com denominador próprio.
- **Média ponderada** = `Σ(mean_ms × calls) ÷ Σ(calls)` para médias e chamadas positivas. Não é p95.
- **Delta** só existe na mesma entidade, mesmo dia, fontes completas e contadores não decrescentes. Reporte idêntico não é tráfego novo.

| Regra | Limiar | Efeito |
|---|---|---|
| Erro | ≥ 5% com ≥ 100 chamadas | Atenção. |
| Erro crítico | ≥ 20% com ≥ 1.000 chamadas | Crítico. |
| Rejeição | ≥ 5% com ≥ 100 chamadas | Atenção, sem inferir causa. |
| Média | ≥ 2.000 ms | Atenção. |
| Média crítica | ≥ 4.000 ms com ≥ 100 chamadas | Crítico. |
| Regressão | ≥ 2× a mediana de ≥ 3 médias anteriores positivas | Atenção. |
| Falha de coleta | 1ª amostra atenção; 2ª consecutiva crítica | Incidente de coleta. |
| Confirmação | 2 detecções consecutivas | `confirmed=true`. |
| Recuperação | 2 amostras avaliáveis abaixo do limiar | `recovering` e depois `resolved`. |

> Exemplo prático: 2.000 chamadas com 500 erros = 25% e amostra suficiente: crítico. Já 120 chamadas com 30 erros = 25%, mas amostra abaixo de 1.000: atenção. Em deltas, 1.000→1.500 chamadas e 50→75 erros produzem 25 erros em 500 chamadas = 5%, não 5% do acumulado.

> Atenção: ausência, amostra baixa, contador inválido ou captura incompleta **não resolvem** um incidente. Só duas amostras avaliáveis consecutivas abaixo do limiar contam como recuperação. “Confirmado por persistência” não prova novos erros no intervalo.

> Limitação: os critérios são analíticos e configuráveis, não SLAs regulatórios. `errors` não identifica status HTTP; `rejections` não prova 429; 403 no Admin não prova indisponibilidade dos serviços.

## Operação e continuidade

Pré-requisitos: Python 3.11/3.12 64 bits; Node 22 apenas para testes. A instalação completa está no manual.

```powershell
.\.venv\Scripts\python.exe -m admin_metrics.cli collect
.\.venv\Scripts\python.exe -m admin_metrics.cli build
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory site
```

Use `build` para republicar sem nova observação. Parâmetros: `--root data --output site --config config`. Não execute dois escritores no mesmo root.

O GitHub Actions usa concorrência única. Em **Actions → Monitorar Admin e publicar Pages → Run workflow**, mantenha `refresh_data` marcado para coletar ou desmarque para republicar. Push em `main` republica sem coletar; sem estado, faz bootstrap. O cron é `17 * * * *` UTC.

| Situação | Comportamento | Ação |
|---|---|---|
| Build falha | Site e estado anteriores permanecem | Corrigir e reexecutar. |
| Deploy falha | Release candidata é descartada | Verificar Pages/permissões. |
| Deploy ok, confirmação falha | Draft pode permanecer | Conferir run e recibo antes de promover. |
| Fonte vazia ou 403 | Diagnóstico preservado, sem zero artificial | Não contornar bloqueio. |
| Cron atrasado | Agenda é *best effort* | Usar execução manual. |
| Lock abandonado | Escritor não reciclado automaticamente | Conferir processo e remover o lock com cuidado. |

```sql
-- Ranking do ciclo atual com denominador válido
SELECT reporter, path, calls, errors,
       ROUND(100.0 * errors / calls, 2) AS error_pct,
       mean_ms
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND source_complete AND calls > 0
  AND errors IS NOT NULL AND errors <= calls
ORDER BY errors DESC, calls DESC
LIMIT 25;
```

> Atenção: Pages e Releases não são uma transação distribuída. Um deploy aprovado com confirmação falha não deve ser “consertado” promovendo um draft sem recibo de deploy.

## Limites e referências

| Não conclua que | Porque | Leitura correta |
|---|---|---|
| A média é p95 | O contrato traz `averageResponse`, sem percentis. | “Média declarada”. |
| Erros têm status HTTP | `errors` é um contador agregado. | “Erros declarados”; investigar a origem. |
| Rejeição é 429 | `rejections` não identifica causa. | “Rejeições declaradas”. |
| 403 no Admin = serviço fora | Acesso recusado ao observador não prova indisponibilidade. | Separar coleta de serviço reportado. |
| Ausência de endpoint = ausência de oferta | O recorte pode não incluir o serviço. | Não inferir oferta. |
| O cron garante alerta em 1 h | GitHub Actions é *best effort*. | Conferir idade real e executar manualmente. |
| O snapshot local é a produção atual | É uma execução de implementação de 2026-11-10. | Consultar o dashboard atual. |

> Limitação: o monitor é single node, sem HA, autenticação corporativa, RBAC, SLA, alerta externo ou operação 24×7. Não é laudo de conformidade regulatória.

Referências: [Admin 2.0.1](https://raw.githubusercontent.com/OpenBanking-Brasil/openapi/main/swagger-apis/admin/2.0.1.yml), [Diretório oficial](https://data.directory.openbankingbrasil.org.br/participants), [dashboard](https://alebitencourtx.github.io/admin-metrics/), [repositório](https://github.com/alebitencourtx/admin-metrics) e [workflow](https://github.com/alebitencourtx/admin-metrics/actions/workflows/pages.yml). Para o detalhamento completo, abra o **Manual completo v3** no topo da página.
