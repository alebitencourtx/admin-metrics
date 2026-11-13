# Documentação do Admin Metrics

A referência funcional e técnica é o **[manual HTML único publicado](https://alebitencourtx.github.io/admin-metrics/documentacao.html)**. A [cópia versionada](documentacao.html) pode ser aberta offline. Ela contém diagramas, regras, dicionário dos contratos JSON/Arrow/SQL, schemas do warehouse, código, configuração e workflows incorporados.

| Documento | Papel |
|---|---|
| `documentacao.html` | Manual completo e autocontido, vinculado ao estado usado na geração |
| [README do projeto](../README.md) | Início rápido, escopo, agenda e organização |
| [Validação](validacao.md) | Evidências históricas de implantação e testes, identificadas por run |
| [Plano](../PLAN.md) | Análise independente e decisões anteriores à implementação |

O manual publicado é regenerado em cada deploy usando o estado aprovado. A cópia do Git é uma evidência da última geração documental, e pode mostrar contagens anteriores ao Pages. IDs, timestamps e janela indicam a qual estado o documento se refere. Não se deve trocar esses números manualmente.

## Fontes da documentação

- `src/admin_metrics/manual-template.html`: contexto, diagramas, regras gerais e uso do dashboard.
- `src/admin_metrics/manual-supplement.html`: dicionário, casos de borda, continuidade e revisão.
- `src/admin_metrics/documentation.py`: campos, schema Arrow, introspecção DuckDB, evidências e incorporação de arquivos reais.
- `analysis.py`, `collect.py`, `archive.py`, `marts.sql`, CLI e workflows: fonte autoritativa do comportamento implementado.

## Atualização verificável

Execute em `teste-opendata/admin-metrics/`, usando o ambiente Python deste projeto. Restaure um estado aprovado em root vazio se desejar documentar a produção. Os comandos de recuperação e verificação estão no HTML.

```powershell
# build não cria amostra; usa o estado existente no root escolhido.
.\.venv\Scripts\python.exe -m admin_metrics.cli build --root data --output site
Copy-Item -LiteralPath site/documentacao.html -Destination docs/documentacao.html
.\.venv\Scripts\python.exe -m pytest -q
node --check src/admin_metrics/web/app.js
node --test tests/test_dashboard.cjs
```

Antes de publicar, conferir âncoras, busca com/sem acento, três diagramas, tabelas, impressão, leitura móvel e ausência de recursos externos obrigatórios. Push em main republica sem nova coleta quando existe estado aprovado. Conferir run_id, jobs build/deploy e que confirm ficou skipped nessa republicação.

Mudanças em regras não recalculam automaticamente incidentes e observações passadas. A documentação deve distinguir limiares configuráveis de constantes no código; `runs[].rules` registra a configuração usada em cada execução.

O [OpenData Observatory](https://alebitencourtx.github.io/open-finance-observatory/documentacao.html) analisa produtos, condições e rede de três grupos. Não compartilha a agenda, o estado ou o protocolo de promoção deste monitor.
