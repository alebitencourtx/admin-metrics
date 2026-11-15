## Resumo executivo

O **Admin Metrics** é um observatório executivo dos oito reportes operacionais Santander que publicam o endpoint Admin do Open Finance. A cada ciclo, ele consulta somente `GET /open-banking/admin/v2/metrics` nos hosts autorizados, preserva o corpo original com hash SHA-256, normaliza as métricas declaradas pelo banco, calcula sinais analíticos explicáveis e publica um dashboard estático, um manual HTML autocontido e tabelas Parquet.

O produto responde a três perguntas: **o que exige atenção agora**, **qual é a evidência de cada endpoint** e **o que o observador conseguiu medir na última tentativa**. Ele não mede diretamente os serviços de clientes, consentimentos ou pagamentos descritos no relatório; mede a resposta do Admin e os agregados que o próprio banco declara.

<div class="cards">
<div class="card"><h3>Decisão apoiada</h3><p>Priorizar investigação por volume de erros, taxa com amostra mínima, rejeição, média declarada, regressão e recorrência no histórico reportado.</p></div>
<div class="card"><h3>Evidência preservada</h3><p>Cada tentativa HTTP guarda status, duração, cabeçalho Date, bytes, SHA-256 do corpo, URL e diagnóstico. O corpo bronze fica disponível nos dois ciclos recentes.</p></div>
<div class="card"><h3>Limite de leitura</h3><p>Média declarada não é p95; erro não identifica status HTTP; rejeição não prova 429; ausência de métrica não vira zero; acesso recusado ao Admin não prova indisponibilidade dos demais serviços.</p></div>
</div>

| Pergunta de negócio | Resposta nesta versão |
|---|---|
| Quem consome | Gestão, operação, analistas de dados e engenharia que acompanham a saúde operacional dos reportes Admin. |
| O que é entregue | Dashboard HTML na raiz do Pages, manual completo e resumido, `dashboard.json`, tabelas Parquet e pacotes de estado nas Releases. |
| Qual é o grão | Uma observação = uma execução × um reporte × um endpoint declarado. Um incidente = uma entidade × uma regra, com histórico de detecção e recuperação. |
| Quando atualiza | Cron horário `17 * * * *` UTC no GitHub Actions, além de `workflow_dispatch` e republicação em push. A agenda é *best effort*. |
| Qual é a janela | Séries do painel: 72 horas. Estado normalizado: 30 dias. Bronze empacotado: dois ciclos recentes. Releases aprovadas: duas. |
| Qual é o estado observado | Snapshot local de implementação de **2026-11-10T18:37:28Z**: oito fontes com HTTP 200 e **276 identidades**. O Santander principal declarou páginas excedentes, registrado como `page_metadata_conflict`. |
| O que não é | Laudo de conformidade regulatória, medição de p95, teste sintético de todos os serviços ou alerta com garantia de pontualidade. |

> Regra de negócio: o painel usa **um único ciclo completo e um único dia de referência** por recorte. Quando a tentativa atual não consegue renovar esse conjunto, os KPIs continuam identificados como **DADOS ANTERIORES**; a saúde da coleta reflete a tentativa atual.

> Exemplo prático: em uma execução em que seis fontes retornam dados válidos e duas retornam HTTP 200 vazio, a saúde da coleta fica `partial`. O panorama executivo pode continuar no último ciclo completo, com dia explícito, enquanto os cartões de cada fonte mostram a tentativa recente e a idade do último dado válido.

A revisão documental é de **2026-11-15** e descreve o projeto na versão **1.2.0** (modelo de captura **3**, envelope de estado **1**), a partir da revisão de código `62994d4`, agora republicada como manual **v2** completo e guia resumido. Consulte o [escopo e estado atual](#escopo), a [arquitetura](#arquitetura), as [regras](#regras) e as [limitações](#limites) antes de usar os números como conclusão operacional.

## Escopo e estado atual

O monitor acompanha oito reportes operacionais do grupo Santander. O catálogo é explícito e versionado em `config/reporters.json`; Nissan e Renault permanecem fontes distintas mesmo compartilhando o mesmo CNPJ. O vínculo entre URL e CNPJ foi conferido no Diretório oficial de participantes e o comprovante é mantido em `config/catalog-evidence.json`, com data, SHA-256 e tamanho do documento consultado.

| Reporte | Empresa declarada | CNPJ | Host consultado |
|---|---|---|---|
| Santander CCVM | SANTANDER CCVM S.A. | `51014223000149` | `ccvm.api.santander.com.br` |
| Aymoré | AYMORE CFI S.A. | `07707650000110` | `financiamentos.api.santander.com.br` |
| Getnet | GETNET ADQUIRENCIA E SERVICOS PARA MEIOS DE PAGAMENTO S A | `10440482000154` | `getnet.api.santander.com.br` |
| Hyundai Capital | BANCO HYUNDAI CAPITAL BRASIL | `30172491000119` | `hyundai.api.santander.com.br` |
| RCI · Nissan | BCO RCI BRASIL S.A. | `62307848000115` | `nissan.api.santander.com.br` |
| Santander | BCO SANTANDER (BRASIL) S.A. | `90400888000142` | `openbanking.api.santander.com.br` |
| RCI · Renault | BCO RCI BRASIL S.A. | `62307848000115` | `renault.api.santander.com.br` |
| Toro | Santander CTVM S.A. | `29162769000198` | `toro.api.santander.com.br` |

O comprovante de catálogo registra `verified_at` em **2026-11-10T18:37:29Z**, documento de **4.486.521 bytes**, SHA-256 `c7f7c645...e164c2b`, **15 correspondências** e a ressalva de que o vínculo por API e CNPJ **não comprova controle societário**. O catálogo é a lista fechada de hosts; o validador rejeita esquema diferente de HTTPS, host fora do padrão `<id>.api.santander.com.br`, porta diferente de 443, credenciais na URL, query, fragmento ou caminho diferente de `/open-banking/admin/v2/metrics`.

### O que está implementado

| Capacidade | Implementação atual |
|---|---|
| Coleta auditável | HTTPX assíncrono com HTTP/2, TLS via `truststore`, timeout de 20 s, até quatro reportes simultâneos, uma página por reporte e nenhum redirecionamento seguido. |
| Limites de captura | 20 páginas, 16 MiB por resposta, 10.000 identidades por reporte e retry limitado a transporte/408/429/500/502/503/504/529. |
| Proveniência | Corpo bruto endereçado por SHA-256 em `data/bronze/<hash>.json`; cada tentativa guarda URL, status, duração, Date, bytes, tentativa e erro. |
| Normalização | Contadores inteiros não negativos; percentuais apenas com denominador positivo e numerador válido; nulos explícitos; dia analítico por página. |
| Histórico | Estado JSON de 30 dias, deltas de contadores cumulativos, baseline de médias, recorrência e incidentes com confirmação e recuperação. |
| Materialização | Arrow tipado, DuckDB embutido, SQL versionado e Parquet Zstandard; três marts analíticos e duas projeções físicas. |
| Entrega | Dashboard estático com oito seções, manual HTML único, `dashboard.json`, CSV de endpoints e assets endereçados por conteúdo. |
| Publicação | GitHub Actions com jobs de build, deploy e confirmação; Release candidata em draft e promoção somente após deploy comprovado. |
| Qualidade | 107 testes Python e 14 testes Node aprovados na revisão local de 2026-11-15; CI em Linux/Windows e Python 3.11/3.12. |

### O que não está no escopo

- Autenticação corporativa, SSO, RBAC, SLA contratado ou operação 24×7.
- Coleta direta de endpoints de clientes, consentimentos, pagamentos ou dados pessoais.
- Medição sintética de todos os serviços citados no relatório Admin.
- Cálculo de p95, percentis ou latência intervalar a partir de médias cumulativas.
- Inferência de causa para erros, rejeições ou bloqueios de acesso.
- Garantia de execução pontual do cron do GitHub Actions.
- Laudo de conformidade regulatória ou substituição de auditoria independente.

```chart
{"type":"bar","title":"Identidades declaradas por reporte no snapshot local","unit":"identidades","source":"site/dashboard.json · execução initial-local-20261110","asOf":"2026-11-10T18:37:28Z","data":[{"label":"Santander principal","value":112,"variant":"accent"},{"label":"Toro","value":45,"variant":"accent"},{"label":"Aymoré","value":27,"variant":"accent"},{"label":"Santander CCVM","value":23,"variant":"accent"},{"label":"Hyundai Capital","value":22,"variant":"accent"},{"label":"RCI · Nissan","value":16,"variant":"neutral"},{"label":"RCI · Renault","value":16,"variant":"neutral"},{"label":"Getnet","value":15,"variant":"neutral"}]}
```

> Atenção: os números do gráfico são um **snapshot local de implementação**, não telemetria ao vivo. Eles demonstram a forma do payload e a cobertura reconciliada naquela execução; não devem ser repetidos como se fossem a situação atual da produção.

> Limitação: o snapshot local contém uma execução e 276 identidades. A série publicada cresce a partir da primeira coleta remota; não há preenchimento retroativo de horários que não foram observados. O estado retido nas Releases e o warehouse preservam 30 dias, mas o payload do Pages publica apenas a janela de 72 horas.

## Uso do dashboard

O dashboard é uma página HTML contínua com navegação lateral por oito seções. O seletor **Reporte** no topo é um filtro global: ele altera panorama, incidentes, tendências, endpoints, saúde da coleta, monitor de execuções e qualidade. O filtro escolhe o último ciclo válido daquele recorte e não mistura fontes de ciclos ou dias diferentes no agregado.

| Seção | Pergunta que responde | Como ler |
|---|---|---|
| 01 · Panorama executivo | O que exige atenção agora? | KPIs, leitura do recorte, top cinco endpoints por erros e cartões por reporte. |
| 02 · Incidentes | Quais sinais estão abertos, em recuperação ou resolvidos? | Severidade, regra, evidência, primeira observação, persistência e amostras de recuperação. |
| 03 · Tendências | Como a métrica evoluiu nas observações próprias? | Pontos com horário e valor; lacunas, atraso e mudança de dia interrompem a linha. |
| 04 · Endpoints | Qual serviço reportado concentra o problema? | Busca sem acento, família, ordenação, tabela paginada e detalhe por endpoint. |
| 05 · Saúde da coleta | O que o observador conseguiu medir? | HTTP, cobertura, identidades, última tentativa, duração do Admin e diagnóstico. |
| 06 · Monitor de execuções | Como cada API respondeu em cada extração? | Matriz de 12 execuções por página, células clicáveis e todas as tentativas preservadas. |
| 07 · Qualidade do reporte | Quais inconsistências mudam a interpretação? | Ocorrências por regra e classificação da comparação com a observação anterior. |
| 08 · Metodologia | Quais critérios e limites estão em vigor? | Regras configuráveis, fontes oficiais e distinção entre média, p95 e ausência. |

### Ler a atualização sem confundir os relógios

O aviso de atualização separa **última tentativa** de **últimos dados válidos do panorama**. Uma tentativa recente vazia não renova o relógio dos dados válidos. O navegador calcula a idade a partir do último panorama válido e muda o aviso após `stale_after_hours` (2 horas por padrão), mesmo sem novo deploy.

- **Tentativa:** instante em que a fonte foi consultada e resultado daquela consulta.
- **Último dado válido:** instante do último ciclo completo que pode alimentar o panorama daquele recorte.
- **DADOS ANTERIORES:** o panorama exibido é de um ciclo anterior; os valores preservados não viram pontos novos.
- **CICLO ATUAL:** o panorama é da execução mais recente do payload.
- **SEM PANORAMA VÁLIDO:** não existe ciclo completo com um único dia de referência para o recorte.

> Regra de negócio: a saúde da coleta é independente do sucesso de publicação. Um workflow verde significa que o processamento e a publicação concluíram; não significa que todas as fontes devolveram métricas válidas.

### Incidentes e persistência

A tabela de incidentes ordena primeiro os críticos e depois o último sinal. O filtro **Estado** permite ver abertos e em recuperação, todos (incluindo resolvidos dos últimos três dias no payload) ou somente críticos ativos. O detalhe mostra quantas detecções ocorreram, quantas foram consecutivas e quantas amostras de recuperação foram acumuladas.

> Exemplo prático: uma regra detectada em uma amostra abre um incidente provisório. Após duas detecções consecutivas, ele fica **confirmado**. Quando duas amostras avaliáveis consecutivas ficam abaixo do limiar, o estado passa a **recuperando** e, na segunda, a **resolvido**. Uma amostra ausente, inválida ou com tráfego abaixo do mínimo **não** conta como recuperação.

### Tendências, endpoints e exportação

Os gráficos usam a janela de 72 horas terminada no último ciclo do payload. A linha só é contínua quando os pontos pertencem ao mesmo dia e estão separados por menos de `chart_gap_hours` (1,5 hora). Períodos sem coleta ficam vazios; o eixo não inventa pontos. A métrica **Chamadas acumuladas do dia** é um contador cumulativo declarado, não uma taxa de chegada por hora.

A busca de endpoints ignora acentos e procura no caminho e no rótulo do reporte. A tabela ordena por erros, taxa de erro, média declarada, chamadas ou nome. O botão **Exportar endpoints** gera CSV com BOM, separador `;` e proteção contra injeção de fórmula; o arquivo reflete o filtro visível.

O detalhe de um endpoint separa duas séries que não devem ser somadas:

| Série | Origem | O que representa |
|---|---|---|
| Observações próprias | Coletas do monitor | Acumulados declarados no instante de cada captura, com cobertura e dia analítico. |
| Dias anteriores declarados | `previousDays` do payload | Histórico diário informado pelo banco, rotulado D−1, D−2 e D−3 na visualização. |

> Atenção: clicar em um endpoint de um **panorama anterior** pode abrir um detalhe com a série própria fora da janela de 72 horas. A interface explica a ausência; ela não transforma a ausência em zero nem inventa uma série.

## Arquitetura da solução

A solução é um ETL em lote, *single node*, executado em runner temporário. O estado vive em JSON e em pacotes de Release; não há banco de dados permanente contratado. DuckDB é embutido no processo Python e materializa as projeções analíticas uma vez por build.

```solution
{
  "title": "Arquitetura em estágios 2D — coleta, análise e publicação",
  "cols": 5,
  "colWidth": 214,
  "colGap": 58,
  "inputs": { "label": "ENTRADAS" },
  "zones": [
    { "id": "aquisicao", "title": "ESTÁGIO 1 · AQUISIÇÃO E EVIDÊNCIA", "subtitle": "runner temporário, rede limitada e bronze imutável", "variant": "warm", "row": 0, "colStart": 1, "colSpan": 4 },
    { "id": "analise", "title": "ESTÁGIO 2 · ANÁLISE, ESTADO E ENTREGA", "subtitle": "normalização, regras, marts e HTML estático", "variant": "cool", "row": 1, "colStart": 1, "colSpan": 4 }
  ],
  "nodes": [
    { "id": "admin", "col": 0, "row": 0, "shape": "cylinder", "role": "regulator", "title": "8 reportes Admin", "lines": ["`GET /open-banking/admin/v2/metrics`", "oito hosts Santander", "sem chamadas a clientes"] },
    { "id": "collect", "col": 1, "row": 0, "step": 1, "role": "step", "title": "Coletar", "lines": ["HTTPX + TLS do sistema", "4 fontes simultâneas", "retry e paginação limitados"] },
    { "id": "bronze", "col": 2, "row": 0, "shape": "cylinder", "role": "analytical", "title": "Bronze SHA-256", "lines": ["`data/bronze/<hash>.json`", "corpo exato + proveniência", "dois ciclos no pacote"] },
    { "id": "state", "col": 3, "row": 0, "shape": "cylinder", "role": "analytical", "title": "Estado normalizado", "lines": ["`data/state.json`", "30 dias de histórico", "incidentes e último contexto"] },
    { "id": "releases", "col": 4, "row": 0, "shape": "cylinder", "role": "neutral", "title": "GitHub Releases", "lines": ["dois pacotes aprovados", "`state.zip` + `SHA256SUMS`", "fora do histórico Git"] },
    { "id": "catalog", "col": 0, "row": 1, "role": "regulator", "title": "Catálogo e regras", "lines": ["`config/reporters.json`", "`config/rules.json`", "evidência do Diretório"] },
    { "id": "normalize", "col": 1, "row": 1, "step": 2, "role": "step", "title": "Normalizar", "lines": ["nulos explícitos e flags", "dia por página", "`entity_id` estável"] },
    { "id": "analyze", "col": 2, "row": 1, "step": 3, "role": "step", "title": "Avaliar", "lines": ["deltas de contadores", "incidentes e recuperação", "panorama coerente por recorte"] },
    { "id": "gold", "col": 3, "row": 1, "shape": "cylinder", "role": "output", "title": "Gold analítico", "lines": ["Arrow → DuckDB → Parquet", "`report_summary`", "`family_summary` e tendências"] },
    { "id": "pages", "col": 4, "row": 1, "role": "output", "title": "GitHub Pages", "lines": ["dashboard + `dashboard.json`", "manual completo e resumido", "assets por conteúdo"] }
  ],
  "edges": [
    { "from": "admin", "to": "collect", "fromSide": "right", "toSide": "left" },
    { "from": "catalog", "to": "collect", "fromSide": "right", "toSide": "left", "style": "dashed", "label": "lista fechada" },
    { "from": "collect", "to": "bronze", "fromSide": "right", "toSide": "left", "label": "corpo + hash" },
    { "from": "bronze", "to": "normalize", "fromSide": "bottom", "toSide": "top", "label": "bytes e json_path" },
    { "from": "catalog", "to": "normalize", "fromSide": "right", "toSide": "left", "style": "dashed", "label": "limiares" },
    { "from": "normalize", "to": "analyze", "fromSide": "right", "toSide": "left" },
    { "from": "analyze", "to": "state", "fromSide": "top", "toSide": "bottom", "label": "estado + incidentes" },
    { "from": "state", "to": "normalize", "fromSide": "left", "toSide": "top", "style": "dashed", "label": "histórico 30 dias" },
    { "from": "analyze", "to": "gold", "fromSide": "right", "toSide": "left", "label": "Arrow/DuckDB" },
    { "from": "gold", "to": "pages", "fromSide": "right", "toSide": "left", "label": "Parquet + HTML" },
    { "from": "state", "to": "releases", "fromSide": "right", "toSide": "left", "style": "dashed", "label": "pacote aprovado" }
  ],
  "legend": [
    { "type": "box", "role": "regulator", "label": "Dados de entrada e catálogo" },
    { "type": "box", "role": "analytical", "label": "Bronze e estado" },
    { "type": "box", "role": "step", "label": "Etapas executáveis" },
    { "type": "box", "role": "output", "label": "Marts e entrega" },
    { "type": "dashed", "role": "neutral", "label": "Dependência de configuração ou persistência" }
  ],
  "note": "O estado só é gravado depois que o HTML e todos os marts foram gerados. O runner restaura o último pacote aprovado antes de coletar; sem estado aprovado, faz bootstrap. O bronze local remove apenas arquivos de hash conhecidos e mantém os dois ciclos recentes."
}
```

| Objeto | Papel | Lido / gravado |
|---|---|---|
| `config/reporters.json` | Lista fechada dos oito hosts e identidades | Lido no início de toda execução e validado antes da coleta. |
| `config/rules.json` | Limiares e parâmetros analíticos versionados | Lido e validado antes da coleta; copiado para cada run. |
| `config/catalog-evidence.json` | Comprovante de conferência no Diretório | Lido como evidência documental; não é consultado em tempo de execução. |
| `data/bronze/<sha>.json` | Corpo HTTP exato endereçado por SHA-256 | Gravado pelo coletor; lido no restore e na auditoria; retido por dois ciclos no pacote. |
| `data/state.json` | Estado normalizado de 30 dias | Lido no início do build e gravado após a geração completa. |
| `data/gold/*.parquet` | Projeções Arrow/DuckDB | Gravado no build; consumido por analistas e ferramentas externas. |
| `site/index.html` + `site/assets/<hash>/` | Dashboard e assets imutáveis | Gerado por build; a raiz referencia o hash atual. |
| `site/documentacao.html` | Manual gerado com os dados do ciclo | Gerado por build; distribuível sozinho. |
| `site/docs_v2/documentacao-v2.html` e `...-resumida.html` | Manual v2 completo e guia rápido | Copiados do diretório `docs_v2/` para o Pages. |
| Releases `state-*` | Pacotes de estado aprovados | Criados em draft, promovidos após deploy e limitados aos dois mais recentes. |

### Componentes e fronteiras

| Módulo | Responsabilidade |
|---|---|
| `collect.py` | Validação do catálogo, HTTPX, TLS, timeout, retry, paginação, deduplicação e bronze. |
| `contracts.py` | Validação segura das URIs declaradas, sem executar chamadas. |
| `health.py` | Resultado da coleta separado do sucesso de processamento/publicação. |
| `analysis.py` | Normalização, nulos, flags, deltas, baseline, recorrência e máquina de incidentes. |
| `panorama.py` | Escolha de um ciclo completo e um dia coerente por recorte. |
| `rules.py` | Configuração tipada, limiares, ordem e cron. |
| `storage.py` | Hash, escrita atômica, lock de escritor e carregamento do estado. |
| `archive.py` | Pacote limitado, manifesto, checksums e restore com rollback. |
| `build.py` | Arrow, DuckDB, Parquet, HTML, assets e cópia dos manuais. |
| `marts.sql` | Definições SQL de resumo por reporte, família e tendência. |
| `pipeline.py` | Orquestra coleta, aplicação, build, commit do estado e retenção. |
| `cloud_pipeline.py` | Restore, candidato draft, confirmação de deploy e retenção remota. |
| `web/app.js` | Filtros, navegação, gráficos, detalhes, monitor e exportação. |
| `documentation.py` | Manual HTML gerado a partir do estado e do código desta versão. |

A fronteira de confiança é explícita: o navegador lê somente `data.js`/`dashboard.json` empacotados; não consulta APIs bancárias. O único tráfego de saída do ETL vai para os oito hosts do catálogo. Não há CDN, fonte remota ou script externo no dashboard e nos manuais.

> Limitação: a arquitetura é single node e um escritor por lake. O lock impede dois escritores simultâneos no mesmo root, mas não distribui trabalho entre máquinas. Um lock abandonado exige conferir o processo antes da remoção manual.

## Fluxo de coleta e publicação

O workflow principal roda em `ubuntu-latest`, com concorrência única `admin-state-and-pages` e `cancel-in-progress: false`. Ele pode ser acionado por push em `main`, pelo cron `17 * * * *` UTC ou manualmente. O input `refresh_data` decide se o ciclo coleta uma nova amostra ou apenas republica o estado aprovado.

```flow
{
  "title": "Fluxo de uma execução e gates de publicação",
  "cols": 4,
  "colWidth": 232,
  "colGap": 46,
  "zones": [
    { "id": "f1", "title": "1 · RETOMADA E COLETA", "subtitle": "estado aprovado, catálogo e resposta bruta", "variant": "warm", "row": 0, "colStart": 0, "colSpan": 2 },
    { "id": "f2", "title": "2 · AQUISIÇÃO", "subtitle": "oito fontes, limites e proveniência", "variant": "cool", "row": 0, "colStart": 2, "colSpan": 2 },
    { "id": "f3", "title": "3 · CONFIRMAÇÃO", "subtitle": "Pages e Release não são uma transação distribuída", "variant": "teal", "row": 1, "colStart": 0, "colSpan": 2 },
    { "id": "f4", "title": "4 · MATERIALIZAÇÃO", "subtitle": "regras, marts, HTML e pacote candidato", "variant": "neutral", "row": 1, "colStart": 2, "colSpan": 2 }
  ],
  "nodes": [
    { "id": "trigger", "col": 0, "row": 0, "step": 1, "role": "step", "title": "Acionar", "lines": ["cron, push ou manual", "concurrency única"] },
    { "id": "has_state", "col": 1, "row": 0, "shape": "decision", "role": "warning", "title": "Existe estado aprovado?", "lines": ["Release com purpose, run e assets válidos"] },
    { "id": "restore", "col": 2, "row": 0, "step": 2, "role": "success", "title": "Restaurar", "lines": ["checksum externo e interno", "manifesto, limites e rollback"] },
    { "id": "collect", "col": 3, "row": 0, "step": 3, "role": "analytical", "title": "Coletar 8 fontes", "lines": ["4 simultâneas", "retry, paginação e dedup"] },
    { "id": "publish", "col": 0, "row": 1, "step": 7, "role": "success", "title": "Confirmar estado", "lines": ["promover Release após deploy", "descartar draft em falha"] },
    { "id": "deploy", "col": 1, "row": 1, "step": 6, "role": "output", "title": "Publicar Pages", "lines": ["upload do diretório `site`", "deploy e URL pública"] },
    { "id": "build", "col": 2, "row": 1, "step": 5, "role": "step", "title": "Gerar artefatos", "lines": ["estado + marts + HTML", "candidato draft"] },
    { "id": "apply", "col": 3, "row": 1, "step": 4, "role": "step", "title": "Aplicar regras", "lines": ["normalizar, deltas e incidentes", "panorama e saúde"] }
  ],
  "edges": [
    { "from": "trigger", "to": "has_state", "fromSide": "right", "toSide": "left" },
    { "from": "has_state", "to": "restore", "branch": "yes", "label": "Sim" },
    { "from": "restore", "to": "collect", "label": "refresh" },
    { "from": "collect", "to": "apply", "fromSide": "bottom", "toSide": "top" },
    { "from": "apply", "to": "build", "fromSide": "left", "toSide": "right" },
    { "from": "build", "to": "deploy", "fromSide": "left", "toSide": "right", "label": "HTML + marts" },
    { "from": "deploy", "to": "publish", "fromSide": "left", "toSide": "right", "label": "deploy ok" }
  ],
  "legend": [
    { "type": "box", "role": "step", "label": "Etapas do workflow" },
    { "type": "box", "role": "warning", "label": "Decisão de estado/refresh" },
    { "type": "box", "role": "success", "label": "Caminho de confirmação" },
    { "type": "box", "role": "output", "label": "Entrega pública" }
  ],
  "note": "O build testa pytest e Node antes de coletar. Se o build falhar antes do upload, o site e o estado anteriores permanecem. Se o deploy falhar, a Release candidata é descartada. Se o deploy concluir e a confirmação falhar, o candidato pode permanecer em draft: consulte o ID do dashboard e o job antes de recuperar."
}
```

1. **Restore.** O workflow consulta Releases publicadas e aceita somente pacotes com tag `state-*`, `purpose=approved-monitor-state`, `workflow_run_id`, `data_run_id` e os assets `state.zip`/`SHA256SUMS`. Sem Release aprovada, o primeiro ciclo faz bootstrap com coleta.
2. **Coleta.** O coletor valida o catálogo, abre no máximo quatro capturas simultâneas e percorre páginas com `page-size=1000` e `period=ALL`. Cada página vira um corpo bronze; cada tentativa fica registrada.
3. **Aplicação.** As linhas são normalizadas, deduplicadas por `(reporter_id, endpoint)` e avaliadas contra a observação anterior da mesma entidade. O estado recebe a execução, as observações, os incidentes e o último contexto útil por reporte.
4. **Build.** Arrow tipado alimenta `current_rows` e `observations`; `marts.sql` produz os três marts; Parquet Zstandard é gravado em `data/gold/`; o HTML, o `dashboard.json` e o manual são gerados em um diretório de staging.
5. **Candidato.** O estado é empacotado com os dois bronzes recentes, manifesto e `SHA256SUMS`; uma Release draft é criada antes do deploy.
6. **Deploy.** O diretório `site` é enviado ao GitHub Pages. O job `deploy` precisa concluir com sucesso para que a confirmação aceite o candidato.
7. **Confirmação.** A Release é promovida, recebe um recibo de deploy e as Releases aprovadas além das duas mais recentes são removidas. Em falha de deploy, o draft é descartado.

### Regras de captura e conciliação

| Condição | Comportamento implementado | Efeito no consumo |
|---|---|---|
| HTTP 200 com `data` vazio | `empty_report`; `data_status=empty`; sem linhas novas | Não renova métricas; pode acionar recaptura se a fonte já teve dados válidos. |
| Primeira captura vazia no bootstrap | Não repete automaticamente | Evita transformar ausência inicial em coleta infinita. |
| Vazio em fonte previamente preenchida | Até duas recapturas após 10 s e 30 s | A espera libera a vaga de concorrência; tentativas ficam preservadas. |
| HTTP 403 | Sem retry e sem contornar bloqueio | Diagnóstico de acesso recusado; não prova indisponibilidade dos serviços. |
| Transporte ou HTTP 408/429/500/502/503/504/529 | Até três tentativas com `Retry-After` limitado a 15 s | A última tentativa define o status final; tentativas anteriores ficam no histórico. |
| Página repetida sem identidade nova | `pagination_no_new_identity`; captura não confirmada | Não soma páginas repetidas nem infla tráfego. |
| Mesma identidade com valores conflitantes | Primeira linha permanece; `conflicting_endpoint`; `ambiguous` | Captura incompleta e fora dos KPIs do ciclo atual. |
| Total de identidades coberto, mas `totalPages` excedente | `page_metadata_conflict`; cobertura conciliada | Não busca páginas fantasma; o conflito de metadata fica visível. |
| Páginas cruzam a meia-noite | `page_day_changed`; captura `mixed_reference_day` | Todas as linhas ficam incompletas e não alimentam o panorama. |
| URI de endpoint inválida | `invalid_endpoint_record`; linha descartada | Captura incompleta; outras fontes continuam. |
| Limite de 10.000 identidades | `record_limit`; captura incompleta | O teto é efetivo; não há crescimento silencioso da captura. |

> Regra de negócio: a deduplicação é por identidade de endpoint dentro do reporte. A primeira ocorrência é mantida como evidência; se a mesma identidade aparecer com valores diferentes, a captura fica ambígua e incompleta em vez de escolher silenciosamente o “melhor” valor.

### Idempotência e falhas

- O `run_id` é UTC com sufixo aleatório. `apply` rejeita um `run_id` já aplicado.
- O estado só avança depois que o build inteiro terminou; uma falha de HTML ou SQL preserva o site e o estado anteriores.
- O build é idempotente para o mesmo estado: `build` não cria nova observação.
- O bronze local mantém somente hashes referenciados pelos dois ciclos recentes; arquivos fora desse conjunto são removidos.
- A ausência de uma fonte não impede a coleta das outras; o `asyncio.gather` devolve o resultado de cada worker.
- O workflow de publicação testa antes de coletar e tem *timeout* de 15 minutos no build e 10 minutos no deploy.

> Atenção: o restore verifica o checksum externo, os hashes internos, o manifesto, os nomes permitidos, duplicatas e limites de expansão **antes** de alterar o diretório de dados. Se a gravação do `state.json` falhar, os arquivos já gravados são removidos; o restore pode ser repetido.

## Regras de negócio e cálculos

As métricas vêm do contrato Admin 2.0.1. Para cada endpoint, o payload traz `invocations`, `errors`, `rejections`, `averageResponse`, `averageTps` e `peakTps`, cada um com `currentDay` e `previousDays`. O monitor não soma snapshots de horários diferentes como se fossem tráfego novo.

### Fórmulas e denominadores

- **Chamadas:** `invocations.currentDay`, inteiro não negativo ou nulo.
- **Erros:** `errors.currentDay`, inteiro não negativo ou nulo, sem detalhamento por status HTTP.
- **Rejeições:** `rejections.currentDay`, inteiro não negativo ou nulo, sem causa implícita.
- **Média declarada:** `averageResponse.currentDay` em milissegundos, positiva ou nula.
- **Taxa de erro:** `100 × errors ÷ calls`, apenas quando `calls > 0` e `0 ≤ errors ≤ calls`; caso contrário, **nula**.
- **Taxa de rejeição:** `100 × rejections ÷ calls` sob os mesmos critérios, com denominador válido próprio.
- **Média ponderada:** `Σ(mean_ms × calls) ÷ Σ(calls)`, somente para linhas com `mean_ms > 0` e `calls > 0`.
- **Delta de contador:** `current − previous` para a mesma entidade, mesmo dia, ambas as fontes completas e contadores não decrescentes.

> Regra de negócio: uma taxa com denominador zero, numerador nulo, numerador maior que as chamadas ou valor não finito é **indisponível**, não zero. O mesmo vale para a média quando não há chamadas positivas.

> Exemplo prático: 2.000 chamadas e 500 erros resultam em `100 × 500 ÷ 2.000 = 25%`, acima de 20%, com amostra de 2.000 chamadas; o sinal é **crítico**. Já 120 chamadas e 30 erros resultam em 25%, mas a amostra é inferior a 1.000 chamadas; o sinal de erro é **atenção**, não crítico.

### Limiares configurados

| Parâmetro | Valor | Efeito |
|---|---:|---|
| `error_attention_pct` | 5% | Taxa de erro ≥ 5% com pelo menos `minimum_calls` chamadas gera atenção. |
| `error_critical_pct` | 20% | Taxa de erro ≥ 20% com pelo menos `critical_minimum_calls` chamadas eleva a crítico. |
| `minimum_calls` | 100 | Amostra mínima para erro, rejeição, latência e recorrência. |
| `critical_minimum_calls` | 1.000 | Amostra mínima para criticidade de erro. |
| `rejection_attention_pct` | 5% | Rejeição ≥ 5% com pelo menos 100 chamadas gera atenção, sem inferir causa. |
| `latency_attention_ms` | 2.000 ms | Média declarada ≥ 2.000 ms gera atenção. |
| `latency_critical_ms` | 4.000 ms | Média declarada ≥ 4.000 ms gera crítico, com amostra mínima de 100 chamadas. |
| `regression_multiplier` | 2× | Média atual ≥ 2× a mediana de pelo menos `baseline_minimum_days` médias diárias anteriores positivas. |
| `baseline_minimum_days` | 3 | Mínimo de médias diárias anteriores positivas para formar baseline. |
| `recurrent_minimum_days` | 3 | Mínimo de dias anteriores com erro ≥ 5% e ≥ 100 chamadas para recorrência. |
| `reported_history_days` | 7 | Máximo de posições `previousDays` aceitas por métrica. |
| `confirmation_samples` | 2 | Detecções consecutivas para confirmar um incidente. |
| `recovery_samples` | 2 | Amostras avaliáveis consecutivas abaixo do limiar para resolver. |
| `clock_skew_seconds` | 900 | Desvio absoluto entre `observed_at` e `requestTime` que gera flag. |
| `stale_after_hours` | 2 | Idade a partir da qual o navegador marca dados válidos como desatualizados. |
| `chart_gap_hours` | 1,5 | Lacuna de tempo que interrompe a linha do gráfico. |
| `empty_retry_delays_seconds` | `[10, 30]` | Duas recapturas após resposta vazia de fonte previamente preenchida. |
| `retention_days` | 30 | Retenção do estado normalizado e dos incidentes resolvidos. |
| `dashboard_history_days` | 3 | Janela de runs e séries publicada no Pages. |
| `schedule_interval_hours` | 1 | Intervalo do cron; aceita 1, 2, 3, 4, 6, 8, 12 ou 24. |
| `schedule_minute` | 17 | Minuto UTC do cron. |

> Limitação: os limiares são critérios analíticos internos, configuráveis e visíveis. Eles não são SLAs regulatórios, não representam p95 e não substituem uma investigação causal.

### Deltas de contadores cumulativos

Um delta só é aceito quando as duas observações são da mesma entidade, têm o mesmo dia de referência, ambas as fontes estão completas, os contadores são válidos e não decresceram, e o delta do numerador não excede o delta de chamadas. Um reporte idêntico ao anterior não gera tráfego intervalar.

| `interval_state` | Condição | Leitura |
|---|---|---|
| `valid` | Todos os critérios atendidos | `interval_calls`, erros, rejeições e taxas estão disponíveis. |
| `first_observation` | Não há observação anterior da entidade | Sem delta; primeira captura. |
| `observation_time_not_increasing` | Instante atual ≤ anterior | Comparação suspensa. |
| `day_changed` | O dia de referência mudou | Contadores cumulativos não são comparáveis entre dias. |
| `incomplete_source` | Uma das capturas está incompleta | Sem delta confiável. |
| `unchanged_report` | Fingerprint idêntico ao anterior | Não é tráfego novo; delta indisponível. |
| `invalid_counter` | Contador nulo, negativo ou acima das chamadas | Delta suspenso. |
| `counter_reset_or_revision` | Contador diminuiu | Reset ou revisão; não há volume negativo. |
| `inconsistent_delta` | Delta de erro/rejeição maior que o delta de chamadas | Delta suspenso. |

> Exemplo prático: D−1 tinha 1.000 chamadas e 50 erros; a observação atual tem 1.500 chamadas e 75 erros. O delta é de 500 chamadas e 25 erros, resultando em `100 × 25 ÷ 500 = 5%`, e não em 5% do acumulado total. Se as chamadas caíssem para 1.400, o delta de chamadas seria negativo e o estado seria `counter_reset_or_revision`.

### Incidentes: detecção, confirmação e recuperação

Cada incidente tem identidade própria por `entity_id + rule + run de abertura`. Reabrir depois de resolver cria outro ID. A severidade pode mudar na mesma ocorrência; a evidência é atualizada com o último sinal.

| Situação | Resultado | Leitura |
|---|---|---|
| Primeira detecção de uma regra | Incidente `open`, ainda provisório | Sinal observado, sem confirmação de persistência. |
| Segunda detecção consecutiva | `confirmed=true` | Persistência confirmada por amostras; não prova novos erros no intervalo. |
| Primeira amostra avaliável abaixo do limiar | `recovering` | Recuperação iniciada, ainda não resolvida. |
| Segunda amostra avaliável consecutiva abaixo do limiar | `resolved` | Regra afetada resolvida; `resolved_at` registrado. |
| Amostra ausente, inválida, incompleta ou com tráfego baixo | Não conta como recuperação | A sequência de recuperação é zerada. |
| Falha de coleta na primeira amostra | `attention` | Problema observado, ainda não confirmado. |
| Falha de coleta na segunda consecutiva | `critical` | Persistência de falha de coleta. |
| Reset de contadores | Suspende regras de contadores | Latência válida continua sendo avaliada separadamente. |

> Atenção: “confirmado por persistência” significa que o sinal se repetiu acima do limiar em duas observações avaliáveis. Pode ocorrer com contadores cumulativos sem mudança real e não demonstra, sozinho, novos erros no intervalo.

## Qualidade, incidentes e continuidade

A qualidade do reporte é tratada como parte do dado, não como um selo de conformidade. O monitor preserva o valor informado e anexa flags quando o contrato, a consistência interna ou a proveniência exigem cautela. Nenhuma flag é usada para “corrigir” silenciosamente o valor de origem.

### Flags de qualidade

| Flag | Condição | Efeito |
|---|---|---|
| `request_time_invalid` | `requestTime` ausente ou não interpretável | O instante original fica nulo; a linha pode permanecer, mas com ressalva. |
| `reported_clock_skew` | Diferença absoluta entre coleta e `requestTime` > 900 s | Divergência sinalizada, sem ajuste automático. |
| `calls_invalid` | `invocations.currentDay` não é inteiro não negativo | Chamadas nulas; taxas ficam indisponíveis. |
| `errors_invalid` / `rejections_invalid` | Contador inválido | Numerador nulo; a taxa correspondente fica indisponível. |
| `mean_ms_invalid` | Média ausente, inválida ou não positiva quando há tráfego | Média nula; não é convertida em zero. |
| `average_tps_invalid` / `peak_tps_invalid` | TPS inválido | Valor nulo e flag. |
| `*_history_invalid` | `previousDays` não é lista ou excede 7 posições | Histórico descartado; baseline e recorrência podem ficar nulos. |
| `*_history_value_invalid` | Item do histórico não é inteiro não negativo | Histórico parcialmente inválido e sinalizado. |
| `history_lengths_differ` | Arrays históricos têm comprimentos diferentes | Contexto incompleto; baseline e recorrência usam apenas valores válidos. |
| `uptime_invalid` / `general_uptime_invalid` | Uptime booleano, não numérico ou fora de [0,1] | Uptime nulo; booleano não vira 100%. |
| `uptime_downtime_conflict` | Uptime 100% com downtime positivo | Inconsistência sinalizada; os valores não são reconciliados. |
| `zero_uptime_without_traffic` | Uptime zero e chamadas zero | Sinal ambíguo; não prova indisponibilidade. |
| `average_tps_above_peak` | TPS médio maior que o pico | Inconsistência de contrato. |
| `counter_above_invocations` | Erros ou rejeições maiores que chamadas | Taxa correspondente fica nula. |
| `zero_mean_with_traffic` | Média zero com chamadas positivas | Média tratada como inválida para elegibilidade. |
| `conflicting_endpoint` | Mesma identidade com valores divergentes na captura | Captura ambígua e incompleta. |
| `page_day_changed` | Páginas da captura cruzaram o dia | Captura incompleta; linhas fora do panorama. |

### Saúde da coleta e continuidade

O resultado da coleta é independente do sucesso de publicação. `health.outcome` classifica cada reporte em `valid`, `empty`, `http_error`, `transport_error` ou `invalid_report`. `collection_health` agrega as fontes da última execução em `healthy`, `partial` ou `unavailable`.

| Estado da coleta | Critério | O que o painel mostra |
|---|---|---|
| `healthy` | Todas as fontes da última tentativa com dados válidos | Panorama pode avançar se houver ciclo completo e dia coerente. |
| `partial` | Pelo menos uma fonte válida, mas não todas | Panorama `all` usa o último ciclo completo; fontes saudáveis podem avançar individualmente. |
| `unavailable` | Nenhuma fonte válida na última tentativa | Panorama anterior é preservado; saúde da tentativa é explícita. |

O panorama é escolhido de trás para frente entre as execuções. Para o escopo `all`, todas as fontes precisam estar válidas; para um recorte de uma fonte, basta ela. A seleção também exige que todas as linhas tenham o mesmo dia e que a contagem normalizada por reporte seja exatamente igual a `records`. Se não houver esse conjunto, o escopo fica sem panorama.

> Exemplo prático: uma execução com seis fontes válidas e duas vazias deixa a saúde `partial`. O panorama `all` continua no último ciclo completo, com a etiqueta **DADOS ANTERIORES**; o recorte de uma fonte saudável pode mostrar o ciclo novo. O agregado não mistura os dois ciclos.

> Atenção: a saúde `unavailable` não apaga o último panorama. Ela também não transforma os valores preservados em novas observações. O monitor prefere a continuidade explícita ao preenchimento artificial de lacunas.

## Modelo de dados

O estado é um JSON versionado com quatro coleções principais: `runs`, `observations`, `incidents` e `latest_rows`. As projeções analíticas são materializadas em Arrow/DuckDB; as estruturas aninhadas de `reports` e `probes` permanecem no JSON e não têm todas as chaves estrangeiras declaradas em SQL. O diagrama abaixo distingue o **estado lógico e a proveniência** das **projeções derivadas**.

### Estado lógico, tentativas e observações

```schema
{
  "title": "Estado lógico: execuções, tentativas, observações e incidentes",
  "cols": 3,
  "colGap": 108,
  "rowGap": 58,
  "entities": [
    {
      "id": "runs",
      "name": "runs",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 ciclo de execução",
      "col": 0,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "name": "observed_at", "type": "utc" },
        { "name": "model_version", "type": "int" },
        { "name": "rules", "type": "object" },
        { "name": "collection_health", "type": "object" }
      ]
    },
    {
      "id": "run_reports",
      "name": "runs[].reports[]",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 run × 1 reporte",
      "col": 1,
      "row": 0,
      "columns": [
        { "key": "PK,FK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "reporter_id", "type": "string" },
        { "name": "status", "type": "int" },
        { "name": "records", "type": "int" },
        { "name": "complete", "type": "bool" },
        { "name": "coverage", "type": "enum" },
        { "name": "issues", "type": "string[]" }
      ]
    },
    {
      "id": "probes",
      "name": "runs[].reports[].probes[]",
      "kind": "json",
      "grain": "Grão: 1 objeto = 1 run × reporte × página × tentativa",
      "col": 2,
      "row": 0,
      "columns": [
        { "name": "capture_attempt", "type": "int" },
        { "name": "page", "type": "int" },
        { "name": "attempt", "type": "int" },
        { "name": "status", "type": "int" },
        { "name": "duration_ms", "type": "number" },
        { "key": "FK", "name": "source_sha", "type": "sha256?" }
      ]
    },
    {
      "id": "observations",
      "name": "observations",
      "kind": "table",
      "grain": "Grão: 1 linha = run × reporter × endpoint",
      "col": 0,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "key": "FK", "name": "reporter_id", "type": "string" },
        { "name": "day", "type": "date" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "mean_ms", "type": "int64?" }
      ]
    },
    {
      "id": "incidents",
      "name": "incidents",
      "kind": "json",
      "grain": "Grão: 1 objeto = entidade × regra × ocorrência",
      "col": 1,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "id", "type": "string" },
        { "name": "entity_id", "type": "string" },
        { "name": "rule", "type": "enum" },
        { "name": "status", "type": "enum" },
        { "name": "severity", "type": "enum" },
        { "name": "recovery_samples", "type": "int" }
      ]
    },
    {
      "id": "latest_rows",
      "name": "latest_rows",
      "kind": "table",
      "grain": "Grão: 1 linha = último contexto útil por endpoint",
      "col": 2,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "name": "reporter_id", "type": "string" },
        { "name": "run_id", "type": "string" },
        { "name": "fresh", "type": "bool" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64?" }
      ]
    }
  ],
  "relations": [
    { "from": "runs", "to": "run_reports", "fromCard": "1", "toCard": "1..N", "label": "cada ciclo tem vários reportes" },
    { "from": "run_reports", "to": "probes", "fromCard": "1", "toCard": "1..N", "label": "tentativas por página" },
    { "from": "runs", "to": "observations", "fromCard": "1", "toCard": "1..N", "label": "linhas normalizadas" },
    { "from": "observations", "to": "incidents", "kind": "lineage", "label": "entity_id + regra" },
    { "from": "probes", "to": "observations", "kind": "lineage", "label": "source_sha + json_path" }
  ],
  "note": "Relações tracejadas representam proveniência ou identidade lógica, não chaves estrangeiras SQL. As estruturas runs[].reports[] e probes[] são aninhadas no JSON de estado."
}
```

### Projeções derivadas e marts

```schema
{
  "title": "Projeções derivadas: contexto atual, tendência e marts",
  "cols": 3,
  "colGap": 112,
  "rowGap": 62,
  "entities": [
    {
      "id": "observations",
      "name": "observations",
      "kind": "table",
      "grain": "Grão: 1 linha = run × reporter × endpoint",
      "col": 0,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "mean_ms", "type": "int64?" }
      ]
    },
    {
      "id": "latest_rows",
      "name": "current_rows",
      "kind": "table",
      "grain": "Grão: 1 linha = último contexto por endpoint",
      "col": 1,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "entity_id", "type": "string" },
        { "name": "reporter_id", "type": "string" },
        { "name": "fresh", "type": "bool" },
        { "name": "source_complete", "type": "bool" },
        { "name": "calls", "type": "int64?" },
        { "name": "mean_ms", "type": "int64?" }
      ]
    },
    {
      "id": "trends",
      "name": "observation_trends",
      "kind": "mart",
      "grain": "Grão: 1 linha = run × reporter",
      "col": 2,
      "row": 0,
      "columns": [
        { "key": "PK", "name": "run_id", "type": "string" },
        { "key": "PK", "name": "reporter_id", "type": "string" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "error_pct", "type": "double?" },
        { "name": "mean_ms", "type": "double?" }
      ]
    },
    {
      "id": "report_summary",
      "name": "report_summary",
      "kind": "mart",
      "grain": "Grão: 1 linha = reporter no ciclo atual completo",
      "col": 0,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "reporter_id", "type": "string" },
        { "name": "endpoints", "type": "int64" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "error_pct", "type": "double?" },
        { "name": "mean_ms", "type": "double?" }
      ]
    },
    {
      "id": "family_summary",
      "name": "family_summary",
      "kind": "mart",
      "grain": "Grão: 1 linha = família no ciclo atual completo",
      "col": 1,
      "row": 1,
      "columns": [
        { "key": "PK", "name": "family", "type": "string" },
        { "name": "endpoints", "type": "int64" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "error_pct", "type": "double?" }
      ]
    },
    {
      "id": "reported_history",
      "name": "reported_history",
      "kind": "json",
      "grain": "Grão: 1 linha = endpoint × posição D−n",
      "col": 2,
      "row": 1,
      "columns": [
        { "name": "entity_id", "type": "string" },
        { "name": "position", "type": "int" },
        { "name": "calls", "type": "int64?" },
        { "name": "errors", "type": "int64?" },
        { "name": "mean_ms", "type": "int64?" }
      ]
    }
  ],
  "relations": [
    { "from": "observations", "to": "trends", "kind": "lineage", "label": "SUM por run + reporter" },
    { "from": "latest_rows", "to": "report_summary", "kind": "lineage", "label": "fresh + source_complete" },
    { "from": "latest_rows", "to": "family_summary", "kind": "lineage", "label": "fresh + source_complete" },
    { "from": "observations", "to": "reported_history", "kind": "lineage", "channel": "bottom", "label": "previousDays do último contexto" }
  ],
  "note": "Marts usam apenas linhas frescas e completas do ciclo atual; o contexto antigo permanece disponível para continuidade, mas não entra nos KPIs correntes. A média dos marts é ponderada por chamadas e não é p95."
}
```

### Identidade, tempo e proveniência

- `entity_id = SHA-256(reporter_id + endpoint)[:24]`. É a chave estável da entidade reportada; o mesmo endpoint em reportes diferentes gera entidades diferentes.
- `run_id` é UTC com sufixo aleatório. Não é a data de referência do banco.
- `day` usa o `HTTP Date` da página que produziu a linha, convertido para `America/Sao_Paulo`; se o Date não for interpretável, usa o instante da aquisição e registra a base.
- `request_time` é o `requestTime` original, sem correção silenciosa. `clock_offset_seconds` mede a diferença para o instante da aquisição.
- `source_sha` identifica o corpo bronze; `json_path` aponta para `$.data[n]` naquele corpo.
- `fingerprint` cobre as seis métricas atuais, uptime, downtime e `previous`; não é um checksum do JSON completo.
- `fresh` significa “mesma execução do último ciclo”, não idade do relógio. Em `observations`, a projeção histórica não deve ser lida como fresca.
- `source_complete` indica cobertura reconciliada da captura, não qualidade de todos os campos.

### Dicionário da projeção Arrow

<details>
<summary>Campos de current_rows e observations</summary>

| Campo | Tipo Arrow | Semântica e nulos |
|---|---|---|
| `run_id` | `string` | Identidade da execução; não é o dia de referência. |
| `entity_id` | `string` | SHA-256 truncado de `reporter_id + endpoint`. |
| `observed_at` | `string` | Instante UTC do início da observação da fonte. |
| `day` | `string` | Dia analítico em `America/Sao_Paulo`, com base registrada em `day_basis`. |
| `reporter_id` | `string` | Identidade do host no catálogo; Nissan e Renault permanecem distintos. |
| `reporter` | `string` | Rótulo operacional da fonte. |
| `endpoint` | `string` | URL/URI declarada pelo banco; nunca chamada pelo monitor. |
| `path` | `string` | Caminho extraído do endpoint, preservando parâmetros de rota. |
| `family` | `string` | Primeiro segmento depois de `/open-banking/`. |
| `calls` | `int64` | `invocations.currentDay`; nulo se inválido. |
| `errors` | `int64` | `errors.currentDay`; sem discriminação de status HTTP. |
| `rejections` | `int64` | `rejections.currentDay`; sem causa implícita. |
| `mean_ms` | `int64` | `averageResponse.currentDay`; média declarada, não p95. |
| `error_pct` | `float64` | `100 × errors ÷ calls` sob denominador válido; nulo caso contrário. |
| `rejection_pct` | `float64` | `100 × rejections ÷ calls` sob denominador válido próprio. |
| `uptime` | `float64` | Razão declarada em [0,1]; a interface multiplica por 100. |
| `source_complete` | `bool` | Cobertura reconciliada da captura que produziu a linha. |
| `fresh` | `bool` | Linha da mesma execução do último ciclo; não mede idade. |

</details>

<details>
<summary>Campos adicionais da observação no estado/JSON</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `day_basis` | string | Relógio que fundamentou `day`; não altera `requestTime`. |
| `source_sha` | SHA-256 | Corpo bronze de origem; os bytes podem expirar da retenção. |
| `json_path` | string | Posição `$.data[n]` no corpo identificado pelo hash. |
| `request_time` | string/nulo | `requestTime` original, sem correção automática. |
| `clock_offset_seconds` | número/nulo | `observed_at − requestTime`; limiar configurável. |
| `average_tps` / `peak_tps` | int64/nulo | TPS atual declarado, não calculado a partir de chamadas. |
| `general_uptime` | razão/nulo | `generalUptimeRate`, independente do uptime do endpoint. |
| `downtime_seconds` / `general_downtime` / `scheduled_outage` | int64/nulo | Segundos declarados em `partialDowntime`, `generalDowntime` e `scheduledOutage`. |
| `previous` | objeto de arrays | Até sete posições por métrica; D−1 primeiro. |
| `baseline_mean_ms` | número/nulo | Mediana das médias diárias anteriores positivas. |
| `recurrent_days` | inteiro | Dias anteriores com chamadas ≥ 100 e erro ≥ 5%. |
| `quality` | array de strings | Ocorrências de contrato/consistência; não reescreve o valor. |
| `fingerprint` | SHA-256 | Seis métricas atuais, uptime, downtime e `previous`. |
| `interval_from` / `interval_to` | UTC/nulo | Instantes das duas observações comparadas. |
| `interval_seconds` | número/nulo | Diferença entre os instantes; tempo não crescente invalida. |
| `interval_calls` / `interval_errors` / `interval_rejections` | int64/nulo | Diferenças aceitas dos cumulativos. |
| `interval_error_pct` / `interval_rejection_pct` | percentual/nulo | Taxas dos deltas aceitos. |
| `interval_state` | enum | Motivo da comparação aceita ou suspensa. |
| `interval_error_state` / `interval_rejection_state` | enum | Comparabilidade de cada numerador com chamadas. |

</details>

<details>
<summary>Tentativas HTTP e pacotes de proveniência</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `capture_attempt` | inteiro | Captura a partir de 1; identifica repetição após vazio, separada do retry HTTP. |
| `page` / `attempt` | inteiro | Página solicitada e tentativa HTTP a partir de 1. |
| `observed_at` | UTC | Início da tentativa HTTP. |
| `url` | URL | Admin e parâmetros solicitados; redirecionamentos não são seguidos. |
| `status` | inteiro | HTTP recebido; 0 quando não houve resposta HTTP. |
| `duration_ms` | número | Tempo até leitura do corpo ou erro; não é latência do serviço. |
| `http_date` | string/nulo | Cabeçalho Date recebido, sem substituir `requestTime`. |
| `source_sha` / `bytes` | hash/inteiro | Corpo completo preservado e tamanho; podem faltar em transporte/limite. |
| `error` | string/nulo | Condição final da tentativa; tentativas transitórias permanecem. |
| `data_status` | enum | Resultado da captura: `valid`, `empty`, `http_error`, `transport_error` ou `invalid_report`. |

</details>

<details>
<summary>Incidentes, evidência e recuperação</summary>

| Campo | Tipo lógico | Semântica |
|---|---|---|
| `id` | hash truncado | Entidade + regra + run de abertura; reabertura cria outro ID. |
| `entity_id` / `rule` | strings | Entidade do serviço ou `source:<reporter_id>`, mais o nome da regra. |
| `reporter_id` / `reporter` / `endpoint` | string/nulo | Identidade estável, rótulo atual e endpoint; coleta não tem endpoint de serviço. |
| `opened_at` / `opened_run` | UTC / ID | Primeira detecção observada. |
| `last_seen` | UTC | Última detecção acima do limiar. |
| `evaluated_at` | UTC | Última avaliação conclusiva de detecção/recuperação. |
| `samples` | inteiro | Total de detecções da ocorrência. |
| `consecutive_samples` | inteiro | Sequência atual de detecções. |
| `confirmed` | booleano | A sequência atingiu `confirmation_samples`; não prova novos erros. |
| `recovery_samples` | inteiro | Amostras avaliáveis consecutivas abaixo do limiar. |
| `status` / `severity` | enum | `open`/`recovering`/`resolved` e `attention`/`critical`. |
| `evidence` | string | Numerador, denominador ou contexto da última detecção. |
| `resolved_at` | UTC opcional | Registrado apenas após completar `recovery_samples`. |

</details>

## Consulta e consumo dos dados

Há quatro formas de consumir a entrega, cada uma com um grão diferente. A escolha depende da pergunta: o painel responde à triagem; o `dashboard.json` entrega o recorte publicado; o Parquet serve à análise histórica; o estado/Releases permitem reconstruir o ciclo operacional.

| Pergunta | Fonte indicada | Cuidado principal |
|---|---|---|
| O que está aberto agora? | Dashboard, seção 02, ou `dashboard.json` → `incidents` | O payload contém resolvidos dos últimos três dias; o estado preserva 30 dias. |
| Qual endpoint concentra erros no dia? | `dashboard.json` → `panoramas.all.rows` ou `data/gold/current_rows.parquet` | Usar apenas linhas frescas e completas para o ciclo atual. |
| Como a taxa evoluiu nas nossas coletas? | `data/gold/observation_trends.parquet` | Cada ponto é um acumulado; não somar entre runs. |
| Quais foram as tentativas HTTP de uma extração? | `dashboard.json` → `runs[].reports[].probes[]` | Duração mede a chamada ao Admin, não o serviço declarado. |
| Como reconstruir um estado anterior? | Release aprovada → `restore` | Restaurar em diretório vazio; conferir checksum e manifesto. |

### Receitas DuckDB

As receitas abaixo pressupõem `data/gold/current_rows.parquet` e `data/gold/observation_trends.parquet` gerados pelo build local. Ajuste o caminho conforme o ambiente.

```sql
-- Ranking de endpoints no ciclo atual, com taxas apenas em denominadores válidos
SELECT reporter,
       path,
       calls,
       errors,
       ROUND(100.0 * errors / calls, 2) AS error_pct,
       mean_ms
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh
  AND source_complete
  AND calls > 0
  AND errors IS NOT NULL
  AND errors <= calls
ORDER BY errors DESC, calls DESC
LIMIT 25;
```

```sql
-- Série de tendência por reporte, sem somar runs diferentes
SELECT observed_at,
       reporter_id,
       calls,
       errors,
       ROUND(error_pct, 2) AS error_pct,
       ROUND(mean_ms, 1) AS mean_ms
FROM read_parquet('data/gold/observation_trends.parquet')
WHERE source_complete
ORDER BY observed_at, reporter_id;
```

```sql
-- Resumo por família no ciclo atual
SELECT family,
       endpoints,
       calls,
       errors,
       ROUND(error_pct, 2) AS error_pct
FROM read_parquet('data/gold/family_summary.parquet')
ORDER BY errors DESC NULLS LAST;
```

```sql
-- Média ponderada por reporte, explicitando o denominador válido
SELECT reporter_id,
       SUM(mean_ms * calls) FILTER (WHERE mean_ms > 0 AND calls > 0)
         / NULLIF(SUM(calls) FILTER (WHERE mean_ms > 0 AND calls > 0), 0) AS weighted_mean_ms,
       SUM(calls) FILTER (WHERE mean_ms > 0 AND calls > 0) AS weighted_calls
FROM read_parquet('data/gold/current_rows.parquet')
WHERE fresh AND source_complete
GROUP BY reporter_id
ORDER BY reporter_id;
```

### Consumir o payload publicado

O `dashboard.json` (e o `data.js`, que contém o mesmo objeto em `window.ADMIN_DATA`) publica apenas a janela de 72 horas, além do contexto necessário para incidentes e panoramas preservados. As chaves de topo são:

| Chave | Conteúdo | Grão / uso |
|---|---|---|
| `meta` | Versão, run, instantes, janelas, cron, contagens retidas | Contexto da publicação. |
| `reporters` | Catálogo dos oito reportes | Dimensão de filtro e rótulos. |
| `latest` | Último contexto útil por endpoint | Ranking, tabela e continuidade. |
| `runs` | Execuções visíveis na janela | Monitor de execuções e coleta. |
| `points` | Pontos das observações próprias | Detalhe do endpoint. |
| `observation_trends` | Agregação por run × reporte | Gráfico de tendência. |
| `reported_history` | D−n declarado pelo banco | Histórico da origem, não nossas coletas. |
| `incidents` | Incidentes abertos, em recuperação e resolvidos recentes | Triagem e evidência. |
| `panoramas` | Um snapshot por escopo (`all` e cada reporte) | KPIs com um único ciclo/dia. |
| `collection_health` | Saúde da última tentativa e por fonte | Diagnóstico de coleta. |
| `rules` | Configuração vigente | Transparência dos limiares. |

```python
import json
from pathlib import Path

payload = json.loads(Path("site/dashboard.json").read_text(encoding="utf-8"))
panorama = payload["panoramas"]["all"]
for row in sorted(panorama["rows"], key=lambda r: r["errors"] or 0, reverse=True)[:10]:
    print(row["reporter"], row["path"], row["calls"], row["errors"], row["error_pct"])
```

> Regra de negócio: os agregados entre reportes podem conter serviços compartilhados. Somar reportes não garante transações únicas entre instituições. A leitura correta é operacional, não uma contagem de eventos distintos do Open Finance.

> Atenção: `reported_history` é o histórico declarado pelo banco dentro do payload atual; ele pode ser revisado pela origem e não representa as nossas coletas passadas. Nossas observações estão em `points` e `observation_trends`.

## Operação local

O projeto requer **Python 3.11 ou 3.12, 64 bits**. Node 22 é necessário apenas para validar o JavaScript e rodar os testes do dashboard; o produto publicado não precisa de servidor Node. O ambiente virtual e as dependências ficam isolados no repositório.

### Preparação

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Em Linux/macOS, troque `.\.venv\Scripts\python.exe` por `.venv/bin/python`. O `pyproject.toml` declara as dependências de runtime e o entry point `admin-metrics`.

### Comandos

| Comando | Efeito | Quando usar |
|---|---|---|
| `python -m admin_metrics.cli collect` | Coleta nova amostra, aplica regras, gera marts/HTML e grava o estado | Uso local ou bootstrap. |
| `python -m admin_metrics.cli build` | Republica o estado existente sem criar nova observação | Regerar site/manual após mudança de código. |
| `python -m http.server 8766 --bind 127.0.0.1 --directory site` | Serve o site local | Conferência no navegador. |
| `python -m pytest -q` | Executa a suíte Python | Antes de commit ou publicação. |
| `node --check src/admin_metrics/web/app.js` | Valida sintaxe do JavaScript | Antes de commit. |
| `node --test tests/test_dashboard.cjs` | Executa os testes do dashboard | Antes de commit. |

Os parâmetros globais do CLI são `--root data`, `--output site` e `--config config`. O `collect` cria uma nova execução; o `build` reutiliza a última e não adiciona observação. Não execute dois escritores no mesmo root: o lock `data/.writer.lock` impede concorrência, mas não é um coordenador distribuído.

### O que esperar

- `collect` imprime um JSON com `run_id`, número de linhas e número de fontes.
- `data/state.json` é gravado apenas ao final; `data/gold/` recebe os cinco Parquet; `site/` recebe o dashboard, `dashboard.json` e o manual.
- `site/assets/<hash>/` contém a versão imutável dos assets; a raiz referencia o hash atual.
- O console registra um evento por reporte com status, registros, `data_status`, retries de vazio e issues.
- O HTML e os manuais funcionam offline; o dashboard precisa da pasta `site/` inteira (assets e `data.js`).

### Diagnóstico rápido

| Sintoma | Causa provável | Ação |
|---|---|---|
| `Escritor ativo ou lock abandonado` | Outro processo está escrevendo ou o lock ficou após interrupção | Confira o processo; remova `data/.writer.lock` somente após garantir que não há escritor. |
| `Nenhuma observação; execute collect primeiro` | `build` sem `state.json` ou estado vazio | Execute `collect` para criar a primeira observação. |
| `URL fora do catálogo permitido` | Catálogo com host, esquema, porta, query ou caminho inválido | Corrija `config/reporters.json`; não contorne a validação. |
| `Regras: parâmetros ausentes ou desconhecidos` | `config/rules.json` incompleto ou com chave extra | Restaure o conjunto exato de parâmetros e respeite a ordem dos limiares. |
| `Modelo de estado incompatível` | `model_version` fora de 1, 2 ou 3 | Use um estado compatível; não edite o modelo para “passar”. |
| Dashboard sem estilos ou dados | Pasta `site/` incompleta | Use o diretório `site` inteiro, não apenas `index.html`. |
| HTTP 403 em uma fonte | Acesso recusado ao Admin | Registre o diagnóstico; não tente contornar bloqueio. |

> Atenção: `collect` faz chamadas reais aos oito hosts do catálogo. Em uma estação de trabalho, isso consome rede e pode ser limitado pela instituição. O comando é somente leitura e não chama endpoints de clientes.

> Limitação: o lock não verifica se o PID ainda está vivo. Um lock abandonado após queda do processo precisa ser conferido e removido manualmente; o sistema não o recicla sozinho.

## Publicação, retenção e recuperação

A publicação remota é feita pelo workflow **Monitorar Admin e publicar Pages**. Ele tem três jobs: `build` (testes, restore, coleta/build, upload do Pages e candidato), `deploy` (publicação) e `confirm` (promoção ou descarte da Release). O grupo de concorrência `admin-state-and-pages` impede que duas execuções disputem estado e Pages.

| Gatilho | `refresh_data` efetivo | Comportamento |
|---|---|---|
| `schedule` (`17 * * * *` UTC) | `true` | Restaura o estado aprovado, coleta nova amostra, publica e confirma candidato. |
| `workflow_dispatch` com input marcado | `true` | Mesmo fluxo do cron, com URL de execução registrada. |
| `workflow_dispatch` com input desmarcado | `false` | Republica o estado aprovado sem nova observação. |
| `push` em `main` | `false` | Republica sem coletar; se não houver estado, faz bootstrap com coleta. |

### Ciclo da Release

1. O workflow baixa a Release aprovada mais recente e executa o restore.
2. Se houver coleta, o estado é aplicado, o build gera os artefatos e um ZIP com `state.json`, `manifest.json` e os bronzes dos dois ciclos recentes é criado.
3. Uma Release `state-<run>-<attempt>` é criada como **draft**, com corpo JSON contendo `data_run_id`, `workflow_run_id`, `source_sha` e `purpose=approved-monitor-state`; `state.zip` e `SHA256SUMS` são anexados.
4. O Pages é publicado. O job `deploy` precisa estar `completed`/`success` para o job `confirm` promover a Release.
5. A promoção adiciona um `deployment-receipt.json` e publica a Release; as aprovadas além das duas mais recentes são removidas.
6. Se o build falhar, o candidato é descartado. Se o deploy falhar, o `confirm` também descarta o draft.

> Atenção: Pages e Releases não formam uma transação distribuída. Um deploy aprovado cujo job de confirmação falhe pode deixar um candidato em draft. Consulte o ID do run no dashboard e o job antes de recuperar; não faça fallback silencioso para um estado corrompido.

### Retenção

| Escopo | Janela / limite | Onde vive |
|---|---|---|
| Estado normalizado | 30 dias, cerca de 720 ciclos horários | `state.json` e Releases |
| Observações e tentativas | 30 dias | `state.json`; o payload publica 72 horas |
| Bronze local | Dois ciclos recentes | `data/bronze/` e pacote `state.zip` |
| Releases aprovadas | Duas mais recentes | GitHub Releases |
| Incidentes resolvidos | 30 dias | `state.json`; o payload mostra os resolvidos recentes |
| Incidentes abertos | Persistem até avaliação conclusiva | `state.json` |
| Séries do dashboard | 72 horas | `dashboard.json` e gráficos |

Cada pacote aprovado tem sua própria janela. A união do pacote atual com o anterior pode conter bytes de três ciclos, mas o pacote individual mantém dois. Hashes históricos permanecem nas observações; os bytes bronze mais antigos podem ter expirado. O restore não sobrescreve um estado existente e não troca automaticamente o estado remoto atual.

### Restauração explícita

Com `gh` autenticado e `GH_REPO=alebitencourtx/admin-metrics`, em um diretório de dados vazio:

```powershell
python scripts/cloud_pipeline.py restore --tag state-<run>-<tentativa>
python -m admin_metrics.cli build
```

O restore verifica o checksum externo (`SHA256SUMS`), os hashes internos do manifesto, a presença de `state.json` e dos bronzes referenciados, nomes permitidos, duplicatas e limites de expansão. Se algo falhar, ele não altera o destino. Se a gravação do `state.json` falhar após os bronzes, os arquivos gravados na tentativa são removidos e o restore pode ser repetido.

### Matriz de recuperação

| Sintoma | Causa provável | Ação de recuperação |
|---|---|---|
| Checksum externo inválido | Download truncado ou `SHA256SUMS` de outro pacote | Baixar novamente os dois assets da mesma Release; não editar o checksum. |
| Checksum interno inválido | ZIP corrompido ou manifesto divergente | Descartar o download e repetir; se persistir, usar a Release anterior. |
| `Restaure em diretório de dados vazio` | Destino já tem `state.json` ou bronze | Escolher outro root; o restore não sobrescreve. |
| `Referências bronze não conciliadas` | Pacote não contém todos os bronzes recentes | Não forçar; selecionar um pacote íntegro. |
| Deploy falhou | Erro de Pages, permissão ou artefato | O workflow descarta o draft; corrigir e reexecutar. |
| Deploy concluiu, confirmação falhou | Falha no job `confirm` ou na API de Releases | Verificar o run e o draft; promover manualmente só com recibo de deploy. |
| Build falhou antes do deploy | HTML, SQL, schema ou teste | O site/estado anteriores permanecem; corrigir e reexecutar. |
| Cron atrasou ou não rodou | Agendamento *best effort* do GitHub | Usar `workflow_dispatch` com `refresh_data`; conferir a idade no painel. |
| Fonte vazia ou 403 | Origem sem dados ou acesso recusado | Preservar o diagnóstico; não inventar zero nem contornar bloqueio. |
| Bronze antigo ausente | Retenção de dois ciclos | Usar o pacote aprovado correspondente ou aceitar a limitação de reprocessamento. |

> Regra de negócio: o workflow só publica uma Release como aprovada após um job `deploy` comprovadamente concluído com sucesso no workflow correspondente. Um recibo sem essa prova não é suficiente para promoção.

## Limitações e interpretação

Esta é uma documentação **as-is**: descreve o que está implementado, não um plano de modernização. As limitações abaixo afetam a interpretação dos números e devem ser lidas antes de qualquer conclusão executiva.

| Pergunta indevida | Por que o dado não responde | Leitura correta |
|---|---|---|
| “Qual é o p95 da resposta?” | O payload traz `averageResponse`, uma média declarada; não há percentis. | Usar “média declarada”; não chamar de p95 nem inferir cauda. |
| “Quais status HTTP causaram os erros?” | `errors` é um contador agregado, sem detalhamento por código. | Dizer “erros declarados”; investigar a origem separadamente. |
| “As rejeições são 429?” | `rejections` não identifica causa nem código. | Dizer “rejeições declaradas”; não atribuir throttling sem evidência externa. |
| “O Admin retornou 403, então o serviço está fora.” | 403 significa acesso recusado ao observador; não prova indisponibilidade dos demais serviços. | Separar falha de coleta de disponibilidade do serviço reportado. |
| “Não há endpoint, então não há oferta.” | Ausência no reporte pode refletir escopo, paginação ou decisão da origem. | Não inferir ausência de oferta a partir do monitor. |
| “A taxa do dia é a taxa das últimas 24 horas.” | Contadores são cumulativos do dia e podem ser parciais; o dia analítico é uma convenção. | Usar o dia de referência explícito e os deltas válidos. |
| “A soma dos oito reportes é o total do Open Finance.” | Reportes podem compartilhar serviços e não há garantia de transações únicas. | Ler como agregado operacional, não como contagem única de eventos. |
| “O cron horário garante alerta em até uma hora.” | O GitHub Actions agenda por melhor esforço e pode atrasar ou desabilitar schedules. | Conferir a idade real e usar execução manual quando necessário. |
| “Duas detecções provam novos erros no intervalo.” | A confirmação mede persistência do sinal, inclusive com contadores cumulativos sem mudança. | Dizer “sinal persistente”; não inferir novos eventos. |
| “O painel é um laudo de conformidade.” | Os critérios são analíticos, configuráveis e não regulatórios. | Usar como observabilidade; não como certificação. |
| “O bronze antigo permite reprocessar todo o histórico.” | O pacote mantém dois ciclos recentes; os bytes mais antigos podem ter expirado. | Reprocessar apenas o que está no pacote/retenção disponível. |
| “A documentação prova que a produção está saudável.” | O documento descreve implementação e um snapshot local; não é telemetria ao vivo. | Consultar o dashboard e as execuções para o estado atual. |

> Limitação: a média ponderada é uma aproximação agregada de médias declaradas por endpoint. Ela não recupera a distribuição, não corrige a semântica da origem e não substitui uma medição sintética.

> Atenção: o snapshot local usado como exemplo contém 276 identidades e uma execução; ele não deve ser citado como situação atual da produção. A série publicada começa na primeira coleta remota e não preenche retroativamente horários não observados.

## Decisões e racional

As decisões abaixo descrevem escolhas implementadas. Quando o motivo histórico não está registrado no código ou na documentação mantida, o texto evita inventar justificativa; descreve o efeito atual da escolha.

| Decisão implementada | Efeito atual |
|---|---|
| Catálogo fechado de oito reportes, sem descoberta dinâmica de hosts | Reduz superfície de rede e impede chamadas a endpoints não autorizados. |
| Apenas o caminho Admin é consultado | O monitor observa o que o banco declara, sem acessar clientes, consentimentos ou pagamentos. |
| Estado em JSON + Releases, sem banco permanente | O runner é descartável e o histórico não entra no Git a cada ciclo. |
| Um escritor por lake com lock | Evita corrida local entre coleta e build; não é coordenação distribuída. |
| Bronze endereçado por SHA-256 | Permite auditar o corpo exato e detectar corrupção. |
| Estado normalizado de 30 dias e payload de 72 horas | Preserva histórico para regras e mantém o Pages leve. |
| Um ciclo completo e um dia por panorama | Evita misturar fontes, ciclos ou dias diferentes nos KPIs. |
| Nulos explícitos, sem conversão de ausência em zero | Mantém a diferença entre “não medido”, “inválido” e “zero”. |
| Dia analítico pelo HTTP Date de cada página | Reduz o risco de atribuir uma linha ao dia errado na virada. |
| Deltas somente com mesma entidade, dia e cobertura completa | Impede somar snapshots cumulativos ou comparar dias diferentes. |
| Incidentes com confirmação e recuperação por amostras | Evita abrir/resolver com um único ponto ambíguo. |
| Arrow/DuckDB/Parquet em vez de servidor analítico | A escala atual cabe em processo único e dispensa infraestrutura contratada. |
| HTML estático sem CDN ou framework SPA | O dashboard e os manuais funcionam offline, com baixo custo operacional. |
| Release draft + recibo de deploy | Só promove estado depois de publicação comprovada; reduz estado “aprovado” sem site. |
| Manuais v2 completos e resumidos lado a lado | Atendem leitura executiva e aprofundamento técnico sem duplicar facts contraditórios. |

> Limitação: a arquitetura não oferece HA, autenticação corporativa, RBAC, SLA, alerta externo ou operação contínua. A ausência desses controles é uma característica do escopo atual, não uma conclusão de suficiência para uso regulatório.

## Glossário e referências

| Termo | Definição |
|---|---|
| **Admin** | API de métricas operacionais do Open Finance consultada em `/open-banking/admin/v2/metrics`. |
| **Reporte** | Cadastro de um host/instituição no catálogo, com id, rótulo, empresa, CNPJ e URL. |
| **Run** | Uma execução do pipeline, identificada por `run_id` UTC; contém reportes, observações e saúde. |
| **Probe** | Uma tentativa HTTP de uma página, com status, duração, Date, bytes, hash e erro. |
| **Bronze** | Corpo HTTP exato preservado por SHA-256 em `data/bronze/`. |
| **Gold** | Projeções tipadas e marts materializados em DuckDB/Parquet. |
| **Observação** | Uma linha normalizada de run × reporte × endpoint. |
| **Entidade** | Identidade técnica `entity_id` derivada de `reporter_id + endpoint`. |
| **Panorama** | Snapshot de um ciclo completo e um único dia para um escopo (`all` ou um reporte). |
| **Dia de referência** | Dia analítico derivado do HTTP Date/instante de coleta em `America/Sao_Paulo`. |
| **Delta** | Diferença válida entre contadores cumulativos da mesma entidade e dia. |
| **Incidente** | Ocorrência de uma regra para uma entidade, com severidade, evidência e recuperação. |
| **Confirmação** | Persistência do sinal por `confirmation_samples` detecções consecutivas. |
| **Recuperação** | `recovery_samples` amostras avaliáveis consecutivas abaixo do limiar. |
| **Fresh** | Linha da mesma execução do último ciclo; não mede idade do relógio. |
| **Média ponderada** | `Σ(mean_ms × calls) ÷ Σ(calls)` para linhas válidas com tráfego. |
| **p95** | Percentil 95; não é calculado nem publicado por este monitor. |
| **Cobertura reconciliada** | Contagem de identidades igual ao total declarado, sem conflitos impeditivos. |
| **DADOS ANTERIORES** | Rótulo do panorama preservado de um ciclo anterior; não são pontos novos. |

### Referências primárias

- [Especificação oficial Admin 2.0.1](https://raw.githubusercontent.com/OpenBanking-Brasil/openapi/main/swagger-apis/admin/2.0.1.yml) — contrato de entrada e semântica dos campos declarados.
- [Diretório oficial de participantes](https://data.directory.openbankingbrasil.org.br/participants) — base da conferência de URL/CNPJ; o comprovante local registra data e hash.
- [Documentação do GitHub Actions sobre schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) — natureza *best effort* da agenda.
- [Dashboard publicado](https://alebitencourtx.github.io/admin-metrics/) — leitura do estado atual e dos manuais.
- [Repositório público](https://github.com/alebitencourtx/admin-metrics) — código, workflows, configuração e histórico de revisões.
- [Workflow de coleta e publicação](https://github.com/alebitencourtx/admin-metrics/actions/workflows/pages.yml) — execuções, logs e recibos.

### Arquivos locais desta documentação

| Caminho | Conteúdo |
|---|---|
| `README.md` | Visão geral e instruções resumidas do projeto. |
| `config/reporters.json` | Catálogo fechado dos oito reportes. |
| `config/rules.json` | Limiares e parâmetros analíticos vigentes. |
| `config/catalog-evidence.json` | Comprovante da conferência no Diretório. |
| `src/admin_metrics/` | Coleta, análise, armazenamento, build, CLI e web. |
| `src/admin_metrics/marts.sql` | Definições dos marts analíticos. |
| `.github/workflows/pages.yml` | Coleta, publicação e confirmação do estado. |
| `.github/workflows/ci.yml` | Matriz de testes Linux/Windows e Python 3.11/3.12. |
| `tests/` | Cenários de análise, coleta, panorama, pipeline, cloud e dashboard. |
| `docs_v2/` | Manuais v2 completo e resumido e seus arquivos de autoria. |

> Limitação: o manual é gerado com `project-html-docs` e não executa o projeto. A verificação estrutural não certifica cardinalidades, significado de negócio, frescor ou status de produção; esses pontos foram checados na leitura das fontes e devem ser reconferidos a cada revisão.
