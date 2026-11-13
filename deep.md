# Auditoria do Admin Metrics

**Data:** 13/11/2026  
**Escopo executado:** leitura dos módulos Python, `app.js`, configurações, workflows e testes; execução de **95 testes Python + 10 testes Node** (todos aprovados); inspeção do estado local e do payload publicado; reprodução de cenários em diretórios temporários. **Nenhum arquivo do projeto foi alterado durante a auditoria original.**

## Resumo executivo

A base é bem organizada e madura: separa tentativa de coleta de métricas válidas, não transforma ausência em zero, preserva panorama coerente e tem boa cobertura de falhas. Os problemas mais relevantes estão em **casos de borda de data, compatibilidade de estado antigo, recuperação parcial de pacote e seleção de Release**.

## 1. Bugs confirmados

| ID | Severidade | Achado | Evidência e impacto | Correção sugerida |
|---|---|---|---|---|
| **B1** | **P1** | O dia analítico de todas as linhas usa o `HTTP Date` da **última página**, não o da página onde cada linha apareceu. | [collect.py:83](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/collect.py:83) atualiza `result["http_date"]` a cada página; [analysis.py:40](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:40) usa um único `report["http_date"]` para normalizar tudo. Reproduzi página 1 com Date `02:59 GMT` (23:59 em São Paulo) e página 2 com `03:01 GMT`: **as duas linhas ficaram no dia 2026-11-10**, embora a primeira pertencesse a 2026-11-09. Afeta deltas, panorama e o "dia de referência" quando a paginação cruza a meia-noite ou há retries lentos. | Guardar `http_date` (ou `day`) por linha no `capture`, normalizar linha a linha e marcar `page_day_changed`/captura incompleta se as páginas cruzarem o dia. Adicionar teste específico. |
| **B2** | **P1** | `pipeline.run` quebra com `KeyError: 'source_sha'` se um probe legado não tiver a chave. | [pipeline.py:41](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/pipeline.py:41) usa `p['source_sha']`; [archive.py:27](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:27) já usa `.get` no mesmo conceito. Reproduzi removendo a chave de um probe: `run(refresh=False)` falhou com `KeyError`. Estados importados/legados podem bloquear republicação e recuperação. | Trocar por `p.get('source_sha')` e validar/filtrar probes antes do GC. Teste de compatibilidade. |
| **B3** | **P1** | Restore parcial deixa bronze gravado sem `state.json` e impede nova tentativa. | [archive.py:79](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:79) exige diretório vazio; [archive.py:109-113](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:109) grava bronze antes do ponteiro final. Simulei falha ao gravar `state.json`: o destino ficou com bronze, sem estado; o segundo restore retornou "Restaure em diretório de dados vazio". | Gravar em diretório de staging e mover atomicamente, ou apagar os arquivos já gravados em caso de falha. Documentar limpeza se a abordagem atual for mantida. |
| **B4** | **P1** | `approved()` aceita qualquer Release publicada com tag `state-*`, inclusive sem `purpose`/recibo válido. | [cloud_pipeline.py:24-25](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/scripts/cloud_pipeline.py:24) filtra só tag/draft/prerelease; [cloud_pipeline.py:70-72](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/scripts/cloud_pipeline.py:70) baixa a primeira. Reproduzi uma release `state-999-1` com `purpose: unrelated` sendo escolhida antes da release válida. `promote` valida o body em [cloud_pipeline.py:96-103](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/scripts/cloud_pipeline.py:96), mas o restore não. | Validar `body.purpose == approved-monitor-state`, `data_run_id`, `workflow_run_id` e a presença de `state.zip`/`SHA256SUMS` antes de selecionar; opcionalmente exigir o recibo de deploy. Teste com releases fora do ciclo. |
| **B5** | **P2** | `coverage_reconciled` pode ficar `true` com captura marcada `complete=false` e `coverage=invalid_records`. | [analysis.py:289-298](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:289) marca `complete=False` ao filtrar endpoint inválido, mas copia `coverage_reconciled` do relatório original. Reproduzi: `complete=False`, `coverage=invalid_records`, `coverage_reconciled=True`, `data_status=invalid_report`. Consumidores que confiam em `coverage_reconciled` podem interpretar a captura como conciliada. | Recalcular `coverage_reconciled` após o filtro, ou forçar `False` quando houver `invalid_endpoint_record`/rejeição de linha. |
| **B6** | **P2** | O limite de 10.000 identidades por fonte não é efetivamente respeitado. | [collect.py:119-120](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/collect.py:119) dispara `record_limit`, mas [collect.py:143](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/collect.py:143) devolve todo o dicionário. Reproduzi 11 páginas de 1.000 linhas: **11.000 rows** retornadas com `issues=['record_limit']` e `complete=false`. Isso pode inflar observações e contraria o limite documentado. | Parar antes de ultrapassar o teto, truncar explicitamente ou rejeitar a captura com contagem limitada; registrar `record_limit` e o total descartado. |
| **B7** | **P2** | Uptime booleano é aceito como `1.0`. | [analysis.py:90-95](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:90) converte com `float()` sem validar tipo; `True` vira `1.0`. Contadores em [analysis.py:25-26](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:25) rejeitam booleanos. Reproduzi `uptimeRate: true` resultando em 100% sem flag de tipo. | Exigir `str` numérica ou número real, rejeitando `bool`; alinhar ao contrato dos contadores. |

## 2. Riscos e inconsistências adicionais

- **Panorama antigo com detalhe vazio:** o payload publica `points` apenas dos runs visíveis na janela de 72h ([build.py:58-60](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/build.py:58), [build.py:93](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/build.py:93)). O panorama pode ser de até 30 dias ([panorama.py:24](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/panorama.py:24)). Ao abrir um ranking desse panorama antigo, `detail` usa `D.points` e mostra "Ainda não há amostras válidas" ([app.js:152-160](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:152)), quando na verdade a amostra existe, mas está fora da janela. **Sugestão:** rotular "fora da janela de 72h" ou incluir pontos do snapshot selecionado.
- **Incidentes resolvidos:** o estado guarda resolvidos por 30 dias ([analysis.py:319](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:319)), mas o payload só inclui resolvidos dos últimos 3 dias ([build.py:71-74](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/build.py:71)). A opção "Todos, incluindo resolvidos" ([app.js:64](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:64)) não deixa claro que é só a janela de 3 dias. Além disso, `resolved_at` não aparece na tabela. **Sugestão:** rotular a janela e exibir a data de resolução.
- **`pack` não é atômico:** [archive.py:68-73](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:68) escreve o ZIP direto no destino e só depois grava o SHA256SUMS. Uma queda no meio deixa ZIP parcial. O CI provavelmente não sobe o arquivo, mas a recuperação local pode ser confusa. **Sugestão:** escrever em temporário e `os.replace`.
- **Memória no transporte:** `pack` e `restore` leem o ZIP inteiro para calcular SHA ([archive.py:73](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:73), [archive.py:84](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/archive.py:84)), e `restore` mantém state + bronzes em memória. Com state de ~300 MiB, o pico pode ficar alto. **Sugestão:** hash em streaming e limites menores por entrada, se possível.
- **Versão de modelo não é validada:** o envelope do estado é versão 1, mas `model_version` é gravado sem checagem de compatibilidade ([analysis.py:284](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/analysis.py:284)). Um estado antigo pode ser misturado com código novo sem migração explícita. **Sugestão:** declarar `model_version` suportado no restore/build e falhar com mensagem clara.
- **Configuração de reporter validada só por `id`:** [pipeline.py:19](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/pipeline.py:19) verifica vazio/duplicado. Campos ausentes ou URL inválida podem abortar toda a coleta via `asyncio.gather`, em vez de gerar erro de configuração claro. **Sugestão:** validar schema completo do catálogo no início.
- **URLs fixas no frontend:** [app.js:133](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:133) só aceita links do repositório `alebitencourtx/admin-metrics`, e [index.html:15-16](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/index.html:15) fixa o repositório e o OpenData. Em fork/renomeação, os links somem ou apontam para o lugar errado. **Sugestão:** incluir `repository_url`/`actions_url` no payload.
- **Contagem de incidentes pode divergir:** `nav-count` e o título executivo usam `live` sem filtro de `reporter_id` ([app.js:50](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:50)); a tabela filtra por `allowed` ([app.js:65-66](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:65)). Incidentes legados sem `reporter_id` podem aparecer na contagem e não na lista.
- **Busca sem normalização de acentos:** [app.js:97](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:97) só faz `toLowerCase()`. Buscar "Aymore" não encontra "Aymoré". **Sugestão:** normalizar diacríticos como o manual já faz.
- **Filtros não persistem na URL:** reporte, busca, família, ordenação e página ficam só em memória. Não é possível compartilhar um recorte. **Sugestão:** sincronizar com `location.hash`/query.
- **Assets antigos acumulam localmente:** [build.py:105-110](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/build.py:105) cria `assets/<hash>` e nunca remove os anteriores. No CI o `site` nasce vazio, mas no uso local o diretório cresce indefinidamente. **Sugestão:** podar assets fora do hash atual após publicar.
- **Diálogo de execução não fecha no backdrop:** só o diálogo de endpoint tem esse tratamento ([app.js:171-172](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:171)); o de execução só fecha por botão/ESC.
- **Rótulo "Falha" para HTTP 200 inválido:** cartões de fonte mostram "Falha" mesmo quando houve HTTP 200 com reporte inválido ([app.js:61](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/app.js:61)). "Reporte inválido" seria mais preciso.

## 3. Oportunidades de melhoria, por área

### Dados e contratos

- Propagar `http_date` por página/linha e detectar mudança de dia dentro da captura (B1).
- Aplicar o teto de 10.000 registros de verdade (B6).
- Rejeitar booleanos/strings inválidas em uptime (B7).
- Detectar mudança de `totalRecords`/`totalPages` entre páginas, não só páginas fantasma.
- Registrar `run.duration_seconds`, contagem de páginas e bytes totais para diagnóstico operacional.
- Validar `model_version` e versão do envelope no restore/build.

### Resiliência e operação

- Staging + commit atômico no restore (B3).
- Validar `purpose`/recibo em `approved()` (B4).
- ZIP de pacote escrito em temporário + `os.replace`.
- Lock com verificação de PID/processo vivo (hoje abandonado só é removido manualmente) [storage.py:40-53](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/storage.py:40).
- Pinar Actions por SHA e adicionar `frame-ancestors`/`form-action` ao CSP [index.html:6](C:/Users/alebi/Documents/ChatGPT/teste-opendata/admin-metrics/src/admin_metrics/web/index.html:6).
- Considerar um gatilho/heartbeat externo se a pontualidade horária for requisito; o cron do GitHub é best effort e o painel já avisa.

### Dashboard/UX

- Explicar "fora da janela de 72h" no detalhe de panorama antigo.
- Mostrar `resolved_at` e rotular a janela de incidentes resolvidos.
- Busca sem acento.
- Filtros compartilháveis via URL.
- Fechar o diálogo de execução no backdrop.
- Melhorar rótulo de HTTP 200 inválido.
- Incluir `json_path`, `request_time` e flags de qualidade no CSV exportado, se o objetivo é auditoria completa.
- Derivar URLs de repositório/Actions do payload.

### Engenharia

- Adicionar `ruff` e `mypy`/`pyright` ao CI; o bug B2 (`p['source_sha']`) e contratos de dict seriam candidatos naturais a tipagem estática.
- Adicionar testes para B1–B7, restore parcial e seleção de Release.
- Adicionar `pip-audit` ou verificação de vulnerabilidades das dependências lockadas.
- Limpar o `site/` local: ele está com artefatos antigos (v1.0.0 e cron `17 */2 * * *`), enquanto `docs/documentacao.html` e o site publicado estão em v1.2.0. Como `site/` é ignorado pelo Git, não afeta o repositório, mas pode confundir validação local.

## 4. O que está bem resolvido

- Separação explícita entre **tentativa de coleta**, **cobertura** e **dados válidos**; ausência não vira zero.
- Preservação do último panorama coerente e identificação clara de "DADOS ANTERIORES".
- Histórico de tentativas, bronze por SHA-256, retenção de dois ciclos e restore com limites.
- Catálogo HTTPS restrito e nenhuma chamada aos endpoints de clientes declarados.
- Regras de incidentes com confirmação e recuperação por amostras avaliáveis.
- CSV com BOM, separador `;` e proteção contra injeção de fórmula.
- Documentação HTML autocontida e testes de navegação/contratos.

## 5. Prioridade recomendada

1. **B2** (`source_sha` com `.get`) — correção pequena e evita bloqueio de republicação.
2. **B1** (data por página) — impacto direto em deltas e dia de referência.
3. **B3** (restore parcial) — caminho de recuperação precisa ser repetível.
4. **B4** (validar Release aprovada) — proteção do ciclo de publicação.
5. **B5/B6/B7** — consistência de contrato e limites.
6. Melhorias de UI/UX e endurecimento de CI.

## 6. Observação operacional da implantação publicada

No momento da auditoria, o `dashboard.json` publicado retornava versão **1.2.0**, cron `17 * * * *`, **12 runs retidos na janela de 72h**, última tentativa com **0/8 fontes válidas** (7 respostas HTTP 200 vazias e Nissan 503), panorama coerente preservado de 00:59 e dados por fonte de 02:57. Isso é compatível com o desenho de continuidade: o painel deve preservar o panorama anterior e sinalizar a idade, não inventar zero. Ao mesmo tempo, 12 runs em 72h mostram que o agendamento do GitHub está esparso; se pontualidade horária for requisito, será necessário um gatilho externo ou uma expectativa operacional explícita.

## 7. Validação

- `pytest -q` → **95 aprovados**.
- `node --test tests/test_dashboard.cjs` → **10 aprovados**.
- `node --check src/admin_metrics/web/app.js` → sem erros.
- O working tree já possuía arquivos de documentação não rastreados antes desta auditoria; eles não foram tocados.
- Os cenários reproduzidos nesta auditoria rodaram em diretórios temporários fora do repositório.
- **Nenhum arquivo do projeto foi alterado para produzir este relatório.**
