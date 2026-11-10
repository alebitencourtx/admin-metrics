"""One standalone manual, tied to the actual observation and bundled source."""
from html import escape
import json
import re
from pathlib import Path

from .storage import atomic

HERE = Path(__file__).parent


def generate(payload, output):
    template = (HERE / 'manual-template.html').read_text(encoding='utf-8')
    def text(v):
        return escape(str(v))
    def table(headers, values):
        return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>'+text(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+text(v)+'</td>' for v in row)+'</tr>' for row in values)+'</tbody></table></div>'
    sources = table(['Reporte', 'Empresa / CNPJ', 'URL Admin'], [(r['label'], r['company']+' / '+r['cnpj'], r['url']) for r in payload['reporters']])
    rules = table(['Parâmetro', 'Valor configurado'], payload['rules'].items())
    evidence = table(['Reporte', 'HTTP', 'Identidades', 'Cobertura', 'Diagnóstico'], [(r['label'],r['status'],r['records'],r['coverage'], ', '.join(r['issues']) or 'Sem flags de coleta') for r in payload['runs'][-1]['reports']])
    modules = [('collect.py','HTTP, limites, retry, paginação e bronze'), ('analysis.py','Contratos, deltas, histórico e incidentes'), ('storage.py','Hash, escrita atômica e exclusão mútua'), ('build.py','Arrow, DuckDB, Parquet e publicação estática'), ('marts.sql','Definições únicas de agregação SQL'), ('pipeline.py','Coleta, build e commit de estado'), ('archive.py','Pacote limitado, integridade e restore seguro'), ('cli.py','Operação local padronizada'), ('documentation.py','Este manual autocontido'), ('web/app.js','Filtros, gráficos, navegação, detalhes e exportação'), ('scripts/cloud_pipeline.py','Restore, candidato, confirmação e retenção remotos')]
    code = ''
    for name, desc in modules:
        path = HERE/name
        if not path.exists():
            path = HERE.parents[1]/name
        if path.is_file():
            code += '<details><summary>'+text(name)+' · '+text(desc)+'</summary><pre><code>'+text(path.read_text(encoding='utf-8'))+'</code></pre></details>'
    substitutes = {'SOURCES': sources, 'RULES': rules, 'EVIDENCE': evidence, 'MODULES': table(['Arquivo','Responsabilidade'],modules), 'CODE':code,
                   'RUN':text(payload['meta']['run_id']), 'OBSERVED':text(payload['meta']['observed_at']), 'ROWS':str(len(payload['latest'])),
                   'VERSION':text(payload['meta']['version']), 'CONFIG':text(json.dumps(payload['rules'],ensure_ascii=False,indent=2))}
    for key, value in substitutes.items():
        template = template.replace('@@'+key+'@@',value)
    if re.search(r'@@[A-Z_]+@@', template):
        raise ValueError('Manual contém placeholder não preenchido')
    atomic(output, template.encode())
    return Path(output)
