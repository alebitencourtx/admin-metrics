# Admin Metrics · Santander Observatory

Observatório executivo dos oito reportes Admin Santander, com atualização remota a cada hora, incidentes explicáveis, histórico e proveniência. Python, HTTPX, Arrow/Parquet, DuckDB e interface estática sem CDN.

- **[Dashboard](https://alebitencourtx.github.io/admin-metrics/)** — HTML na raiz, sem redirect de release.
- **[Documentação funcional e técnica](https://alebitencourtx.github.io/admin-metrics/documentacao.html)** — um único HTML autocontido, com desenhos de solução, fluxo e entidades, contratos, regras, código e manual do dashboard.
- **[Executar ou consultar o ETL](https://github.com/alebitencourtx/admin-metrics/actions/workflows/pages.yml)**.
- [Plano anterior à implementação](PLAN.md).

## Documentação atualizada

A referência completa é o [HTML único publicado](https://alebitencourtx.github.io/admin-metrics/documentacao.html), com [índice das fontes e manutenção](docs/README.md). Além de arquitetura, fluxo, ER e uso das oito seções, inclui dicionário JSON/Arrow/SQL, schemas reais do DuckDB, todos os estados de intervalo, exemplos de interpretação, regras fixas versus configuráveis, recuperação e cópias dos workflows/configurações.

O checkout local fica em `teste-opendata/admin-metrics/`, ao lado de `observatory-opendata/`. São repositórios e ambientes independentes. A agenda deste monitor não atualiza o OpenData.

## Escopo e interpretação

Consulta somente `GET /open-banking/admin/v2/metrics` dos oito hosts em `config/reporters.json`. **Não chama serviços de clientes ou pagamentos listados dentro do relatório.** O vínculo de URL/CNPJ foi verificado no Diretório oficial, com comprovante em `config/catalog-evidence.json`.

Duas medições distintas: duração da nossa tentativa HTTP ao Admin e médias dos serviços declaradas pelo banco. Média não é p95. Erros não identificam seus status HTTP, rejeições não provam 429 e acesso recusado ao Admin não comprova indisponibilidade dos demais serviços. Critérios analíticos não são laudo de conformidade regulatória. “Confirmado por persistência” significa repetir um sinal acima do limiar em duas observações; pode ocorrer com cumulativos sem mudança e não demonstra novos erros no intervalo.

A análise preliminar foi conferida independentemente. Na coleta de implementação, os oito reportes retornaram HTTP 200 e 276 identidades; o Santander principal declarou páginas excedentes apesar de já cobrir o total de registros. A divergência de aproximadamente três horas em requestTime permanece sinalizada, sem correção silenciosa. Dados publicados são reais; a série observada cresce a partir da primeira execução remota, sem inventar coletas anteriores.

## Executar localmente

Python 3.11 ou 3.12, 64 bits. No Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m admin_metrics.cli collect
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory site
```

Abra `http://127.0.0.1:8766/`. `build` no lugar de `collect` republica sem criar nova amostra. Parâmetros: `--root data --output site --config config`. Em Linux/macOS use `.venv/bin/python`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check src/admin_metrics/web/app.js
node --test tests/test_dashboard.cjs
```

## Engenharia e regras

| Camada | Responsabilidade |
|---|---|
| `config/` | Oito reportes permitidos, evidência de catálogo, regras versionadas |
| `src/admin_metrics/collect.py` | TLS, timeout, concorrência 4, retry limitado, paginação e deduplicação |
| `storage.py`, `archive.py` | Bronze SHA-256, escrita atômica, lock, checksum e restore ZIP limitado |
| `rules.py`, `contracts.py` | Configuração validada e URIs declaradas isoladas por fonte |
| `health.py`, `panorama.py` | Saúde da tentativa e último panorama completo por recorte, com dia coerente |
| `analysis.py` | Contratos, nulos, dia analítico, deltas e incidentes com recuperação |
| `marts.sql`, `build.py` | Arrow tipado, DuckDB, Parquet Zstandard e artefatos estáticos |
| `web/` | Página contínua, navegação ativa, filtros, gráficos SVG, detalhes e CSV |
| `documentation.py`, `manual-template.html` | Manual HTML único gerado a partir dos dados e código desta versão |
| `scripts/cloud_pipeline.py` | Restore, candidato draft, confirmação de deploy e retenção |
| `tests/` | Cenários temporais, falhas HTTP, ZIP corrompido, recuperação, publicação e replay |
| `.github/workflows/` | CI Windows/Linux e coleta/publicação remota |
| `data/`, `site/`, `.runtime/` | Gerados e ignorados pelo Git |

- Erro ≥5% com ≥100 chamadas: atenção; ≥20% com ≥1.000: crítico.
- Rejeição ≥5% com ≥100 chamadas: atenção, sem inferir causa.
- Média ≥2.000 ms: atenção; ≥4.000 ms: crítico, com amostra mínima de 100 chamadas.
- Regressão: ≥2× a mediana de pelo menos três médias diárias anteriores positivas.
- Recorrência contextual: ≥3 dias anteriores com erro ≥5% e ≥100 chamadas/dia.
- Falha de coleta: atenção na primeira, crítico na segunda consecutiva.
- Recuperação: duas amostras avaliáveis consecutivas. Falha, ausência, baixa amostra ou métrica inválida não resolvem a regra afetada. Reset suspende regras de contadores; latência válida continua sendo avaliada.

As taxas agregadas usam numeradores e denominadores válidos correspondentes. Média ponderada usa somente linhas com média e chamadas positivas. Últimas métricas boas ficam identificadas por fonte. Os marts do ciclo atual excluem linhas antigas; o panorama executivo preserva o último ciclo completo com um único dia de referência, explicitamente rotulado como anterior. Filtro por fonte escolhe o último ciclo válido daquele recorte, sem misturar ciclos no agregado.

Deltas comparam contadores cumulativos da mesma entidade/dia com cobertura completa. Não se somam snapshots; resets/revisões suspendem comparação. Dia de referência usa HTTP Date em America/Sao_Paulo, ou UTC da aquisição convertido se Date não for interpretável. Essa convenção analítica não comprova o fuso de consolidação da origem.

## Coleta a cada hora

Cron **`17 * * * *` UTC** no GitHub Actions. Não depende da máquina local. Em **Actions → Monitorar Admin e publicar Pages → Run workflow**, mantenha `refresh_data` marcado para coletar, ou desmarque para republicar o estado aprovado. Push republica sem criar observação; somente no bootstrap sem estado é feita uma coleta inicial.

GitHub Actions agenda por melhor esforço: pode atrasar e pode desabilitar schedule de repositórios públicos inativos. O navegador avisa após duas horas sem coleta. O workflow usa runner Linux padrão em repositório público; DuckDB é embutido no Python e não exige servidor contratado.

## Estado, retenção e recuperação

Observações e tentativas normalizadas: **30 dias**, cerca de 720 ciclos. Bronze no estado atual: **dois últimos ciclos**. Cada backup aprovado tem sua própria janela; a união de atual/anterior pode conter bytes de três ciclos. A poda temporal é aplicada após uma nova coleta. Incidentes abertos persistem; resolvidos por 30 dias. `state.json` contém os eventos de falha, mesmo quando nenhuma fonte retorna dados válidos. Configuração de regras usada é registrada por execução.

GitHub Releases mantém **dois pacotes aprovados**, atual e anterior. Cada um contém estado limitado e os bronzes dos dois ciclos recentes, com manifesto e SHA256SUMS. Dados novos não entram no histórico Git. Restore verifica checksum externo/interno, referências recentes, nomes permitidos, duplicatas e expansão limitada. Hashes históricos permanecem, mas os bytes bronze mais antigos podem ter expirado.

O candidato só é promovido após um job `deploy` comprovadamente concluído com sucesso no workflow correspondente. Um recibo acompanha a Release. Falha estrutural bloqueia; falha observável da fonte publica diagnóstico. Pages e Releases não têm transação distribuída: um deploy aprovado com confirmação falha pode deixar um candidato em draft; consulte o ID do dashboard e o job antes de recuperar.

Para restaurar explicitamente um estado anterior em diretório de dados vazio, com `gh` autenticado e `GH_REPO=alebitencourtx/admin-metrics`:

```powershell
python scripts/cloud_pipeline.py restore --tag state-<run>-<tentativa>
python -m admin_metrics.cli build
```

O restore não sobrescreve estado existente nem troca automaticamente o atual remoto. Nunca apague o pacote anterior antes de verificar a recuperação. Procedimento completo e confirmação de candidato após falha estão na documentação HTML.

O dashboard e os arquivos públicos de consumo contêm os **últimos 3 dias (72 horas)**. O eixo permanece nessa janela mesmo quando ainda há poucas coletas; lacunas ficam vazias. O estado nas Releases e o warehouse preservam os 30 dias. Não é possível preencher retroativamente os horários que não foram coletados.

## Continuidade quando a origem falha

HTTP 200 com resposta vazia não renova as métricas. O panorama mantém o último ciclo completo e um único dia de referência, rotulado **DADOS ANTERIORES**, enquanto a saúde informa a situação da tentativa atual. Selecionar uma fonte usa o último ciclo válido daquele recorte. Não há soma silenciosa de fontes de ciclos ou dias diferentes e valores preservados não viram pontos novos.

Última tentativa e últimos dados válidos têm horários e idades separados. Resposta vazia de fonte anteriormente preenchida tem até duas recapturas após 10 e 30 segundos, configuráveis; o período de espera libera a vaga de concorrência. HTTP/transporte mantém retry próprio limitado. `coverage_reconciled` indica conciliação de contagens; `complete`/`usable` exigem reporte não vazio. `data_status` distingue válido, vazio, falha HTTP, transporte e reporte inválido.

O Actions publica a saúde `healthy`, `partial` ou `unavailable` em output e resumo, com warning para degradação. O workflow continua publicando o diagnóstico e preservando estado: verde significa que o processamento/publicação concluiu, não que todas as fontes devolveram métricas.

## Dash e documentação

Oito seções: panorama, incidentes, tendências, endpoints, coleta, monitor de execuções, qualidade e metodologia. O monitor apresenta a matriz extração × API em páginas de 12 execuções, com detalhe de HTTP, horário, registros, tentativas, duração, bytes, diagnóstico e SHA. Novas execuções gravam o link do Actions; links antigos só são preenchidos quando há metadados de Release que comprovem a associação. O monitor atualiza a cada publicação, sem consulta bancária no navegador. O reporte é filtro global; busca/família/ordenação afetam a tabela e CSV. Clique em endpoint ou ranking para ver dias anteriores declarados, observações próprias, deltas, flags e SHA. As séries têm pontos com horário/valor; lacunas e mudança de dia interrompem linhas. CSV protege campos com prefixos de fórmula.

`site/documentacao.html` pode ser distribuído sozinho e funciona offline. O dashboard exige toda a pasta `site/`. A documentação contém três diagramas SVG, busca por seção, impressão, código real e tabelas do modelo.

## Fontes primárias

[OAS Admin 2.0.1](https://raw.githubusercontent.com/OpenBanking-Brasil/openapi/main/swagger-apis/admin/2.0.1.yml), [Diretório oficial](https://data.directory.openbankingbrasil.org.br/participants), [schedule GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Single node, um escritor por lake, sem autenticação corporativa ou medição contínua. Agregados entre reportes podem conter serviços compartilhados, sem garantia de transações únicas. Não inferir causa, percentis ou ausência de oferta a partir deste monitor.
