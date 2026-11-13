# Operação, publicação e recuperação

Revisão: 13/11/2026; Admin Metrics 1.2.0. Execute a partir de `teste-opendata/admin-metrics/`. Os comandos abaixo podem gerar arquivos ou consultar fontes; ler esta documentação não executa esses procedimentos.

## Preparação e comandos locais

Python 3.11/3.12 64 bits; Node 22 para testes JavaScript; GitHub CLI autenticado para operações remotas. Instale pelos locks, depois o pacote editável:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
# Nova coleta: consulta exclusivamente os Admins do catálogo.
.\.venv\Scripts\python.exe -m admin_metrics.cli collect --root data --output site --config config
# Reconstrução: não consulta bancos nem acrescenta observação.
.\.venv\Scripts\python.exe -m admin_metrics.cli build --root data --output site --config config
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory site
```

Abra `http://127.0.0.1:8766/`. `--root`, `--output` e `--config` são opções do CLI Admin. No OpenData a sintaxe é diferente: `--lake` vem antes do subcomando.

## Agenda e gatilhos

O [workflow Pages](../.github/workflows/pages.yml) usa `17 * * * *` UTC: uma previsão a cada hora, no minuto 17, também minuto 17 em Brasília. O GitHub pode atrasar ou não entregar um disparo; frequência configurada não comprova amostragem real.

| Gatilho | Comportamento |
|---|---|
| `schedule` | Restaura, coleta, gera, publica e confirma candidata |
| Manual `refresh_data=true` | Mesmo fluxo de coleta nova |
| Manual `refresh_data=false` | Republica estado aprovado sem coleta |
| Push na `main` | Testa e republica; bootstrap sem estado aprovado faz coleta inicial |

Na interface: Actions → Monitorar Admin e publicar Pages → Run workflow. Pelo CLI:

```powershell
gh workflow run pages.yml --repo alebitencourtx/admin-metrics --ref main -f refresh_data=true
gh workflow run pages.yml --repo alebitencourtx/admin-metrics --ref main -f refresh_data=false
```

O workflow testa antes de publicar. `candidate_tag` vazio significa republicação sem candidata; `confirm` fica skipped. A saída `collection_status` e o resumo distinguem `healthy`, `partial` e `unavailable`. Coleta degradada emite warning e publica diagnóstico; verde não atesta disponibilidade das métricas.

## Onde os dados persistem

O runner é descartável. Releases `state-*` guardam `state.zip`, `SHA256SUMS` e, após confirmação, recibo de deploy. A atual leva o histórico normalizado de até 30 dias; a anterior é backup. Cada pacote leva bronze de dois ciclos. DuckDB/Parquet/site são derivados reconstruídos a partir do estado.

Panorama preservado pode ser anterior à janela de 72h dos gráficos, desde que ainda exista na retenção de 30 dias. Fontes vazias não geram pontos copiados. A poda é feita em coleta nova, por run completo, e não por relógio em tempo real durante simples rebuild.

## Diagnóstico

| Sintoma | Verificação / ação |
|---|---|
| HTTP 200 sem dados | Abrir célula no monitor; conferir registros/probes. Fonte antes válida já tem até duas recapturas espaçadas. Não interpretar como zero tráfego |
| HTTP 503 ou transporte | Conferir probes/bronze e horários. Retry HTTP já é limitado; não desativar TLS ou contornar acesso |
| Última tentativa recente, dados antigos | Comportamento esperado em vazio/erro. Ler a data do panorama e saúde atual |
| Muitas horas sem run | Conferir workflow ativo, branch e histórico de disparos; disparo manual não prova que o cron voltou a funcionar |
| Estado sem fontes válidas | Diagnóstico continua persistido/publicável; últimas boas e panorama coerente permanecem enquanto retidos |
| Configuração inválida, hash ou referência inválida | Falha estrutural: bloquear avanço, conferir pacote e recuperar explicitamente |
| Lock local abandonado | Verificar processo/PID e root antes de remover `.writer.lock`; não há expiração automática |
| Deploy publicado, candidata ainda draft | Comparar run_id público, manifesto e jobs; reconciliar antes de promover/descartar |

## Restaurar em diretório novo

Escolha uma tag **aprovada atualmente existente**; as tags dos relatórios históricos podem ter expirado pela rotação. Não restaure sobre `data/` ocupado.

```powershell
$tag = 'state-<workflow_run_id>-<attempt>'
gh release download $tag --repo alebitencourtx/admin-metrics --pattern state.zip --pattern SHA256SUMS --dir .runtime/recovery-download
.\.venv\Scripts\python.exe -c "from pathlib import Path; from admin_metrics.archive import restore; p=Path('.runtime/recovery-download'); restore(p/'state.zip',p/'SHA256SUMS',Path('.runtime/recovered-data'))"
.\.venv\Scripts\python.exe -m admin_metrics.cli build --root .runtime/recovered-data --output .runtime/recovered-site
.\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1 --directory .runtime/recovered-site
```

O restore verifica checksum externo, hashes internos, nomes permitidos, duplicatas, limites, run do manifesto e bronze recente. O ponteiro `state.json` é escrito por último; se a gravação falhar, os bronzes criados naquela tentativa são removidos para permitir nova tentativa em diretório limpo. Só Releases com `purpose=approved-monitor-state`, IDs válidos e os assets `state.zip`/`SHA256SUMS` são consideradas aprovadas. Esses comandos locais não escolhem outro estado como atual no GitHub.

O helper `python scripts/cloud_pipeline.py restore --tag ...` restaura em **`data/` fixo**, também vazio, e usa `GH_REPO`. Não tem opção `--root`; para outro destino use o procedimento Python acima.

## Falha entre deploy e promoção

1. Consulte o run do Actions, ID do dashboard, corpo da candidata e manifesto.
2. Confirme que o job `deploy` daquela candidata concluiu e que o site corresponde ao seu `data_run_id`.
3. Só então execute `promote --tag ...` no contexto correto. O helper exige prova do job remoto e grava recibo.
4. `discard` aceita somente candidata draft do prefixo `state-`; não descarte enquanto a publicação não estiver reconciliada.

Não existe transação conjunta Pages/Releases. Não reinicie histórico vazio por falha de download, não apague o backup para fazer validação passar e não promova candidata de outro workflow. O helper do OpenData não usa o mesmo protocolo.

## Verificação sem novas coletas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check src/admin_metrics/web/app.js
node --test tests/test_dashboard.cjs
git diff --check
```

A evidência registrada para `38a1faf` é 95 testes Python e dez Node, além de CI Windows/Linux × Python 3.11/3.12. Não é promessa de cobertura integral, SLA, homologação de acessibilidade ou auditoria regulatória.
