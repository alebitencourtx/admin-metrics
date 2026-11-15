## Resumo executivo e escopo

O **Admin Metrics · Observatório Santander** transforma os relatórios públicos do Admin do Open Finance em um painel operacional auditável. A cada hora, o projeto consulta os oito hosts Santander catalogados, preserva o corpo bruto de cada resposta, normaliza as métricas declaradas, calcula sinais de atenção e publica um dashboard estático, um JSON de consumo e um manual offline.

O problema que ele resolve é específico: separar **o que o banco declarou** do **o que o observador conseguiu medir**. A duração e o status HTTP da nossa tentativa ao Admin são evidências da coleta; as médias, erros e rejeições dos serviços são valores autodeclarados pelo Santander. O projeto mantém essas duas camadas visíveis e não as mistura.

<div class="cards">
<div class="card"><h3>Pergunta que responde</h3><p>Quais endpoints reportados estão acima dos limiares de erro, rejeição ou latência, em qual fonte e com qual evidência?</p></div>
<div class="card"><h3>O que entrega</h3><p>Dashboard, payload JSON, Parquet/DuckDB, estado versionado em Release e um manual HTML que funciona sem servidor.</p></div>
<div class="card"><h3>O que não é</h3><p>Não é laudo de conformidade, medidor de p95, teste sintético dos serviços de clientes ou prova de causa de uma rejeição.</p></div>
</div>

### Em uma página

| Dimensão | Implementação atual |
|---|---|
| Origens | Oito hosts `*.api.santander.com.br`, todos no caminho `GET /open-banking/admin/v2/metrics` |
| Catálogo | `config/reporters.json`, com URL, CNPJ, empresa e rótulo; vínculo conferido no Diretório oficial e registrado em `config/catalog-evidence.json` |
| Cadência | GitHub Actions em `17 * * * *` UTC, além de push e execução manual |
| Janela do painel | 72 horas de observações próprias, com eixo fixo mesmo quando há poucas amostras |
| Histórico durável | 30 dias de ciclos normalizados e incidentes resolvidos; dois ciclos de bronze local |
| Entrega estática | `site/index.html`, `site/dashboard.json`, `site/documentacao.html` e `site/docs_v2/documentacao-v2.html` |
| Entrega analítica | `data/gold/*.parquet`, `data/gold/warehouse.duckdb` e o estado `data/state.json` |
| Durabilidade remota | Releases `state-<run>-<attempt>` com `state.zip`, `manifest.json`, bronzes e `SHA256SUMS`; até dois pacotes aprovados |
| Consumo | Dashboard no navegador, JSON para integrações e receitas SQL/DuckDB sobre Parquet |
| Operação | Um único escritor por diretório de dados, lock explícito, restauração apenas em raiz vazia e promoção somente após deploy comprovado |

### Quem usa o quê

| Leitor | Pergunta principal | Entrada recomendada |
|---|---|---|
| Gestão e operação | “O que exige atenção agora?” | [Uso do dashboard](#uso) e [Regras de negócio](#regras) |
| Analista de dados | “Como consultar e comparar os números?” | [Consulta e consumo](#consumo) e [Modelo de dados](#dados) |
| Engenharia | “Como a coleta e a publicação funcionam?” | [Arquitetura](#arquitetura) e [Fluxo](#fluxo) |
| Suporte / plantão | “Como recuperar uma execução?” | [Operação](#operacao) e [Qualidade](#qualidade) |

### Fronteiras explícitas

- O monitor chama **somente** os oito endpoints Admin do catálogo. As URIs de clientes, pagamentos, contas e consentimentos citadas dentro do relatório são validadas como texto e **nunca** acessadas.
- A coleta é uma fotografia do acumulado declarado no dia. Ela não mede cada transação, não identifica o status HTTP de cada erro e não transforma rejeição em diagnóstico de causa.
- A média declarada é uma média, não p95, p99 ou distribuição. O projeto não calcula percentis a partir dela.
- O dia analítico é uma convenção do observador, derivada do `HTTP Date` da página e convertida para `America/Sao_Paulo`. Ele não prova o fuso de consolidação da origem.
- Ausência de métrica é tratada como **indisponível**, não como zero. Um zero só aparece quando a origem declarou zero.

> Regra de negócio: o painel publica o último ciclo completo e coerente por recorte. Quando a tentativa atual não consegue renovar esse ciclo, os valores anteriores permanecem identificados como **DADOS ANTERIORES** e a saúde da coleta descreve a tentativa real.

> Atenção: os números deste manual foram observados no snapshot local de **10/11/2026 18:37 UTC** (`initial-local-20261110`). Eles servem para explicar a implementação e não representam a produção deste momento.

> Limitação: o repositório prova a implementação, não a execução bem-sucedida em produção. Datas, volumes e estados de saúde mudam a cada publicação; consulte o dashboard e as Releases para o estado corrente.

## Estado atual observado

Esta seção descreve o snapshot local disponível no checkout usado para documentar a revisão `5a8cda6`. A fonte é o arquivo gerado `site/dashboard.json`, não uma consulta ao vivo. O snapshot contém **um único ciclo** (`initial-local-20261110`), portanto os intervalos aparecem como `first_observation` e não há série histórica própria para comparar.

| Indicador do snapshot | Valor observado |
|---|---|
| Data e hora da observação | `2026-11-10T18:37:28Z` |
| Ciclo | `initial-local-20261110` |
| Fontes na tentativa | 8 de 8 com HTTP 200 e cobertura conciliada |
| Identidades de endpoint | 276 |
| Dia de referência | `2026-11-10` |
| Chamadas declaradas no dia | 82.209.558 |
| Erros declarados no dia | 1.212.481 |
| Incidentes abertos no snapshot | 57 (41 de taxa de erro, 11 de regressão de latência, 5 de média elevada) |
| Severidade dos incidentes | 49 de atenção e 8 críticos |
| Ocorrências de qualidade | 276 de horário declarado divergente; 143 de TPS médio acima do pico; 11 de uptime 100% com downtime positivo |
| Ciclos retidos no estado | 1 |
| Pontos publicados | 276 |

```chart
{"type":"bar","title":"Identidades Admin por reporte no snapshot local","unit":"identidades","source":"site/dashboard.json · snapshot local de 2026-11-10","asOf":"2026-11-10T18:37Z","data":[{"label":"Santander CCVM","value":23},{"label":"Aymoré","value":27},{"label":"Getnet","value":15},{"label":"Hyundai Capital","value":22},{"label":"RCI · Nissan","value":16},{"label":"Santander","value":112},{"label":"RCI · Renault","value":16},{"label":"Toro","value":45}]}
```

```chart
{"type":"bar","title":"Ocorrências de qualidade no snapshot local","unit":"ocorrências","source":"site/dashboard.json · snapshot local de 2026-11-10","asOf":"2026-11-10T18:37Z","data":[{"label":"Horário declarado divergente","value":276,"variant":"warning"},{"label":"TPS médio acima do pico","value":143,"variant":"warning"},{"label":"Uptime 100% com downtime","value":11,"variant":"danger"}]}
```

### Leitura por reporte

| Reporte | Identidades | Chamadas | Erros | Taxa de erro | Média declarada |
|---|---:|---:|---:|---:|---:|
| Santander CCVM | 23 | 133.427 | 775 | 0,58% | 224,61 ms |
| Aymoré | 27 | 20.119 | 1.314 | 6,53% | 166,85 ms |
| Getnet | 15 | 9.487 | 110 | 1,16% | 186,02 ms |
| Hyundai Capital | 22 | 1.298 | 110 | 8,47% | 179,24 ms |
| RCI · Nissan | 16 | 339 | 95 | 28,02% | 321,53 ms |
| Santander | 112 | 81.665.261 | 1.198.290 | 1,47% | 1.186,65 ms |
| RCI · Renault | 16 | 349 | 103 | 29,51% | 274,55 ms |
| Toro | 45 | 379.278 | 11.684 | 3,08% | 217,09 ms |

> Exemplo prático: no snapshot, RCI · Nissan e RCI · Renault compartilham o mesmo CNPJ, mas aparecem como reportes distintos porque a identidade interna é o `reporter_id` do catálogo, não o CNPJ. O mesmo acontece com serviços potencialmente compartilhados entre reportes: o agregado soma o que cada fonte declarou, sem garantir transações únicas entre instituições.

### O que o snapshot permite e não permite concluir

| Pergunta | Resposta com o snapshot | Cuidado de leitura |
|---|---|---|
| Quais endpoints concentram mais erros? | Sim, pelo ranking do painel e pela tabela de endpoints | O ranking usa valores declarados no dia; não é taxa de chegada nem prova de incidente real |
| A média de resposta piorou? | Não com um único ciclo | É necessário pelo menos um intervalo válido e, para regressão, três médias diárias anteriores positivas |
| O Admin está fora do ar? | Não se conclui de uma resposta 200 | A saúde da coleta mede nossa tentativa; um relatório vazio ou inválido é diagnóstico da fonte, não indisponibilidade dos demais serviços |
| O horário do banco está correto? | Há 276 linhas com `reported_clock_skew` no snapshot | O projeto sinaliza a divergência de aproximadamente três horas e não corrige o `requestTime` silenciosamente |
| Os valores de uptime são confiáveis? | Há 11 conflitos entre uptime 100% e downtime positivo | O conflito é registrado em `quality`; o valor original permanece para inspeção |

> Limitação: este snapshot tem apenas o primeiro ciclo e todos os intervalos em `first_observation`. Ele é útil para conferir contratos e apresentação, mas insuficiente para avaliar tendência, recuperação de incidentes ou estabilidade ao longo do tempo.

## Uso do dashboard e leitura executiva

O dashboard publicado está em [alebitencourtx.github.io/admin-metrics](https://alebitencourtx.github.io/admin-metrics/) e exige apenas um navegador. A página carrega `data.js` e `app.js` do próprio site; a política de segurança bloqueia conexões de rede, então a consulta é sempre ao payload já publicado. O manual runtime fica em `documentacao.html` e esta documentação v2 fica em `docs_v2/documentacao-v2.html`, ambos acessíveis pelo rodapé lateral do dashboard.

### Leitura em 60 segundos

1. Confira o aviso de **frescor** no topo: ele separa a última tentativa da última data com dados válidos do panorama.
2. Olhe os quatro indicadores do panorama: fontes com dados utilizáveis, chamadas declaradas, taxa de erro e média ponderada.
3. Leia o cartão executivo: ele informa se há sinal crítico, sinal de atenção ou cobertura insuficiente.
4. Abra **Incidentes** e priorize os críticos; confirme se o sinal é provisório ou confirmado por persistência.
5. Use **Endpoints** para localizar o serviço e clique no caminho para ver dias anteriores declarados, deltas, flags e SHA.
6. Use **Saúde da coleta** e **Monitor de execuções** para distinguir problema de dados de problema de publicação.
7. Exporte o recorte atual em CSV quando precisar investigar fora do painel.

### As oito seções

| Seção | Pergunta que responde | O que entrega |
|---|---|---|
| 01 · Panorama executivo | O que exige atenção agora? | Quatro KPIs, leitura do recorte, top 5 de erros e cartões por reporte |
| 02 · Incidentes | Quais sinais estão abertos, em recuperação ou resolvidos? | Severidade, regra, evidência, primeira observação e persistência |
| 03 · Tendências | Como as métricas evoluem na janela? | Séries de erro, média declarada, chamadas e duração da tentativa Admin |
| 04 · Endpoints | Qual serviço está pior e com qual contexto? | Busca, família, ordenação, paginação e detalhe por endpoint |
| 05 · Saúde da coleta | O que o observador conseguiu medir? | HTTP, cobertura, identidades, duração e diagnóstico por fonte |
| 06 · Monitor de execuções | O que aconteceu em cada extração? | Matriz extração × API, 12 execuções por página, tentativas e SHA |
| 07 · Qualidade do reporte | Quais inconsistências mudam a interpretação? | Contagem de flags e estados de intervalo |
| 08 · Metodologia | Quais critérios e limites foram aplicados? | Regras configuráveis, fontes oficiais e resumo metodológico |

### Filtros e navegação

| Controle | Efeito | Persistência |
|---|---|---|
| Reporte | Filtra panorama, incidentes, tendências, endpoints, execuções e qualidade para uma fonte | URL (`?reporter=...`) |
| Estado do incidente | Abertos/em recuperação, todos ou somente críticos ativos | Apenas na sessão |
| Métrica de tendência | Taxa de erro, média declarada ou chamadas acumuladas | Apenas na sessão |
| Busca de endpoint | Filtra por caminho e nome do reporte, ignorando acentos | URL (`?q=...`) |
| Família | Restringe pela primeira parte do caminho depois de `/open-banking/` | URL (`?family=...`) |
| Ordenação | Erros, taxa, média, chamadas ou nome do caminho | URL (`?sort=...`) |
| Paginação | 25 endpoints por página; 12 execuções por página no monitor | Apenas na sessão |
| Exportar endpoints | Gera CSV do recorte visível, com BOM e proteção contra fórmulas | Download local |

A busca usa normalização NFD e remove diacríticos, então `Aymore` encontra `Aymoré`. Os filtros de URL são restaurados ao abrir a página e atualizados com `history.replaceState` sem recarregar o dashboard.

### Como interpretar o frescor

| Situação exibida | O que significa | Como agir |
|---|---|---|
| “Última tentativa” recente e “Últimos dados válidos” recente | Coleta e panorama coerentes | Leitura normal |
| “Última tentativa” recente, mas “Últimos dados válidos” antigo | A tentativa atual não renovou o panorama | Ver saúde da coleta; os KPIs são anteriores e estão rotulados |
| Aviso com “DADOS ANTERIORES” | O painel preservou o último ciclo completo e um único dia de referência | Não trate os valores como novos; verifique a fonte e o motivo |
| Aviso de dados desatualizados | A idade do último panorama excede `stale_after_hours` (2 horas por padrão) | Verifique atraso do Actions, falha de fonte ou publicação |
| “Nenhum ciclo completo disponível” | Não há panorama coerente para o recorte | Métricas aparecem como “—”; não são convertidas em zero |
| Fonte “HTTP 200 sem dados” | A resposta foi HTTP, mas o corpo não trouxe métricas | Verifique a origem e o histórico; não é o mesmo que falha HTTP |
| Fonte “Reporte inválido” | O corpo veio, mas não reconciliou contrato ou cobertura | Consulte o diagnóstico e as tentativas preservadas |

> Regra de negócio: o painel nunca mistura fontes de ciclos diferentes no agregado. O panorama “Todos” só é aceito quando todas as oito fontes têm dados válidos, cobertura reconciliada e um único dia de referência. O filtro por fonte usa o último ciclo válido daquele recorte.

### O que evitar

- **Somar snapshots**: as chamadas são acumuladas do dia; somar dois horários conta o mesmo tráfego duas vezes.
- **Comparar média com p95**: a origem declara média; não há distribuição nem percentis.
- **Atribuir causa**: erro não traz status HTTP por endpoint e rejeição não prova 429, bloqueio ou falha de negócio.
- **Somar reportes como transações únicas**: serviços compartilhados podem aparecer em mais de uma instituição.
- **Interpretar ausência como zero**: valores nulos ficam fora do denominador; zero só aparece quando informado.
- **Usar o CSV sem conferir filtros**: a exportação reflete exatamente o recorte visível, não o universo inteiro.

> Atenção: o botão de exportação neutraliza campos iniciados por `=`, `+`, `-`, `@`, tabulação ou retorno de carro, prefixando-os com apóstrofo. Ainda assim, trate o arquivo como dado de origem não confiável ao abri-lo em planilhas.

## Arquitetura da solução

A solução é um pipeline batch de um único nó, executado no runner do GitHub Actions ou localmente. Não há banco de dados servidor, fila, API própria ou processo residente: o estado é um JSON versionado, o warehouse é um arquivo DuckDB recriado a cada build e a publicação é um conjunto de arquivos estáticos.

```solution
{
  "title": "Arquitetura em dois estágios · coleta auditável e publicação estática",
  "cols": 4,
  "colWidth": 206,
  "colGap": 44,
  "inputs": { "label": "ENTRADAS" },
  "zones": [
    {
      "id": "coleta",
      "title": "ESTÁGIO 1 · COLETA E ANÁLISE",
      "subtitle": "a cada execução com refresh",
      "variant": "warm",
      "row": 0,
      "colStart": 1,
      "colSpan": 3
    },
    {
      "id": "publicacao",
      "title": "ESTÁGIO 2 · APRESENTAÇÃO E DURABILIDADE",
      "subtitle": "panorama, build e Pages",
      "variant": "cool",
      "row": 1,
      "colStart": 1,
      "colSpan": 2
    }
  ],
  "nodes": [
    {
      "id": "admin",
      "col": 0,
      "row": 0,
      "shape": "cylinder",
      "role": "regulator",
      "title": "8 hosts Admin",
      "lines": [
        "`GET /admin/v2/metrics`",
        "catálogo + evidência do Diretório"
      ]
    },
    {
      "id": "release",
      "col": 0,
      "row": 1,
      "shape": "cylinder",
      "role": "info",
      "title": "Release aprovada",
      "lines": [
        "`state.zip` + `SHA256SUMS`",
        "até 2 pacotes"
      ]
    },
    {
      "id": "coletar",
      "col": 1,
      "row": 0,
      "step": 1,
      "role": "step",
      "title": "Coletar",
      "lines": [
        "HTTP/2 · 4 em paralelo",
        "paginação, retry e bronze"
      ]
    },
    {
      "id": "analisar",
      "col": 2,
      "row": 0,
      "step": 2,
      "role": "step",
      "title": "Normalizar e analisar",
      "lines": [
        "contratos, dia e deltas",
        "saúde, qualidade e incidentes"
      ]
    },
    {
      "id": "estado",
      "col": 3,
      "row": 0,
      "shape": "cylinder",
      "role": "analytical",
      "title": "Estado + warehouse",
      "lines": [
        "`data/state.json`",
        "`warehouse.duckdb` + Parquet"
      ],
      "meta": "30 dias de ciclos"
    },
    {
      "id": "panorama",
      "col": 1,
      "row": 1,
      "step": 3,
      "role": "step",
      "title": "Montar panorama",
      "lines": [
        "último ciclo completo",
        "um dia por escopo"
      ]
    },
    {
      "id": "publicar",
      "col": 2,
      "row": 1,
      "step": 4,
      "role": "step",
      "title": "Publicar",
      "lines": [
        "dashboard + manual",
        "assets endereçados por hash"
      ]
    },
    {
      "id": "pages",
      "col": 3,
      "row": 1,
      "shape": "cylinder",
      "role": "output",
      "title": "Pages + Release",
      "lines": [
        "`site/` no GitHub Pages",
        "candidato → deploy → aprovação"
      ]
    }
  ],
  "edges": [
    { "from": "admin", "to": "coletar", "label": "relatórios públicos" },
    { "from": "release", "to": "coletar", "style": "dashed", "label": "restaura estado aprovado" },
    { "from": "coletar", "to": "analisar" },
    { "from": "analisar", "to": "estado", "label": "commit lógico" },
    { "from": "estado", "to": "panorama", "label": "ciclos retidos" },
    { "from": "panorama", "to": "publicar" },
    { "from": "publicar", "to": "pages", "label": "artefatos" },
    { "from": "publicar", "to": "release", "channel": "bottom", "style": "dashed", "label": "novo candidato quando há refresh" }
  ],
  "legend": [
    { "type": "box", "role": "regulator", "label": "Origem regulatória e dado declarado" },
    { "type": "box", "role": "analytical", "label": "Estado e projeções analíticas" },
    { "type": "box", "role": "step", "label": "Etapas executáveis" },
    { "type": "dashed", "role": "neutral", "label": "Leitura ou retorno de estado" }
  ],
  "note": "A coleta e a publicação são independentes: o workflow pode falhar em uma fonte e ainda publicar diagnóstico. O estado só avança depois que o build e os artefatos forem gerados."
}
```

| Objeto | Papel | Lido / gravado |
|---|---|---|
| `config/reporters.json` | Catálogo dos oito hosts e identidades | Lido antes da coleta; qualquer URL fora do padrão bloqueia a execução |
| `config/rules.json` | Limiares, janelas, retenção e agenda | Lido e validado antes da coleta; registrado no ciclo |
| `data/state.json` | Estado lógico versionado | Lido no início; gravado somente após build bem-sucedido |
| `data/bronze/<sha>.json` | Corpo HTTP integral endereçado por SHA-256 | Gravado durante a coleta; dois ciclos recentes permanecem |
| `data/gold/warehouse.duckdb` | Warehouse local recriado no build | Gravado e consultado no build; não é publicado como site |
| `data/gold/*.parquet` | Projeções Arrow comprimidas com Zstandard | Gravadas no build; consumo analítico |
| `site/` | Dashboard, payload, manual e assets | Gerado e publicado no GitHub Pages |
| Release `state-*` | Pacote durável do estado e bronzes | Criada como draft; promovida após deploy comprovado |

### Componentes e responsabilidades

| Componente | Responsabilidade | Não faz |
|---|---|---|
| `collect.py` | TLS, HTTP/2, timeout, concorrência, paginação, retry, deduplicação e bronze | Não chama endpoints de clientes e não segue redirecionamentos |
| `contracts.py` | Valida URIs declaradas sem executá-las | Não faz requisição nem resolve DNS |
| `storage.py` | SHA-256, escrita atômica, lock e load do estado | Não publica e não decide regra |
| `analysis.py` | Normaliza campos, calcula dia, qualidade, deltas, sinais e incidentes | Não inventa status HTTP, causa ou p95 |
| `health.py` | Classifica a tentativa e a saúde da coleta | Não transforma publicação bem-sucedida em saúde dos dados |
| `panorama.py` | Escolhe um ciclo completo e um dia por escopo | Não mistura fontes de ciclos diferentes |
| `build.py` | Arrow, DuckDB, marts, Parquet, HTML, assets e cópia da documentação v2 | Não altera o estado |
| `marts.sql` | Define as agregações SQL de reporte, família e tendência | Não define limiares de incidente |
| `rules.py` | Valida o conjunto exato de parâmetros e gera o cron | Não aplica regra analítica diretamente |
| `documentation.py` | Gera o manual runtime autocontido | Não substitui esta documentação v2 |
| `web/` | Dashboard estático com filtros, gráficos e detalhes | Não consulta banco nem rede em runtime |
| `scripts/cloud_pipeline.py` | Restore, candidato, promoção, descarte e retenção | Não decide se um dado é válido |
| Workflows | Agenda, testes, build, deploy e confirmação | Não corrigem dados da origem |

### Topologia de execução

| Ambiente | O que acontece |
|---|---|
| GitHub Actions | `prepare` restaura a Release aprovada mais recente, coleta ou republica, gera `site/` e cria um candidato draft quando há refresh |
| GitHub Pages | Publica o conteúdo de `site/` como artefato estático; não executa backend |
| GitHub Releases | Guarda até dois pacotes aprovados com estado, bronzes, manifesto e checksums |
| Checkout local | Permite coletar, buildar e servir `site/` em `127.0.0.1`; requer as dependências Python |
| Navegador | Abre o dashboard e o manual; CSP e ausência de CDN mantêm a leitura offline |

> Regra de negócio: o estado é a fonte de verdade lógica. O `warehouse.duckdb` e os Parquet são projeções recriadas a cada build, e o site é uma projeção de apresentação. Nenhum artefato publicado é lido de volta como insumo da análise.

> Atenção: o build ocorre antes da gravação de `state.json`. Se a geração do manual, do HTML ou dos marts falhar, o estado e o site publicado anterior permanecem intactos; a próxima execução parte do último estado válido.

> Limitação: o site é público e não possui autenticação corporativa, controle de acesso por usuário ou medição contínua dos serviços de clientes. O repositório e as Releases são a fronteira de confiança operacional.

## Fluxo de coleta, análise e publicação

O fluxo nominal é uma execução com `refresh=True`: restaura o último estado aprovado quando necessário, coleta as oito fontes, aplica a análise, valida o estado, gera os artefatos e só então grava o novo `state.json`. Uma execução de republicação usa `refresh=False` e não cria nova observação.

```flow
{
  "title": "Fluxo de decisão entre nova coleta, análise e publicação",
  "cols": 4,
  "colWidth": 214,
  "colGap": 38,
  "zones": [
    {
      "id": "entrada",
      "title": "1 · GATILHO E ESTADO",
      "subtitle": "push, agenda ou execução manual",
      "variant": "neutral",
      "row": 0,
      "colStart": 0,
      "colSpan": 2
    },
    {
      "id": "processo",
      "title": "2 · PROCESSAMENTO E PUBLICAÇÃO",
      "subtitle": "coleta condicional, análise e build",
      "variant": "teal",
      "row": 0,
      "rowSpan": 2,
      "colStart": 2,
      "colSpan": 2
    }
  ],
  "nodes": [
    { "id": "gatilho", "col": 0, "row": 0, "step": 1, "role": "step", "title": "Receber gatilho", "lines": ["push, cron ou `workflow_dispatch`"] },
    { "id": "refresh", "col": 1, "row": 0, "shape": "decision", "role": "warning", "title": "Nova coleta?", "lines": ["`refresh_data` ou agenda"] },
    { "id": "coletar", "col": 2, "row": 0, "step": 2, "role": "step", "title": "Coletar e normalizar", "lines": ["8 fontes · paginação", "bronze por SHA-256"] },
    { "id": "analisar", "col": 3, "row": 0, "step": 3, "role": "step", "title": "Aplicar análise", "lines": ["deltas, sinais", "incidentes e saúde"] },
    { "id": "restaurar", "col": 1, "row": 1, "role": "info", "title": "Restaurar release", "lines": ["somente raiz vazia", "estado aprovado"] },
    { "id": "cobertura", "col": 2, "row": 1, "shape": "decision", "role": "warning", "title": "Cobertura completa?", "lines": ["8 fontes e um dia"] },
    { "id": "build", "col": 3, "row": 1, "step": 4, "role": "step", "title": "Build e publicar", "lines": ["marts + HTML", "site + manual"] },
    { "id": "pacote", "col": 0, "row": 1, "step": 5, "role": "output", "title": "Empacotar candidato", "lines": ["se houve refresh", "draft + checksums"] }
  ],
  "edges": [
    { "from": "gatilho", "to": "refresh" },
    { "from": "refresh", "to": "coletar", "branch": "yes", "label": "Sim · nova amostra" },
    { "from": "refresh", "to": "restaurar", "branch": "no", "label": "Não · republicar" },
    { "from": "coletar", "to": "analisar" },
    { "from": "analisar", "to": "cobertura" },
    { "from": "cobertura", "to": "build", "branch": "yes", "label": "Sim · ciclo válido" },
    { "from": "cobertura", "to": "build", "branch": "no", "style": "dashed", "label": "Não · diagnóstico" },
    { "from": "restaurar", "to": "build", "style": "dashed", "label": "estado anterior" },
    { "from": "build", "to": "pacote", "channel": "bottom", "label": "se houve refresh" }
  ],
  "legend": [
    { "type": "box", "role": "warning", "label": "Decisão operacional" },
    { "type": "box", "role": "step", "label": "Etapa executável" },
    { "type": "box", "role": "output", "label": "Pacote durável" },
    { "type": "dashed", "role": "neutral", "label": "Caminho de republicação ou diagnóstico" }
  ],
  "note": "Mesmo quando nenhuma fonte entrega métricas válidas, a execução pode concluir, publicar o diagnóstico e preservar o panorama anterior. Sucesso do workflow significa processamento e publicação concluídos, não saúde dos dados."
}
```

### Ordem efetiva da execução

1. **Validar configuração** — `validate_reporters` confere lista, campos obrigatórios, CNPJ de 14 dígitos, unicidade de `id` e URL exata; `validate_rules` exige o conjunto completo de parâmetros e limites coerentes.
2. **Adquirir o lock** — `data/.writer.lock` é criado com `O_EXCL`. Se já existir, a execução falha com “Escritor ativo ou lock abandonado”.
3. **Carregar o estado** — `state.json` versão 1 é lido; se não existir, o estado vazio contém `runs`, `observations`, `incidents` e `latest_rows`.
4. **Reconciliar links de execução** — recibos de Release podem preencher `execution_url` de ciclos antigos; links não são adivinhados por horário.
5. **Coletar quando `refresh=True`** — um `run_id` UTC com sufixo aleatório é criado; fontes anteriormente válidas são passadas para a política de repetição de resposta vazia.
6. **Aplicar a análise** — normalização, dia, qualidade, intervalos, incidentes e saúde são calculados; `model_version=3` é gravado no ciclo.
7. **Validar o estado** — `archive.validate` verifica versão, modelo suportado, unicidade de run, referências e hashes de bronze recentes.
8. **Gerar marts e artefatos** — DuckDB recriado, cinco Parquet, payload, dashboard, manual runtime, assets e cópia da documentação v2.
9. **Gravar o estado** — somente depois do build; em seguida, o GC remove bronzes fora dos dois ciclos recentes.
10. **Publicar e confirmar** — GitHub Pages recebe `site/`; se houve refresh, um draft de Release é criado e só é promovido após o job `deploy` comprovadamente concluído com sucesso.

### Coleta em detalhe

| Parâmetro / comportamento | Valor implementado | Efeito |
|---|---|---|
| Protocolo | HTTPS com `truststore` e HTTP/2 | Usa a confiança do sistema operacional |
| Timeout | 20 segundos | Limita uma tentativa individual |
| Concorrência | 4 conexões simultâneas | Não sobrecarrega as oito fontes |
| Redirecionamentos | Não seguidos | Evita sair do catálogo permitido |
| Páginas | Até 20 | `page` começa em 1 |
| Tamanho de página | 1000 | Enviado como `page-size=1000` |
| Período | `ALL` | Enviado em todas as requisições |
| Corpo máximo | 16 MiB | Acima disso, a tentativa falha por `response_size_limit` |
| Registros únicos | 10.000 | Ao atingir, a captura fica incompleta (`record_limit`) |
| Retries HTTP | 2 (3 tentativas) | Aplicados a transporte, 408, 429, 500, 502, 503, 504 e 529 |
| Espera | `Retry-After` ou backoff exponencial | Limitada a 15 segundos |
| Repetição de vazio | 10 e 30 segundos | Somente para fonte que já teve dados válidos; não ocupa a vaga de outra fonte durante a espera |
| User-Agent | `SantanderAdminMetrics/1.0` | Identificação da coleta |

A deduplicação usa o valor exato de `endpoint` como identidade dentro da captura. Se a mesma identidade aparecer em páginas diferentes, o primeiro registro é mantido. Quando os demais campos, exceto `requestTime`, divergem, a captura recebe `duplicate_endpoint` e `conflicting_endpoint`, e o registro é marcado como ambíguo. A captura não é considerada completa nesse caso.

A completude não depende apenas de HTTP 200. O código exige `data` como lista, `meta` como objeto, totais inteiros não negativos e conciliação entre identidades únicas e `totalRecords`. Uma página vazia depois de uma página com dados gera `pagination_no_new_identity`; um `totalRecords` atingido antes de `totalPages` gera `page_metadata_conflict`; um total que nunca é alcançado gera `total_mismatch` ou `missing_total`.

### Análise em detalhe

| Etapa | O que faz | Principal saída |
|---|---|---|
| Normalização | Lê `invocations`, `errors`, `rejections`, `averageResponse`, `averageTps` e `peakTps` do `currentDay` | Campos `calls`, `errors`, `rejections`, `mean_ms`, `average_tps`, `peak_tps` |
| Contrato de histórico | Aceita até 7 posições em `previousDays` e exige inteiros não negativos | `previous` por métrica e flags de histórico |
| Disponibilidade | Converte `uptimeRate` e `generalUptimeRate` para razão finita em [0,1] | `uptime`, `general_uptime` e flags |
| Dia analítico | Usa o `HTTP Date` da página em `America/Sao_Paulo`; fallback para `observed_at` | `day` e `day_basis` |
| Relógio declarado | Compara `observed_at` com `requestTime` | `clock_offset_seconds` e `reported_clock_skew` |
| Identidade | `SHA-256([reporter_id, endpoint])[:24]` | `entity_id` estável por fonte e endpoint |
| Fingerprint | Hash de seis métricas, uptime, downtime e histórico | Detecta repetição sem mudança de conteúdo |
| Intervalo | Compara a observação anterior da mesma entidade | Estados e deltas de chamadas, erros e rejeições |
| Sinais | Aplica limiares configuráveis | Lista de regras, severidade e evidência |
| Incidentes | Abre, confirma, recupera ou resolve por regra e entidade | Estado persistido em `incidents[]` |

> Exemplo prático: suponha que a página 1 retorne o endpoint `A` com 100 erros e `meta.totalRecords=2`, e a página 2 retorne o mesmo endpoint `A` com 101 erros. O primeiro registro é mantido, mas a captura recebe `duplicate_endpoint`, `conflicting_endpoint` e `pagination_no_new_identity`. O relatório fica incompleto, ambos os corpos brutos permanecem no bronze e a fonte pode abrir um incidente de coleta.

> Exemplo prático: uma resposta `HTTP 200` com `data=[]` e `totalRecords=0` tem cobertura reconciliada, mas não é utilizável. O estado registra `empty_response`, `complete=false` e `data_status=empty`; se a fonte tinha um panorama anterior, ele permanece identificado como anterior.

> Atenção: um build que falha antes da gravação do estado preserva `state.json` e o `index.html` já publicado. O próximo ciclo não herda um estado parcial; a falha é registrada no job e o candidato correspondente é descartado quando aplicável.

## Regras de negócio e critérios analíticos

As regras são parâmetros versionados em `config/rules.json` e validadas antes de qualquer coleta. O conjunto de chaves é fechado: uma chave ausente, desconhecida ou fora dos limites faz a execução falhar antes de chamar a origem. Os valores padrão também são verificados por teste contra o cron do workflow.

### Limiares e condições

| Regra | Condição de detecção | Severidade | Cuidado de leitura |
|---|---|---|---|
| Taxa de erro | `errors ÷ calls ≥ 5%` e `calls ≥ 100` | Atenção | O denominador é o total de chamadas declarado no dia |
| Taxa de erro crítica | `errors ÷ calls ≥ 20%` e `calls ≥ 1.000` | Crítico | Uma taxa alta com menos de 1.000 chamadas não vira crítica |
| Taxa de rejeição | `rejections ÷ calls ≥ 5%` e `calls ≥ 100` | Atenção | Não existe nível crítico nem causa inferida |
| Média de resposta | `mean_ms ≥ 2.000` e `calls ≥ 100` | Atenção | Média declarada, não p95 |
| Média crítica | `mean_ms ≥ 4.000` e `calls ≥ 100` | Crítico | A amostra mínima é a mesma da atenção |
| Regressão | `mean_ms ≥ 2 × mediana` de pelo menos 3 médias diárias anteriores positivas | Atenção | A mediana usa `previousDays`; não é média das médias |
| Recorrência contextual | Pelo menos 3 dias anteriores com `calls ≥ 100` e erro ≥ 5% | Sinal de contexto | O detalhe visual mostra somente D−1 a D−3 |
| Falha de coleta | Resposta não 200, incompleta ou sem registros | Atenção na primeira, crítico na segunda consecutiva | A falha é da nossa tentativa, não prova indisponibilidade dos serviços |
| Confirmação | Duas detecções consecutivas da mesma regra e entidade | `confirmed=true` | Confirma persistência do sinal, não novos erros no intervalo |
| Recuperação | Duas amostras avaliáveis consecutivas sem o sinal | `resolved` | Ausência, baixa amostra ou métrica inválida não resolvem |

### Fórmulas e denominadores

| Cálculo | Fórmula implementada | Quando fica nulo |
|---|---|---|
| Taxa de erro | `100 × errors ÷ calls` | `calls ≤ 0`, numerador nulo, numerador maior que chamadas ou valor inválido |
| Taxa de rejeição | `100 × rejections ÷ calls` | Mesmos critérios, com denominador válido próprio |
| Média ponderada | `Σ(mean_ms × calls) ÷ Σ(calls)` | Nenhuma linha com `mean_ms > 0` e `calls > 0` |
| Baseline de latência | Mediana das médias diárias anteriores positivas | Menos de `baseline_minimum_days` (3) médias positivas |
| Regressão | `mean_ms ÷ baseline_mean_ms` | Baseline ausente ou média atual inválida |
| Recorrência | Contagem de dias anteriores que passam em `calls` e taxa de erro | Histórico ausente ou sem posições suficientes |
| Delta de contador | `current − previous` para chamadas, erros e rejeições | Reset, dia diferente, origem incompleta, fingerprint igual ou delta impossível |

O cálculo de taxa agregada não soma percentuais: ele soma numeradores e denominadores **válidos correspondentes**. Uma linha com `errors > calls` fica fora do denominador daquela taxa; uma linha com `mean_ms = 0` e chamadas positivas não entra na média ponderada.

### Exemplos numéricos

> Exemplo prático: um endpoint declara 120 chamadas e 4 erros. A taxa é `100 × 4 ÷ 120 = 3,33%`. Como 3,33% é menor que 5%, não há sinal de erro, embora o valor apareça na tabela e no detalhe. O limite mínimo de 100 chamadas foi atendido.

> Exemplo prático: um endpoint declara 100 chamadas e 6 erros. A taxa é `6%`, então o sinal é de **atenção**. Para ser **crítico**, seriam necessárias pelo menos 1.000 chamadas e taxa ≥ 20%.

> Exemplo prático: um endpoint declara 999 chamadas e 250 erros. A taxa é `25,03%`, mas o sinal permanece de **atenção** porque o piso de criticidade é 1.000 chamadas. O mesmo endpoint com 1.000 chamadas e 250 erros seria crítico.

> Exemplo prático: duas linhas válidas compõem a média ponderada. A primeira tem 1.000 chamadas e média 100 ms; a segunda tem 4.000 chamadas e média 400 ms. A média ponderada é `(1.000 × 100 + 4.000 × 400) ÷ 5.000 = 340 ms`. A média simples de 250 ms estaria errada para o volume.

> Exemplo prático: a mediana das médias anteriores positivas é 300 ms. A média atual é 650 ms. Como `650 ≥ 2 × 300`, há regressão de latência. Se a média atual fosse 590 ms, não haveria regressão, mesmo com aumento de 96,7%.

### Ciclo de vida dos incidentes

| Estado | Condição implementada | Leitura no dashboard |
|---|---|---|
| Aberto, provisório | Primeira detecção da regra para a entidade | “sinal provisório”; ainda não confirmado |
| Aberto, confirmado | `consecutive_samples ≥ 2` | “persistência confirmada” |
| Em recuperação | Uma amostra avaliável sem o sinal após detecção | Ainda não resolvido; `recovery_samples` mostra o avanço |
| Resolvido | Duas amostras avaliáveis consecutivas sem o sinal | “resolvido” e horário da resolução |
| Reaberto | Nova detecção após resolução | Cria novo `id` porque inclui o run de abertura |

Uma amostra é avaliável para uma regra quando a origem está completa, há pelo menos `minimum_calls` chamadas e o estado de intervalo não bloqueia a métrica. Para latência, a média precisa ser positiva; para erro e rejeição, cada numerador tem seu próprio estado de intervalo. Uma amostra desconhecida, ausente ou inválida **zera** a sequência de recuperação; ela não conta como recuperação.

> Regra de negócio: o incidente descreve a persistência de um sinal acima do limiar, não a existência de novos erros entre duas coletas. Como os contadores são cumulativos, uma sequência de duas detecções pode ocorrer sem mudança nos erros.

> Atenção: reset ou revisão de um contador suspende as regras daquele contador, mas não invalida uma latência válida. Erro e rejeição têm estados de intervalo independentes; um reset de rejeições não esconde uma taxa de erro válida.

> Limitação: o monitor não identifica o status HTTP de cada erro, não distingue 429 de outras rejeições e não observa os serviços de clientes. Os sinais são critérios analíticos, não laudo de conformidade nem diagnóstico causal.

## Modelo de dados e dicionário

O modelo separa **estado de captura** (ciclos, relatórios, tentativas, bronze e incidentes) das **projeções analíticas** (linhas atuais, observações e marts). O grão é declarado em cada objeto; agregações usam linhagem tracejada, não chaves estrangeiras inventadas.

### Captura e estado

```schema
{
  "title": "Estado de captura · ciclo, relatório, tentativa e observação",
  "colGap": 118,
  "rowGap": 58,
  "entities": [
    {
      "id": "run",
      "name": "run",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 ciclo de execução",
      "col": 0,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "name": "observed_at", "type": "string" },
        { "name": "model_version", "type": "int" },
        { "name": "collection_health", "type": "json" },
        { "name": "rules", "type": "json" },
        { "name": "execution_url", "type": "string", "nullable": true }
      ]
    },
    {
      "id": "report",
      "name": "report",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 fonte em 1 ciclo",
      "col": 1,
      "row": 0,
      "columns": [
        { "key": "PK,FK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "id", "type": "string" },
        { "name": "status", "type": "int" },
        { "name": "complete", "type": "bool" },
        { "name": "records", "type": "int" },
        { "name": "coverage", "type": "string" },
        { "name": "issues", "type": "array" },
        { "name": "observed_at", "type": "string" }
      ]
    },
    {
      "id": "probe",
      "name": "probe",
      "kind": "table",
      "grain": "Grão: 1 linha = 1 tentativa HTTP",
      "col": 2,
      "row": 0,
      "columns": [
        { "key": "FK", "name": "run_id", "type": "string" },
        { "key": "FK", "name": "report_id", "type": "string" },
        { "name": "page", "type": "int" },
        { "name": "attempt", "type": "int" },
        { "name": "capture_attempt", "type": "int" },
        { "name": "status", "type": "int" },
        { "name": "duration_ms", "type": "double" },
        { "name": "bytes", "type": "int" },
        { "name": "source_sha", "type": "string" }
      ]
    },
    {
      "id": "bronze",
      "name": "bronze",
      "kind": "external",
      "grain": "Grão: 1 objeto = 1 corpo HTTP integral",
      "col": 0,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "source_sha", "type": "string" },
        { "name": "bytes", "type": "int" },
        { "name": "arquivo", "type": "string" }
      ]
    },
    {
      "id": "observation",
      "name": "observation",
      "kind": "table",
      "grain": "Grão: 1 linha = 1 endpoint × fonte × ciclo",
      "col": 1,
      "row": 1,
      "columns": [
        { "key": "PK,FK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "key": "FK", "name": "reporter_id", "type": "string" },
        { "name": "endpoint", "type": "string" },
        { "name": "day", "type": "string" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64" },
        { "name": "errors", "type": "int64" },
        { "name": "mean_ms", "type": "int64" }
      ]
    },
    {
      "id": "incident",
      "name": "incident",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 entidade × regra aberta",
      "col": 2,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "id", "type": "string" },
        { "key": "FK", "name": "entity_id", "type": "string" },
        { "name": "rule", "type": "string" },
        { "name": "status", "type": "string" },
        { "name": "severity", "type": "string" },
        { "name": "consecutive_samples", "type": "int" },
        { "name": "recovery_samples", "type": "int" },
        { "key": "FK", "name": "opened_run", "type": "string" }
      ]
    }
  ],
  "relations": [
    { "from": "run", "to": "report", "fromCard": "1", "toCard": "1..N", "label": "contém" },
    { "from": "report", "to": "probe", "fromCard": "1", "toCard": "1..N", "label": "tentativas" },
    { "from": "report", "to": "observation", "kind": "lineage", "label": "normaliza linhas" },
    { "from": "bronze", "to": "observation", "kind": "lineage", "label": "source_sha" }
  ],
  "note": "O estado lógico usa JSON; as entidades acima descrevem o contrato, não tabelas relacionais. No JSON, report e probe são aninhados em runs[].reports[] e report_id é a chave lógica do relatório. Incidentes referenciam o run de abertura por opened_run. Source_sha é referência ao corpo bronze, e não uma chave estrangeira de banco."
}
```

### Projeções e marts

```schema
{
  "title": "Projeções publicadas · linhas atuais, histórico e marts",
  "colGap": 126,
  "rowGap": 62,
  "entities": [
    {
      "id": "current",
      "name": "current_rows",
      "kind": "table",
      "grain": "Grão: 1 linha = 1 endpoint no último contexto por fonte",
      "col": 0,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "key": "FK", "name": "reporter_id", "type": "string" },
        { "name": "run_id", "type": "string" },
        { "name": "fresh", "type": "bool" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64" },
        { "name": "errors", "type": "int64" },
        { "name": "mean_ms", "type": "int64" }
      ]
    },
    {
      "id": "report_summary",
      "name": "report_summary",
      "kind": "mart",
      "grain": "Grão: 1 linha = 1 reporte no ciclo atual",
      "col": 1,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "reporter_id", "type": "string" },
        { "name": "reporter", "type": "string" },
        { "name": "endpoints", "type": "int" },
        { "name": "calls", "type": "int" },
        { "name": "errors", "type": "int" },
        { "name": "error_pct", "type": "double" },
        { "name": "mean_ms", "type": "double" }
      ]
    },
    {
      "id": "family_summary",
      "name": "family_summary",
      "kind": "mart",
      "grain": "Grão: 1 linha = 1 família no ciclo atual",
      "col": 2,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "family", "type": "string" },
        { "name": "endpoints", "type": "int" },
        { "name": "calls", "type": "int" },
        { "name": "errors", "type": "int" },
        { "name": "error_pct", "type": "double" }
      ]
    },
    {
      "id": "observations",
      "name": "observations",
      "kind": "table",
      "grain": "Grão: 1 linha = 1 endpoint × fonte × ciclo",
      "col": 0,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "name": "observed_at", "type": "string" },
        { "name": "day", "type": "string" },
        { "name": "calls", "type": "int64" },
        { "name": "errors", "type": "int64" },
        { "name": "source_complete", "type": "bool" }
      ]
    },
    {
      "id": "trends",
      "name": "observation_trends",
      "kind": "mart",
      "grain": "Grão: 1 linha = 1 reporte × ciclo",
      "col": 1,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "reporter_id", "type": "string" },
        { "name": "observed_at", "type": "string" },
        { "name": "calls", "type": "int" },
        { "name": "errors", "type": "int" },
        { "name": "error_pct", "type": "double" },
        { "name": "mean_ms", "type": "double" }
      ]
    },
    {
      "id": "payload",
      "name": "dashboard_payload",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 publicação",
      "col": 2,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "meta.run_id", "type": "string" },
        { "name": "latest", "type": "array" },
        { "name": "runs", "type": "array" },
        { "name": "panoramas", "type": "json" },
        { "name": "collection_health", "type": "json" },
        { "name": "points", "type": "array" }
      ]
    }
  ],
  "relations": [
    { "from": "observations", "to": "current", "kind": "lineage", "label": "último contexto por fonte" },
    { "from": "current", "to": "report_summary", "kind": "lineage", "label": "agrega por reporte" },
    { "from": "current", "to": "family_summary", "kind": "lineage", "label": "agrega por família" },
    { "from": "observations", "to": "trends", "kind": "lineage", "label": "agrega por reporte e ciclo" },
    { "from": "trends", "to": "payload", "kind": "lineage", "label": "série visível" }
  ],
  "note": "Os marts são recriados a cada build. O dashboard_payload é montado a partir de latest, runs, panoramas, saúde e marts. current_rows contém o último contexto por fonte, que pode estar antigo; fresh indica se ele pertence ao ciclo mais recente. Não some snapshots cumulativos entre ciclos."
}
```

### Identidade, grão e cardinalidade

| Objeto | Chave / identidade | Grão | Observação |
|---|---|---|---|
| Ciclo | `run_id` | 1 execução lógica | Formado por timestamp UTC e sufixo aleatório; não é a data de referência do banco |
| Relatório | `(run_id, reporter id)` | 1 fonte em 1 ciclo | Guarda status, cobertura, issues e tentativas |
| Tentativa | `(run_id, report, page, attempt)` | 1 requisição HTTP | Tentativas transitórias permanecem no histórico |
| Observação | `(run_id, entity_id)` | 1 endpoint × fonte × ciclo | Identidade única dentro do ciclo |
| Linha atual | `entity_id` | 1 endpoint no último contexto por fonte | Pode ser de ciclo antigo; `fresh` distingue |
| Incidente | `id` | 1 entidade × regra aberta | Reabertura após resolução cria novo `id` |
| Bronze | `source_sha` | 1 corpo HTTP integral | Conteúdo endereçado por SHA-256 |
| Release | `tag state-*` | 1 pacote de estado aprovado | Até dois pacotes aprovados |

O `entity_id` é `SHA-256` de `[reporter_id, endpoint]`, truncado em 24 caracteres. O mesmo caminho em reportes diferentes gera identidades diferentes. O `endpoint` é comparado como string exata; variações de caixa, barras ou parâmetros podem gerar identidades distintas. O CNPJ **não** é chave: Nissan e Renault compartilham CNPJ, mas têm `reporter_id` próprios.

### Semântica temporal

| Campo | Origem | Significado | Cuidado |
|---|---|---|---|
| `observed_at` | Relógio da coleta | Início da observação da fonte ou da tentativa | É UTC; não é a data do relatório |
| `http_date` | Cabeçalho `Date` | Horário declarado pelo servidor na página | Pode estar ausente ou divergir do `requestTime` |
| `day` | `http_date` em `America/Sao_Paulo` | Dia analítico da linha | Fallback para `observed_at` quando o `Date` não é interpretável |
| `day_basis` | Código | Explica qual relógio fundamentou o dia | Não altera o `requestTime` original |
| `request_time` | `requestTime` do registro | Horário declarado pelo banco no payload | Preservado sem correção automática |
| `clock_offset_seconds` | `observed_at − requestTime` | Diferença observada | `reported_clock_skew` acima de 900 s |
| `interval_from` / `interval_to` | Observações comparadas | Instantes da comparação | Não são a janela oficial de agregação da instituição |
| `history_window_start/end` | Build | Janela fixa de 72 horas do painel | Pode conter lacunas; não é preenchida retroativamente |

> Regra de negócio: se páginas de uma mesma captura cruzarem o dia analítico, a captura é marcada como incompleta (`mixed_reference_day`, `page_day_changed`) e não alimenta os KPIs. O projeto não força um único dia para “corrigir” a origem.

### Contrato Arrow de `current_rows` e `observations`

| Campo | Tipo Arrow | Papel | Semântica / nulos |
|---|---|---|---|
| `run_id` | `string` | `PK` | Identidade do ciclo UTC; não é a data de referência |
| `entity_id` | `string` | `PK` | SHA-256 de reporter + endpoint, truncado em 24 |
| `observed_at` | `string` | Tempo | Início da observação da fonte em UTC |
| `day` | `string` | Tempo | Dia analítico em `America/Sao_Paulo` |
| `reporter_id` | `string` | `FK` | Identidade estável do catálogo |
| `reporter` | `string` | Rótulo | Nome operacional; não prova controle societário |
| `endpoint` | `string` | Identidade | URI declarada; nunca chamada pelo monitor |
| `path` | `string` | Classificação | Caminho extraído da URI |
| `family` | `string` | Classificação | Primeiro segmento depois de `/open-banking/` |
| `calls` | `int64` | Métrica | `invocations.currentDay`; não negativo ou nulo |
| `errors` | `int64` | Métrica | `errors.currentDay`; sem status HTTP detalhado |
| `rejections` | `int64` | Métrica | `rejections.currentDay`; sem causa inferida |
| `mean_ms` | `int64` | Métrica | `averageResponse.currentDay`; média, não p95 |
| `error_pct` | `double` | Derivado | `100 × errors ÷ calls` com denominador válido |
| `rejection_pct` | `double` | Derivado | `100 × rejections ÷ calls` com denominador válido |
| `uptime` | `double` | Disponibilidade | Razão em [0,1]; interface multiplica por 100 |
| `source_complete` | `bool` | Contrato | Cobertura reconciliada da captura; não atesta todos os campos |
| `fresh` | `bool` | Contexto | Linha do ciclo mais recente; na projeção histórica pode ser nulo |

<details>
<summary>Campos adicionais da observação no estado e no JSON</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `day_basis` | string | Explica qual relógio fundamentou `day` |
| `source_sha` | SHA-256 | Corpo bronze de origem; os bytes podem expirar |
| `json_path` | string | Posição `$.data[n]` no corpo identificado |
| `request_time` | string/nulo | `requestTime` original, sem correção de fuso |
| `clock_offset_seconds` | número/nulo | `observed_at − requestTime` |
| `average_tps` / `peak_tps` | int64/nulo | TPS médio e pico declarados; não calculados |
| `general_uptime` | razão/nulo | `generalUptimeRate` declarado |
| `downtime_seconds` / `general_downtime` / `scheduled_outage` | int64/nulo | Segundos declarados nos campos de downtime |
| `previous` | objeto de arrays | Até 7 posições por métrica; D−1 primeiro |
| `baseline_mean_ms` | número/nulo | Mediana das médias diárias anteriores positivas |
| `recurrent_days` | inteiro | Dias anteriores com chamadas e erro acima dos limiares |
| `quality` | array de strings | Ocorrências de contrato/consistência; não reescreve o valor |
| `fingerprint` | SHA-256 | Seis métricas atuais, uptime, downtime e histórico |
| `interval_from` / `interval_to` | UTC/nulo | Instantes das duas observações comparadas |
| `interval_seconds` | número/nulo | Diferença entre os instantes; tempo não crescente invalida |
| `interval_calls` / `interval_errors` / `interval_rejections` | int64/nulo | Diferenças aceitas dos cumulativos |
| `interval_error_pct` / `interval_rejection_pct` | percentual/nulo | Taxas dos deltas aceitos |
| `interval_state` | enum | Motivo da comparação aceita ou suspensa |
| `interval_error_state` / `interval_rejection_state` | enum | Comparabilidade de cada numerador com chamadas |

</details>

<details>
<summary>Tentativas HTTP: runs[].reports[].probes[]</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `capture_attempt` / `data_status` | inteiro / enum | Captura a partir de 1 e resultado da resposta |
| `page` / `attempt` | inteiro | Página solicitada e tentativa HTTP a partir de 1 |
| `observed_at` | UTC | Início da tentativa, distinto do início do ciclo |
| `url` | URL | Admin e parâmetros solicitados; redirecionamentos não são seguidos |
| `status` | inteiro | HTTP recebido; 0 quando não houve resposta HTTP |
| `duration_ms` | número | Tempo da tentativa até leitura do corpo ou erro |
| `http_date` | string/nulo | Cabeçalho `Date` recebido, preservado |
| `source_sha` / `bytes` | hash/inteiro | Corpo completo preservado e seu tamanho |
| `error` | string/nulo | Condição final da tentativa; tentativas transitórias permanecem |

</details>

<details>
<summary>Ocorrências: incidents[]</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `id` | hash truncado | Entidade + regra + run de abertura |
| `entity_id` / `rule` | strings | Entidade do serviço ou `source:<reporter_id>`, mais a regra |
| `reporter_id` / `reporter` / `endpoint` | string/nulo | Identidade estável, rótulo atual e endpoint |
| `opened_at` / `opened_run` | UTC / ID | Primeira detecção observada |
| `last_seen` | UTC | Última detecção acima do limiar |
| `evaluated_at` | UTC | Última avaliação conclusiva |
| `samples` | inteiro | Total de detecções da ocorrência |
| `consecutive_samples` | inteiro | Sequência atual de detecções |
| `confirmed` | booleano | Sequência atingiu `confirmation_samples` |
| `recovery_samples` | inteiro | Amostras avaliáveis consecutivas abaixo do limiar |
| `status` / `severity` | enum | `open` / `recovering` / `resolved` e `attention` / `critical` |
| `evidence` | string | Numerador, denominador ou contexto da última detecção |
| `resolved_at` | UTC opcional | Registrado após completar a recuperação |

</details>

<details>
<summary>Payload publicado: chaves de topo</summary>

| Chave | Conteúdo | Consumo |
|---|---|---|
| `meta` | Versão, run, datas, janelas, cron e contagens retidas | Cabeçalho e frescor |
| `rules` | Parâmetros aplicados no ciclo | Metodologia e limiares |
| `reporters` | Catálogo dos oito reportes | Filtros e rótulos |
| `latest` | Último contexto por endpoint | Tabela de endpoints e detalhe |
| `runs` | Ciclos visíveis na janela de 72h | Tendências e monitor de execuções |
| `incidents` | Incidentes abertos e resolvidos recentes | Seção de incidentes |
| `reported_history` | Até 3 dias anteriores declarados | Gráficos D−1 a D−3 |
| `panoramas` | Último ciclo completo por recorte | KPIs e ranking |
| `collection_health` | Saúde da última tentativa e por fonte | Aviso de frescor |
| `points` | Pontos próprios para detalhe | Série do endpoint |
| `report_summary` | Agregado por reporte | Cards e leitura executiva |
| `family_summary` | Agregado por família | Apoio analítico |
| `observation_trends` | Série por reporte e ciclo | Tendências |

</details>

> Limitação: `source_complete` indica que a captura reconciliou a cobertura esperada; não garante que todos os campos estejam corretos. `quality` registra suspeitas sem reescrever os valores. O dicionário descreve o contrato implementado, não uma garantia de qualidade da origem.

## Consulta e consumo dos dados

O projeto entrega três formas de consumo: o dashboard para leitura, o JSON para integrações simples e os arquivos Parquet/DuckDB para análise. Todas derivam do mesmo estado lógico; a diferença é o recorte e a forma de acesso.

### Artefatos entregues

| Caminho | Grão / conteúdo | Uso recomendado | Observação |
|---|---|---|---|
| `site/index.html` | Dashboard completo | Leitura operacional no navegador | Requer toda a pasta `site/` |
| `site/dashboard.json` | Payload da publicação | Integrações e inspeção | Inclui `meta`, `latest`, `runs`, `incidents`, `panoramas` e marts |
| `site/data.js` | `window.ADMIN_DATA` | Carregamento do dashboard | Não é formato de integração; prefira o JSON |
| `site/documentacao.html` | Manual runtime autocontido | Distribuição offline | Gerado a partir dos dados e do código |
| `site/docs_v2/documentacao-v2.html` | Esta documentação | Leitura funcional e técnica | Build independente da skill `project-html-docs` |
| `data/gold/current_rows.parquet` | 1 linha por endpoint no último contexto | Consulta do retrato atual | Filtrar `fresh AND source_complete` para o ciclo atual |
| `data/gold/observations.parquet` | 1 linha por endpoint × ciclo | Série e auditoria | Não somar cumulativos entre ciclos |
| `data/gold/report_summary.parquet` | 1 linha por reporte | Comparação entre fontes | Mesmo grão do card por reporte |
| `data/gold/family_summary.parquet` | 1 linha por família | Visão por domínio | Famílias vêm do caminho do endpoint |
| `data/gold/observation_trends.parquet` | 1 linha por reporte × ciclo | Tendência agregada | Somente ciclos visíveis na janela |
| `data/gold/warehouse.duckdb` | Tabelas e views do build | Consulta local ad hoc | Recriado a cada build |
| Release `state.zip` | Estado + bronzes + manifesto | Recuperação operacional | Até dois pacotes aprovados |

### Preparar o ambiente local

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m admin_metrics.cli build
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory site
```

Abra `http://127.0.0.1:8766/`. Use `collect` no lugar de `build` para criar uma nova amostra; `build` republica o estado existente sem criar observação. Os caminhos padrão são `--root data`, `--output site` e `--config config`.

### Receitas DuckDB

As receitas abaixo consideram o diretório do projeto como diretório atual. Ajuste os caminhos se o checkout estiver em outro local.

**1. Abrir o warehouse e conferir os objetos disponíveis**

```sql
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'main'
ORDER BY table_name;
```

**2. Retrato atual por endpoint, sem misturar contexto antigo**

```sql
SELECT reporter_id, reporter, family, path, calls, errors, error_pct, mean_ms, quality
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND source_complete
ORDER BY errors DESC NULLS LAST
LIMIT 50;
```

**3. Reconciliar a taxa por reporte com a mesma regra dos marts**

```sql
SELECT reporter_id,
       count(*) AS endpoints,
       sum(calls) AS calls,
       100.0 * sum(errors) FILTER (WHERE errors <= calls AND calls > 0)
         / nullif(sum(calls) FILTER (WHERE errors <= calls AND calls > 0), 0) AS error_pct,
       sum(mean_ms::DOUBLE * calls) FILTER (WHERE mean_ms > 0 AND calls > 0)
         / nullif(sum(calls) FILTER (WHERE mean_ms > 0 AND calls > 0), 0) AS mean_ms
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND source_complete
GROUP BY reporter_id
ORDER BY error_pct DESC NULLS LAST;
```

**4. Visão por família**

```sql
SELECT family,
       count(*) AS endpoints,
       sum(calls) AS calls,
       sum(errors) AS errors,
       100.0 * sum(errors) FILTER (WHERE errors <= calls AND calls > 0)
         / nullif(sum(calls) FILTER (WHERE errors <= calls AND calls > 0), 0) AS error_pct
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND source_complete
GROUP BY family
ORDER BY calls DESC;
```

**5. Série de um reporte na janela publicada**

```sql
SELECT run_id, observed_at, reporter_id, calls, errors, error_pct, mean_ms
FROM read_parquet('data/gold/observation_trends.parquet')
WHERE reporter_id = 'openbanking'
ORDER BY observed_at;
```

**6. Listar ocorrências de qualidade por endpoint**

```sql
SELECT reporter_id, path, quality
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND len(quality) > 0
ORDER BY reporter_id, path;
```

**7. Analisar intervalos aceitos e suspensos**

```sql
SELECT reporter_id, path, interval_state,
       interval_error_state, interval_rejection_state,
       interval_calls, interval_errors, interval_error_pct
FROM read_parquet('data/gold/observations.parquet')
WHERE interval_state <> 'first_observation'
ORDER BY observed_at DESC, interval_state;
```

**8. Consultar o estado bruto em Python**

```python
import json
from pathlib import Path

state = json.loads(Path("data/state.json").read_text(encoding="utf-8"))
open_incidents = [i for i in state["incidents"] if i["status"] != "resolved"]
latest_run = state["runs"][-1]
print(latest_run["run_id"], len(open_incidents), len(state["observations"]))
```

> Atenção: em `current_rows`, `fresh=false` identifica o último contexto de uma fonte que não renovou o ciclo. Essas linhas são úteis para diagnóstico, mas não entram nos KPIs atuais nem nos marts `report_summary` e `family_summary`. Sempre filtre `fresh AND source_complete` ao reproduzir os cards.

> Exemplo prático: no snapshot local, `current_rows` tem 276 linhas, todas com `fresh=true` e `source_complete=true`; `report_summary` tem 8 linhas e `family_summary` tem 26. Se uma fonte falhar no próximo ciclo, `latest` ainda terá suas linhas antigas com `fresh=false`, e os marts do ciclo atual ficarão sem essa fonte.

### Cuidados de consulta

| Armadilha | Por que acontece | Como evitar |
|---|---|---|
| Somar chamadas de vários `run_id` | Os contadores são cumulativos do dia | Escolha um ciclo ou use deltas validados |
| Somar reportes como transações únicas | Serviços podem ser compartilhados | Trate o agregado como soma de declarações, não deduplicação de clientes |
| Usar `mean_ms` como p95 | A origem só declara média | Não derive percentis |
| Tratar `error_pct` nulo como zero | Denominador inválido ou numerador impossível | Mantenha nulo e exclua do denominador correspondente |
| Comparar `day` com `request_time` | O dia usa `HTTP Date`, não o `requestTime` | Leia `day_basis` e preserve o horário original |
| Considerar incidente resolvido como falha atual | O estado preserva resolvidos por 30 dias | Filtre `status != 'resolved'` para leitura corrente |
| Contar bronzes como observações | O bronze é conteúdo HTTP endereçado por hash | Use `observations` para o grão analítico |
| Usar a janela de 72h como histórico completo | O painel publica 3 dias; o estado guarda 30 | Consulte o estado/Parquet para o histórico durável |

## Operação, agenda e recuperação

A operação normal é conduzida pelo GitHub Actions. O checkout local serve para desenvolvimento, inspeção e recuperação assistida. O projeto não tem API de administração, painel de escrita ou autenticação corporativa; o controle é o workflow, o catálogo e o estado em Release.

### Pré-requisitos

| Requisito | Versão / observação |
|---|---|
| Python | 3.11 ou 3.12, 64 bits |
| Node.js | 22 ou superior para as verificações do dashboard |
| Dependências Python | `requirements-dev.lock` para desenvolvimento; `requirements.lock` para runtime |
| GitHub CLI | `gh` autenticado para restaurar, criar ou promover Releases |
| Acesso ao repositório | `GH_REPO=alebitencourtx/admin-metrics` no ambiente do workflow |

### Comandos locais

```powershell
# Instalar
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .

# Coletar uma nova amostra e publicar
.\.venv\Scripts\python.exe -m admin_metrics.cli collect

# Republicar o estado existente sem criar observação
.\.venv\Scripts\python.exe -m admin_metrics.cli build

# Servir o site local
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory site

# Verificações
.\.venv\Scripts\python.exe -m pytest -q
node --check src/admin_metrics/web/app.js
node --test tests/test_dashboard.cjs
```

### Parâmetros de configuração

| Parâmetro | Valor padrão | Efeito | Restrição validada |
|---|---:|---|---|
| `retention_days` | 30 | Retenção de ciclos, observações e incidentes resolvidos | Inteiro > 0; ≥ `dashboard_history_days` |
| `dashboard_history_days` | 3 | Janela publicada no painel | Inteiro > 0; ≤ retenção |
| `schedule_interval_hours` | 1 | Intervalo esperado do cron | 1, 2, 3, 4, 6, 8, 12 ou 24 |
| `schedule_minute` | 17 | Minuto do cron | 0–59 |
| `error_attention_pct` | 5 | Limiar de atenção de erro | 0–100; ≤ crítico |
| `error_critical_pct` | 20 | Limiar crítico de erro | 0–100 |
| `minimum_calls` | 100 | Amostra mínima para regras | Inteiro > 0; ≤ crítico |
| `critical_minimum_calls` | 1000 | Amostra mínima para erro crítico | Inteiro > 0 |
| `rejection_attention_pct` | 5 | Limiar de atenção de rejeição | 0–100 |
| `latency_attention_ms` | 2000 | Limiar de atenção de latência | Inteiro > 0; ≤ crítico |
| `latency_critical_ms` | 4000 | Limiar crítico de latência | Inteiro > 0 |
| `regression_multiplier` | 2 | Fator de regressão sobre a mediana | > 1 |
| `recovery_samples` | 2 | Amostras para resolver | Inteiro > 0 |
| `confirmation_samples` | 2 | Amostras para confirmar | Inteiro > 0 |
| `baseline_minimum_days` | 3 | Mínimo de médias anteriores para baseline | Inteiro > 0; ≤ histórico |
| `recurrent_minimum_days` | 3 | Mínimo de dias para recorrência | Inteiro > 0; ≤ histórico |
| `reported_history_days` | 7 | Máximo de posições em `previousDays` | ≤ 7 |
| `clock_skew_seconds` | 900 | Tolerância entre `requestTime` e coleta | Número ≥ 0 |
| `stale_after_hours` | 2 | Idade que aciona aviso de dados antigos | ≥ intervalo do cron |
| `chart_gap_hours` | 1.5 | Lacuna que interrompe a linha do gráfico | ≥ intervalo do cron |
| `empty_retry_delays_seconds` | `[10, 30]` | Repetições após resposta vazia | Até 2 inteiros entre 1 e 60 |

> Atenção: alterar `rules.json` exige manter exatamente o conjunto de chaves e respeitar as ordens de grandeza. O teste `test_versioned_configuration_matches_hourly_workflow` compara o cron gerado com o workflow; uma mudança de agenda precisa atualizar ambos.

### Agenda e gatilhos

| Gatilho | Comportamento |
|---|---|
| `push` na `main` | Republica o estado aprovado sem criar nova observação, salvo bootstrap sem estado |
| `schedule` `17 * * * *` UTC | Cria uma nova observação a cada hora, em melhor esforço |
| `workflow_dispatch` com `refresh_data=true` | Coleta uma nova observação |
| `workflow_dispatch` com `refresh_data=false` | Apenas republica o estado aprovado |
| `pull_request` | Executa o workflow de CI, não o de Pages |

O workflow `pages.yml` usa concorrência `admin-state-and-pages` com `cancel-in-progress: false`, instala dependências, roda `pytest`, verifica o JavaScript, prepara o estado, envia `site/` como artefato e faz o deploy. O job `confirm` promove o candidato somente se o job `deploy` terminou com sucesso; caso contrário, descarta o draft.

### Ciclo de Release

1. **Preparar** — restaura a Release aprovada mais recente, se existir; executa o pipeline; publica o site; cria um draft `state-<run>-<attempt>` com `state.zip`, `SHA256SUMS` e um corpo JSON de recibo.
2. **Publicar Pages** — o artefato `site/` é enviado ao GitHub Pages.
3. **Confirmar** — o job `confirm` verifica o recibo do deploy; se houver sucesso, promove o draft e mantém apenas os dois pacotes aprovados mais recentes.
4. **Descartar** — se o build ou o deploy falhar, o draft é excluído. Uma Release já aprovada não é apagada por falha de deploy.

O corpo do recibo contém `data_run_id`, `workflow_run_id`, `source_sha` e `purpose=approved-monitor-state`. A promoção exige um job `deploy` com `status=completed` e `conclusion=success`; links de execução de ciclos antigos só são preenchidos quando há recibo de Release que comprove a associação.

### Runbook de recuperação

| Sintoma | Causa provável | Ação |
|---|---|---|
| Build falhou antes de gravar o estado | Erro de código, DuckDB, template ou validação | Corrigir a causa, reexecutar; o estado e o site anterior permanecem |
| Deploy do Pages falhou | Indisponibilidade do Pages ou artefato inválido | O job `confirm` descarta o draft; reexecute após o serviço normalizar |
| Candidato ficou em draft após deploy aprovado | Falha no `confirm` ou no recibo | Verificar o ID do dashboard e o job; promover manualmente com `gh release edit` só após comprovar o deploy |
| Fonte respondeu HTTP 200 vazio | Relatório sem métricas naquele instante | A fonte pode ser recapturada após 10 e 30 s se já tinha dados válidos; o panorama anterior é preservado |
| Fonte retornou HTTP 4xx/5xx | Acesso, indisponibilidade ou bloqueio | Ver as tentativas preservadas; não inferir causa dos serviços de clientes |
| Estado restaurado em raiz não vazia | Proteção contra sobrescrita | Escolha um diretório vazio; o restore não altera o estado atual |
| Checkup externo/interno falhou | ZIP corrompido, checksum divergente ou entrada inválida | Não use o pacote; restaure outro backup aprovado |
| Lock abandonado | Processo anterior interrompido | Confirme que não há escritor ativo e remova `data/.writer.lock`; nunca remova com uma execução em andamento |
| Estado com versão incompatível | Pacote de outra geração | Use um pacote com `version=1` e modelo suportado (1–3) |
| Site sem a documentação v2 | Build antigo ou arquivo ausente | Confirme `docs_v2/documentacao-v2.html` e reexecute o build |
| Dados desatualizados no navegador | Última tentativa recente, panorama antigo | Verifique a saúde da coleta e o motivo da não renovação; não trate como zero |

Restauração explícita em diretório vazio, com `gh` autenticado:

```powershell
$env:GH_REPO = "alebitencourtx/admin-metrics"
python scripts/cloud_pipeline.py restore --tag state-<run>-<tentativa>
python -m admin_metrics.cli build
```

> Atenção: o restore não sobrescreve estado existente e não troca automaticamente o estado remoto atual. Nunca apague o pacote anterior antes de verificar a recuperação e o build local.

> Limitação: o agendamento do GitHub Actions é de melhor esforço. Uma execução pode atrasar ou não ocorrer; o aviso de dados desatualizados usa a idade real do último panorama, não a promessa do cron.

## Qualidade, continuidade e limites

O projeto prefere **diagnóstico explícito** a correção silenciosa. Uma resposta HTTP 200 pode ser publicada com um diagnóstico de fonte vazia; um build bem-sucedido pode publicar um panorama anterior identificado. Sucesso do workflow não é o mesmo que saúde dos dados.

### Matriz de condições e comportamento

| Condição | Comportamento implementado | Impacto no consumidor |
|---|---|---|
| HTTP 200 com `data=[]` e total 0 | `coverage=empty_response`, `complete=false`, `data_status=empty` | Fonte não renova o panorama; dados anteriores permanecem rotulados |
| HTTP 200 com corpo malformado | `data_not_array`, `meta_not_object` ou `invalid_totals`; captura incompleta | Fonte entra em falha de coleta; sem métricas novas |
| HTTP 4xx/5xx | `http_<status>` e captura incompleta | Diagnóstico de coleta; não é indisponibilidade dos serviços de clientes |
| Falha de transporte | `status=0`, `transport_error` | Pode haver retry; se persistir, saúde parcial ou indisponível |
| Paginação sem novas identidades | `pagination_no_new_identity`; cobertura não confirmada | Captura incompleta; evita loop infinito |
| Identidade duplicada com valores iguais | `duplicate_endpoint`; primeiro registro mantido | Captura incompleta, mas sem conflito de valores |
| Identidade duplicada com valores diferentes | `duplicate_endpoint` + `conflicting_endpoint`; registro ambíguo | Captura incompleta; não entra como ciclo completo |
| Total alcançado antes de `totalPages` | `page_metadata_conflict`, mas `complete=true` se o total reconciliar | Cobertura conciliada com alerta de metadados |
| Total nunca alcançado | `total_mismatch` ou `missing_total`; `unconfirmed` | Captura incompleta |
| Limite de 10.000 identidades | `record_limit`, `coverage=record_limit` | Captura incompleta; pode indicar crescimento anormal |
| Páginas cruzam o dia | `page_day_changed`, `mixed_reference_day`; `source_complete=false` | Linhas ficam fora dos KPIs do ciclo |
| `requestTime` ausente ou inválido | `request_time_invalid` | `clock_offset_seconds` nulo; valor original preservado |
| `requestTime` diverge mais de 900 s | `reported_clock_skew` | Sinal de relógio; não corrige o horário |
| Uptime booleano | `uptime_invalid` | Valor nulo; não é convertido em 1 nem 0 |
| Uptime 100% com downtime positivo | `uptime_downtime_conflict` | Valor original mantido; interpretação exige cautela |
| TPS médio maior que o pico | `average_tps_above_peak` | Inconsistência registrada; valores preservados |
| Erro ou rejeição maior que chamadas | `counter_above_invocations`; taxa nula | Linha fora do denominador daquela taxa |
| Média zero com chamadas positivas | `zero_mean_with_traffic` | Média não entra na média ponderada |
| Históricos de métricas com tamanhos diferentes | `history_lengths_differ` | Baseline e recorrência podem ficar indisponíveis |
| `previousDays` com valor inválido | `<métrica>_history_value_invalid`; posição nula | Histórico não é corrigido |
| Reset ou revisão de contador | `counter_reset_or_revision`; intervalo suspenso | Regras daquele contador não avaliam; latência válida continua |
| Fingerprint igual ao anterior | `unchanged_report`; intervalo suspenso | Não conta como tráfego novo |
| Reporte incompleto | `source_complete=false` | Fora dos KPIs e dos marts do ciclo |
| Fonte nunca completou | `latest_rows` mantém o contexto parcial mais recente | Diagnóstico disponível, mas sem promessa de completude |
| Release sem recibo de deploy | Promoção rejeitada | O draft não vira pacote aprovado |
| ZIP com caminho não permitido | Restore rejeitado antes de qualquer escrita | Nenhum arquivo é extraído |
| Estado com modelo desconhecido | `archive.validate` rejeita | Pacote incompatível não é promovido |

### Estados de cobertura e saúde

| Campo / valor | Significado |
|---|---|
| `coverage=reported_total_reconciled` | Total de identidades conciliado com `totalRecords` |
| `coverage=total_mismatch` | Total declarado não foi alcançado |
| `coverage=empty_response` | Resposta reconciliada sem métricas |
| `coverage=record_limit` | Limite de identidades atingido |
| `coverage=unconfirmed` | Paginação encerrou sem confirmação |
| `coverage=invalid_records` | Havia registros inválidos na captura |
| `coverage=mixed_reference_day` | Páginas cruzaram o dia de referência |
| `coverage=unknown` | Cobertura não determinada |
| `data_status=valid` | HTTP 200, captura completa e ao menos um registro |
| `data_status=empty` | HTTP 200 sem métricas utilizáveis |
| `data_status=http_error` | HTTP diferente de 200 |
| `data_status=transport_error` | Sem resposta HTTP |
| `data_status=invalid_report` | Corpo recebido, mas contrato/cobertura inválidos |
| `collection_health=healthy` | Todas as fontes com dados válidos |
| `collection_health=partial` | Ao menos uma fonte válida e ao menos uma não válida |
| `collection_health=unavailable` | Nenhuma fonte com dados válidos |

### Continuidade do panorama

O panorama é escolhido percorrendo os ciclos do mais recente para o mais antigo. Para o escopo “todos”, todas as oito fontes precisam estar válidas, com a contagem normalizada exata e um único dia de referência. Para um escopo de fonte, basta aquela fonte. O primeiro ciclo que satisfizer o critério vira o panorama daquele recorte; não há mistura de fontes ou dias.

A saúde (`collection_health`) sempre descreve a **última tentativa**, mesmo que o panorama venha de um ciclo anterior. Os campos `last_attempt_at` e `last_valid_at` são separados de propósito. O navegador calcula a idade do último dado válido, não a idade da última tentativa.

> Regra de negócio: uma tentativa vazia recente não renova a idade do panorama. O aviso “Dados válidos desatualizados” usa o instante do último ciclo completo, por isso pode aparecer mesmo com uma execução recente.

### Retenção e expiração

| Camada | Retenção | Consequência |
|---|---|---|
| Painel publicado | 72 horas de ciclos e pontos | Lacunas ficam vazias; não há preenchimento retroativo |
| Estado lógico | 30 dias de ciclos, observações e `latest_rows` | Ciclos antigos são removidos inteiros, não linha a linha |
| Incidentes | Abertos persistem; resolvidos por 30 dias | Histórico de resolução limitado à janela |
| Bronze local | Dois ciclos recentes referenciados | Hashes antigos permanecem no estado, mas os bytes podem expirar |
| Release | Dois pacotes aprovados | A união do atual com o anterior pode conter bronzes de três ciclos |
| Warehouse/Parquet | Recriados a cada build | O warehouse local não é fonte de verdade nem é publicado |
| GitHub Pages | Conteúdo do último deploy | O site é uma projeção; não é backup do estado |

### Limitações conhecidas

- **Média não é p95.** A origem declara `averageResponse`; o projeto não inventa distribuição.
- **Erro não tem status HTTP.** O campo `errors` é um contador; não é possível separar 400, 401, 429 ou 500 por endpoint.
- **Rejeição não prova causa.** O projeto não afirma bloqueio, fraude, limite de taxa ou falha de negócio.
- **Serviços podem ser compartilhados.** O agregado soma declarações de reportes; não garante transações únicas entre instituições.
- **Um único escritor.** Não há coordenação distribuída; o lock local e o workflow com concorrência são a proteção.
- **Agenda de melhor esforço.** O GitHub pode atrasar ou desabilitar schedules de repositórios públicos inativos.
- **Dados publicados são reais, mas não contínuos.** A série começa na primeira execução; não há preenchimento de horários não coletados.
- **O snapshot local não é produção.** Números de exemplo têm data e run; não devem ser citados como estado atual.
- **Sem autenticação corporativa.** O site é público e não tem controle de acesso por usuário.
- **Sem transação distribuída.** Pages, Releases e estado local não formam uma transação única; uma falha de confirmação pode deixar um draft para inspeção.

> Limitação: o projeto documenta o comportamento implementado. Ele não certifica que a origem cumpriu o contrato Admin, não mede disponibilidade real dos serviços de clientes e não substitui os relatórios oficiais do regulador.

## Decisões de implementação e configuração

As decisões abaixo descrevem o que está implementado e as consequências observáveis. Elas não são um histórico de arquitetura nem uma proposta de modernização; são a leitura do código desta revisão.

| Decisão | Implementação | Consequência |
|---|---|---|
| Estado como JSON versionado | `state.json` versão 1, com listas de runs, observations, incidents e latest_rows | Simples de inspecionar, restaurar e transportar; requer escrita atômica e lock |
| Escritor único | `data/.writer.lock` com `O_EXCL` | Evita dois processos alterando o mesmo estado; lock abandonado exige intervenção |
| Warehouse embutido | DuckDB recriado a cada build, com `memory_limit=1GB` e `threads=2` | Sem servidor de banco; o build é determinístico a partir do estado |
| Parquet como entrega analítica | Cinco arquivos Arrow/Parquet com compressão Zstandard | Consumo portátil; não é necessário subir banco para consultar |
| Site estático | HTML, JS e dados no próprio `site/`, sem CDN | Leitura offline e CSP restritiva; toda a pasta é necessária no dashboard |
| Assets endereçados por hash | `site/assets/<sha20>/` e poda de versões antigas | Cache seguro e rollback de assets; o índice aponta para a versão atual |
| Release como estado durável | `state.zip` + manifesto + checksums, até dois aprovados | Recuperação independente do histórico Git; bytes de bronze podem expirar |
| Catálogo allowlist | Host exato, caminho exato e HTTPS; CNPJ de 14 dígitos | Impede chamadas a URLs arbitrárias; mudanças de catálogo exigem edição explícita |
| Evidência de catálogo | `catalog-evidence.json` com fonte, data, hash, bytes e matches | Rastreia o vínculo URL/CNPJ; não comprova controle societário |
| Nulo não é zero | Campos inválidos ficam nulos e fora dos denominadores | Evita subestimar taxas e inventar tráfego |
| Dia pelo HTTP Date | `http_date` da página em `America/Sao_Paulo`; fallback para coleta | Evita usar o relógio local como verdade; páginas que cruzam o dia invalidam a captura |
| Erro e rejeição separados | Estados de intervalo independentes por numerador | Reset de rejeição não esconde erro válido; latência tem elegibilidade própria |
| Configuração fechada | Conjunto exato de 21 chaves, ordens e limites validados | Falha cedo; evita regra silenciosamente ignorada |
| Dois manuais | Manual runtime gerado por `documentation.py` e documentação v2 independente | O site mantém o manual operacional; a v2 cobre a jornada funcional/técnica |
| Sem chamadas a clientes | `contracts.endpoint_parts` valida texto e nunca faz request | Reduz risco e mantém o escopo Admin estrito |
| TLS do sistema | `truststore.SSLContext` com HTTP/2 | Confiança alinhada ao sistema operacional do runner |

### Validação da configuração

`validate_rules` exige que o objeto tenha exatamente as chaves de `DEFAULT_RULES`. Ele rejeita booleanos onde se espera número, valores não finitos, percentuais acima de 100, ordens invertidas, intervalos de agenda não suportados e listas de retry com mais de duas posições ou fora de 1–60 segundos. `schedule_cron` deriva o cron do intervalo e do minuto; o teste de configuração compara o resultado com `pages.yml`.

`validate_reporters` exige lista não vazia, campos de identidade preenchidos, `id` único, CNPJ de 14 dígitos e URL compatível com `https://<id>.api.santander.com.br/open-banking/admin/v2/metrics`, sem query, fragmento, usuário, senha ou porta alternativa.

### Consequências operacionais

- Alterar a retenção ou a janela do painel exige revisar o payload, os testes e a documentação; a retenção é aplicada em ciclos inteiros.
- Alterar o cron exige atualizar `rules.json` e `pages.yml`; o teste falha se divergirem.
- Alterar o esquema Arrow exige atualizar `build.SCHEMA`, o dicionário, as receitas e os testes de pipeline.
- Alterar o catálogo exige atualizar `reporters.json` e, idealmente, a evidência do Diretório; o catálogo é a fronteira de segurança.
- Alterar o layout do payload exige atualizar `web/app.js`, o manual runtime e esta documentação.

> Atenção: não edite `data/state.json` manualmente para “corrigir” uma observação. Use o fluxo de coleta/build ou restaure um pacote aprovado; a validação de estado e o checksum existem para proteger a série.

> Limitação: o repositório não contém um registro histórico de decisões (ADR) com justificativas originais. As decisões acima são inferidas do código, da configuração e dos testes; quando a motivação não é demonstrável, ela não é inventada.

## Glossário e referências

### Glossário

| Termo | Definição |
|---|---|
| Admin | API pública do Open Finance brasileiro que declara métricas operacionais dos serviços |
| Reporte | Fonte do catálogo; um dos oito hosts Santander |
| Endpoint declarado | URI descrita pelo banco dentro do relatório; não é chamada pelo monitor |
| Identidade / `entity_id` | Hash de `reporter_id` + `endpoint`, truncado em 24 caracteres |
| Ciclo / `run_id` | Execução lógica que agrupa coletas, análises e publicação |
| Observação | Linha normalizada de um endpoint em um ciclo |
| Bronze | Corpo HTTP integral preservado e endereçado por SHA-256 |
| Panorama | Último ciclo completo e coerente para um recorte (`all` ou uma fonte) |
| Dia analítico | Dia derivado do `HTTP Date` em `America/Sao_Paulo`, com fallback para a coleta |
| Intervalo | Comparação entre duas observações da mesma entidade e dia |
| Fingerprint | Hash das métricas atuais e do histórico, usado para detectar repetição |
| Sinal | Regra acima do limiar, ainda sem confirmação |
| Incidente | Ocorrência persistida de uma regra para uma entidade |
| Confirmado | Sinal repetido em `confirmation_samples` amostras consecutivas |
| Recuperação | Amostras avaliáveis consecutivas abaixo do limiar |
| `source_complete` | Cobertura reconciliada da captura que produziu a linha |
| `fresh` | Linha do ciclo mais recente; não mede idade do relógio |
| Mart | Tabela agregada derivada por SQL (`report_summary`, `family_summary`, `observation_trends`) |
| Release aprovada | Pacote `state-*` com recibo de deploy e checksums |
| Draft | Candidato de Release ainda não promovido |
| p95 | Percentil 95; não disponível no projeto |
| Taxa de erro | `100 × errors ÷ calls` com denominador válido |
| Taxa de rejeição | `100 × rejections ÷ calls` com denominador válido |
| Média ponderada | `Σ(mean_ms × calls) ÷ Σ(calls)` para linhas válidas com tráfego |
| Baseline | Mediana das médias diárias anteriores positivas |
| Recorrência contextual | Contagem de dias anteriores acima dos limiares de erro |
| DADOS ANTERIORES | Rótulo do painel quando o panorama preservado não é do ciclo atual |
| Lock | Arquivo `.writer.lock` que impede dois escritores simultâneos |
| Checksum | SHA-256 externo e interno usado para validar pacotes e bronzes |

### Mapa de módulos

| Arquivo | Responsabilidade |
|---|---|
| `src/admin_metrics/pipeline.py` | Orquestra coleta, análise, build, estado e GC de bronze |
| `src/admin_metrics/collect.py` | HTTP, catálogo, paginação, retry, deduplicação e bronze |
| `src/admin_metrics/contracts.py` | Validação passiva de URIs declaradas |
| `src/admin_metrics/storage.py` | Hash, escrita atômica, lock e contrato de estado |
| `src/admin_metrics/analysis.py` | Normalização, dia, qualidade, deltas, sinais e incidentes |
| `src/admin_metrics/health.py` | Classificação da tentativa e saúde da coleta |
| `src/admin_metrics/panorama.py` | Seleção do último ciclo completo por escopo |
| `src/admin_metrics/rules.py` | Validação de parâmetros e geração do cron |
| `src/admin_metrics/build.py` | Arrow, DuckDB, marts, Parquet, site e cópia da v2 |
| `src/admin_metrics/marts.sql` | Agregações SQL dos três marts |
| `src/admin_metrics/documentation.py` | Manual runtime autocontido |
| `src/admin_metrics/web/` | Dashboard estático e interativo |
| `scripts/cloud_pipeline.py` | Restore, candidato, promoção, descarte e retenção |
| `.github/workflows/pages.yml` | Agenda, build, deploy e confirmação |
| `.github/workflows/ci.yml` | Matriz de testes Python e dashboard |
| `config/reporters.json` | Catálogo dos oito reportes |
| `config/rules.json` | Parâmetros analíticos e de apresentação |
| `config/catalog-evidence.json` | Evidência do vínculo URL/CNPJ no Diretório |

### Referências externas

- [Dashboard publicado](https://alebitencourtx.github.io/admin-metrics/)
- [Manual runtime publicado](https://alebitencourtx.github.io/admin-metrics/documentacao.html)
- [Documentação v2 publicada](https://alebitencourtx.github.io/admin-metrics/docs_v2/documentacao-v2.html)
- [Contrato oficial Admin 2.0.1](https://raw.githubusercontent.com/OpenBanking-Brasil/openapi/main/swagger-apis/admin/2.0.1.yml)
- [Diretório de participantes do Open Finance](https://data.directory.openbankingbrasil.org.br/participants)
- [Workflow de coleta e publicação](https://github.com/alebitencourtx/admin-metrics/actions/workflows/pages.yml)

### Manutenção desta documentação

Esta documentação foi gerada com a skill `project-html-docs` a partir do código e da configuração da revisão `5a8cda6`. Os arquivos editáveis ficam em `docs_v2/document.json` e `docs_v2/content.md`; o HTML é um artefato de build e não deve ser editado manualmente.

```powershell
# Inventário estático e plano de leitura
python <skill>/scripts/inspect_repo.py . --out docs_v2/inventory.json --plan docs_v2/reading-plan.md

# Impacto incremental contra uma documentação existente
node <skill>/scripts/verify.mjs docs_v2/document.json docs_v2/documentacao-v2.validation.json --impact --dossier docs_v2/inventory.json --plan docs_v2/update-plan.md

# Build e verificação
node <skill>/scripts/build.mjs docs_v2/document.json --out docs_v2/documentacao-v2.html --force
node <skill>/scripts/verify.mjs docs_v2/document.json docs_v2/documentacao-v2.validation.json
```

> Regra de negócio: a documentação descreve a implementação da revisão indicada e o snapshot local identificado; ela não substitui a leitura do dashboard, das Releases ou dos relatórios oficiais para decisões operacionais.

> Limitação: o código prova a implementação, não uma execução de produção bem-sucedida. Números do snapshot têm data e origem; não devem ser tratados como telemetria ao vivo.
