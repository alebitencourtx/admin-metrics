# Documentação Markdown do Admin Metrics

Revisão: **13/11/2026**. Implementação documentada: pacote **1.2.0**, checkout de código **38a1faf**, modelo das novas capturas **3**, envelope de estado **1**. As notas operacionais abaixo descrevem o que existe; evidências de execuções específicas têm identificação e data próprias.

| Documento | Conteúdo |
|---|---|
| [README do projeto](../README.md) | Início rápido, escopo, stack e links públicos |
| [Arquitetura](arquitetura.md) | Solução, fluxo, responsabilidades, persistência, publicação e limites |
| [Contratos, dados e regras](dados-e-regras.md) | Grãos, relações, campos, fórmulas, todos os parâmetros e retenção |
| [Uso do dashboard](dashboard.md) | Oito seções, panorama preservado, monitor, filtros e interpretação |
| [Operação e recuperação](operacao.md) | CLI, Actions, gatilhos, restore isolado e falhas entre deploy/promoção |
| [Validação](validacao.md) | Resultados ligados a versões/runs; números históricos não são contagem ao vivo |
| [Plano original](../PLAN.md) | Decisões iniciais preservadas e quadro das mudanças implementadas |
| [Manual HTML publicado](https://alebitencourtx.github.io/admin-metrics/documentacao.html) | Documento autocontido gerado em cada publicação |

## Fontes de verdade e atualização

- `config/reporters.json` e `config/catalog-evidence.json`: catálogo e comprovação de URL/CNPJ.
- `config/rules.json`, `rules.py`, `contracts.py`, `collect.py`, `analysis.py`: parâmetros e comportamento analítico.
- `health.py` e `panorama.py`: saúde atual e seleção de ciclo coerente; não confundir com os marts atuais.
- `build.py`, `marts.sql`, `web/app.js` e `scripts/cloud_pipeline.py`: payload, consumo e lifecycle remoto.
- `.github/workflows/pages.yml` e `ci.yml`: agenda, concorrência, permissões e checks.

Os arquivos Python citados estão em `src/admin_metrics/`, exceto o helper explicitamente em `scripts/`. Os Markdown usam links relativos para funcionar após mover o checkout. Execute comandos a partir de `teste-opendata/admin-metrics/`.

Ao mudar comportamento, atualize estes Markdown junto da implementação e identifique as evidências novas. Revisões somente textuais não exigem nova coleta. Na revisão de 13/11/2026 solicitada para Markdown, os HTMLs não foram regenerados.

O manual HTML tem fontes próprias em `manual-template.html`, `manual-supplement.html` e `documentation.py`. Em uma atualização futura do HTML, execute build com estado aprovado e copie o arquivo gerado; não troque manualmente os IDs/contagens de uma geração antiga. A cópia versionada [documentacao.html](documentacao.html) pode ter um run diferente do Pages.

## Identidades e limites

Versão de pacote, modelo por run, versão do envelope, run dos dados, workflow do Actions e revisão documental são identidades diferentes. Build sem coleta não cria observação; o lifecycle remoto pode enriquecer vínculos antigos com o Actions a partir de metadados comprovados das Releases, sem recalcular métricas.

O cron é **horário**, `17 * * * *` UTC. Os gráficos e o monitor mostram **72h**; o estado conserva **30 dias**. O panorama pode usar ciclo anterior ainda retido e informa data/idade. Não há backfill automático de horários perdidos.

O [OpenData](../../observatory-opendata/README.md) é independente: não recebe a agenda do Admin, não possui esse monitor de execuções e não usa o mesmo protocolo de promoção.
