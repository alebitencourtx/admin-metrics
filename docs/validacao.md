# Evidências de validação

Revisão do índice de evidências: **13/11/2026**. Números, tags, horários e tempos abaixo pertencem às execuções identificadas; não são um painel ao vivo. A retenção pode remover Releases históricas citadas. Documentos vigentes: [dados/regras](dados-e-regras.md), [dashboard](dashboard.md) e [operação](operacao.md).

## Última versão de código validada: 1.2.0

| Evidência | Referência |
|---|---|
| Commit | `38a1faf63002ff78da7dd9f566b593aac0d9455f` |
| CI | [43362739900](https://github.com/alebitencourtx/admin-metrics/actions/runs/43362739900): quatro combinações Windows/Linux × Python 3.11/3.12 aprovadas; 95 testes Python e dez Node |
| Republicação por push | [43362740559](https://github.com/alebitencourtx/admin-metrics/actions/runs/43362740559): build/deploy aprovados, sem nova observação |
| Nova coleta e confirmação | [43362828874](https://github.com/alebitencourtx/admin-metrics/actions/runs/43362828874): build/deploy/confirm aprovados; saúde `unavailable` corretamente sinalizada |
| Dados dessa coleta | Run `20261113T040226Z-890eadd0`, início 13/11 às 01h02 BRT; 12 ciclos e 2.759 observações retidos |
| Resultado de origem | Sete Admins HTTP 200 vazios, cada um com duas recapturas/três probes; Nissan 503 com três tentativas HTTP |
| Preservação | Panorama conjunto `20261113T005910Z-1cdc203e`, dia 12/11, 279 endpoints; nenhum ponto inventado no ciclo vazio |
| Pacote conferido | `state-43362828874-1`: checksum e contrato validados; modelo 3. Na conferência, backup `state-43359450248-1` |

Os avisos de depreciação das actions e migração da imagem Ubuntu observados no CI não foram tratados como falha dos testes. O verde do workflow indica processamento/publicação, não sucesso de todas as fontes.

## Correções de robustez · 13/11/2026

- **107 testes Python e 14 testes Node** aprovados localmente após as correções.
- Dia analítico passou a usar o `HTTP Date` da página que produziu cada linha; páginas que cruzam o dia tornam a captura incompleta (`page_day_changed`/`mixed_reference_day`).
- Limite de 10.000 identidades agora é efetivo e registra `record_limit`; o rebuild tolera probe legado sem `source_sha`.
- `coverage_reconciled` passa a `false` quando registros inválidos são descartados na normalização.
- Restore remove bronzes gravados na tentativa que falhou antes do `state.json`; só Releases com `purpose`, IDs e assets esperados são selecionadas.
- Catálogo valida `id`, `label`, `company`, `cnpj` e URL; uptime booleano é rejeitado; estado com `model_version` desconhecido é bloqueado.
- Dashboard: busca sem acentos, filtros na URL, `resolved_at` visível, aviso de panorama fora da janela de 72h, fechamento do diálogo de execução no backdrop e rótulo próprio para reporte HTTP 200 inválido.
- Não houve coleta real nesta revisão; os cenários novos usam `MockTransport` e diretórios temporários.

## Cronologia histórica

## Antes da implantação

- Migração do projeto anterior: repositório íntegro, remote preservado e 67 testes aprovados após reinstalar o pacote editável na nova pasta.
- Catálogo novo: oito correspondências URL/CNPJ no Diretório oficial, comprovante em `config/catalog-evidence.json`.
- Coleta real local: oito HTTP 200 e 276 endpoints; nenhuma chamada aos serviços de clientes listados.
- Testes automatizados: cenários de zeros/nulos/contadores impossíveis, horário/dia, resets, deduplicação, retry e 403, recuperação de incidentes, falha estrutural preservando publicação, falha total das fontes, retenção, reprocessamento, ZIP corrompido/path traversal e promoção após deploy.
- Navegador: panorama, filtro Santander, busca recurring-payments, detalhe com D−1…D−6, exportação CSV, navegação ativa, manual com busca/estado vazio e layout móvel a 390 px sem overflow horizontal de página.
- Ensaio sintético local: 360 ciclos × 276 registros = 99.360 observações; build Arrow/DuckDB/Parquet/HTML em 1,573 s, payload 26.136.648 bytes. Dados altamente repetitivos derivados da primeira coleta para testar a escala, sem publicação; não é benchmark de tráfego, variabilidade ou rede. Não estabelece SLA.

O diretório `artifacts/benchmark` é ignorado e não integra o site público.

## Primeira execução remota verificada

- Actions [42880395554](https://github.com/alebitencourtx/admin-metrics/actions/runs/42880395554): build, deploy e confirm concluídos com sucesso. Oito HTTP 200, 276 identidades, observação `20261110T185746Z-8b6176b9`.
- CI [42880395657](https://github.com/alebitencourtx/admin-metrics/actions/runs/42880395657): quatro combinações Windows/Linux × Python 3.11/3.12 aprovadas, 44 testes em cada.
- Release `state-42880395554-1`: ZIP, SHA256SUMS e recibo de deploy publicados após confirmação.
- Pages novo e documentação retornaram HTTP 200; o site OpenData anterior também continuou respondendo HTTP 200.
- Na implantação inicial de 10/11, o workflow estava `active` com cron `17 */2 * * *` UTC. Essa agenda foi substituída pelo cron horário em 12/11; acionamento manual permanece disponível.

O workflow é best effort. O sucesso da primeira execução não demonstra disponibilidade futura nem pontualidade garantida da agenda.

## Restore e segunda execução remota

- Republicação por push [42880998560](https://github.com/alebitencourtx/admin-metrics/actions/runs/42880998560): sucesso, sem nova observação.
- Coleta manual [42881001169](https://github.com/alebitencourtx/admin-metrics/actions/runs/42881001169): restore do estado aprovado, nova coleta, deploy e confirmação concluídos com sucesso.
- Duas Releases aprovadas: `state-42881001169-1` e `state-42880395554-1`, com recibos de deploy. O pacote atual foi baixado, verificado e reconstruído localmente: 2 ciclos, 552 observações e 16 objetos bronze.
- As 276 entidades permaneceram sem mudança entre essas duas observações próximas; todos os intervalos foram corretamente classificados como `unchanged_report`, sem inventar tráfego. Essas execuções manuais não representam amostras espaçadas em duas horas.
- Revisão de leitura solicitada pelo usuário: fontes auxiliares de 13–14 px, contraste reforçado, títulos semânticos no ranking, caminhos com quebra de linha, resumo executivo dividido em destaques e gráficos com dimensões adaptadas à largura real. Preview conferido em desktop e em 390 px, sem overflow horizontal da página.

## Correções e frequência horária · 12/11/2026

- Cron alterado para `17 * * * *` UTC; configuração informativa e YAML conferidos por teste. Aviso de atraso após duas horas. Agendamento permanece best effort do GitHub, sem serviço externo.
- Corrigidos: supressão de latência por contadores não comparáveis; poda com referências órfãs na fronteira de 30 dias; falta de retry após interrupção do corpo HTTP 200; URI inválida interrompendo normalização; filtro de incidentes baseado no rótulo mutável.
- Comparabilidade separada de erros/rejeições: reset de um numerador não esconde regra válida do outro. Incidentes novos usam `model_version=2`; identidade estável migra incidentes legados sem recalcular detecções passadas.
- Duplicatas conflitantes tornam a fonte incompleta, preservam evidência e última coleta boa, e ficam fora dos KPIs do ciclo. Regras têm validação de tipo, limites e ordem antes da coleta.
- Pack e restore compartilham limites: estado até 512 MiB, objetos até 16 MiB, total expandido até 512 MiB e ZIP até 300 MiB. O estado horário estimado ultrapassaria o limite antigo de 256 MiB; o ensaio abaixo confirmou o transporte com a nova configuração.
- Dashboard, tendências, duração Admin e detalhe de endpoint: janela de 72 horas; estado/warehouse continuam com 30 dias. Os três dias anteriores declarados são exibidos separadamente; arrays completos permanecem no estado para baseline/recorrência.
- Testes locais: 82 testes Python e três testes Node aprovados. Cenário de 31 dias horários cruza a fronteira de retenção com captura três segundos após o início do run, validando referências em cada ciclo.
- Ensaio sintético de escala: 720 ciclos × 279 endpoints = 200.880 observações, derivadas da última coleta real apenas para teste local. Estado 303,25 MiB; ZIP 35,64 MiB; JSON público de 3 dias 5,74 MiB e 20.088 pontos. Build 1,652 s, pack 14,547 s e restore 6,613 s. Dados repetitivos, sem chamadas de rede, sem publicação e sem garantia de SLA; resultado em `artifacts/hourly-scale-v2/result.json`, ignorado pelo Git.
- Replay local do pacote aprovado `state-43279156859-1`: oito ciclos e 2.216 observações preservados. Manual regenerado sem acrescentar observação.
- Navegador: tendências de 72h com lacunas reais, filtro CCVM com incidentes, detalhe D−1/D−2/D−3, manual aberto pelo link da navegação, três diagramas e busca sem acentos. Sem erros de console nas páginas verificadas.

Os horários não coletados antes da correção não são preenchidos. Uma janela de três dias não comprova três dias completos de amostragem; o painel informa desde quando existem observações.

## Continuidade e monitor de extrações · 13/11/2026

- v1.2.0 / modelo de captura 3: HTTP 200 vazio tem cobertura conciliada independente de usabilidade; as novas capturas ficam complete=false/usable=false/data_status=empty. Runs legados são interpretados sem inventar métricas ou recalcular incidentes passados.
- Última tentativa e últimos dados válidos separados. Panorama derivado de um único ciclo completo e um único dia por recorte; preservado durante falha parcial/total, sem repetir pontos ou misturar ciclos.
- Retentativas de vazio para fonte antes válida: 10 e 30 segundos, com concorrência liberada durante espera, todos os probes/bronzes preservados e uma aplicação analítica por ciclo.
- Monitor dos três dias, matriz execução × API, páginas de 12, filtros globais e detalhe de resposta, horários, registros, tentativas, duração, bytes e SHA. Link do Actions novo registrado; links antigos enriquecidos somente pelos metadados comprovados de Releases aprovadas.
- Actions: output/resumo de saúde e warning para coleta parcial/indisponível; diagnóstico continua publicável, distinguindo conclusão do pipeline da disponibilidade das métricas.
- 95 testes Python e dez testes Node passaram localmente, incluindo falha total, parcial, recuperação, mudança de dia, fontes com dias divergentes, resposta vazia, retentativas, relógio recente/antigo, interpolação do aviso, monitor e paginação.
- Replay do pacote state-43359450248-1: 11 ciclos e 2.759 observações preservados; a tentativa 00h31 BRT tinha sete HTTP 200 vazios e Nissan 503. O panorama coerente selecionado foi 12/11 às 21h59 (279 endpoints, 106.602.207 chamadas declaradas), enquanto saúde permaneceu 0/8. Fontes individuais saudáveis na coleta anterior usam o ciclo de 23h57.
- Navegador sem erros de console: aviso com dados antigos explícitos, matriz com a transição 7/8 → 0/8, detalhe HTTP 200 vazio com SHA, e ranking abrindo a evidência do ciclo preservado. Página sem overflow horizontal global; matriz tem rolagem própria.

O monitor é estático e muda após publicação; não informa andamento de um job antes do deploy. Histórico de até 30 dias limita a busca do panorama preservado. Sem ciclo válido retido, o painel informa indisponibilidade, sem converter ausência em zero.
