"""One standalone manual, tied to the actual observation and bundled source."""
from html import escape
import json
import re
import os
from pathlib import Path

from .storage import atomic, sha

HERE = Path(__file__).parent
DOC_REVISION = '2026-11-12.1'

FIELD_HELP = {
    'run_id': 'Identidade de execução UTC + sufixo aleatório; não é a data de referência do banco.',
    'entity_id': 'SHA-256 truncado a 24 caracteres de reporter_id + endpoint. Chave técnica da entidade reportada.',
    'observed_at': 'Instante UTC de início da observação da fonte; cada tentativa também guarda seu próprio instante.',
    'day': 'Dia analítico por HTTP Date em America/Sao_Paulo, com fallback para a coleta; não comprova o fuso de consolidação da origem.',
    'reporter_id': 'Identidade do host no catálogo; Nissan e Renault permanecem distintos mesmo com CNPJ igual.',
    'reporter': 'Rótulo operacional da fonte, e não prova de controle societário.',
    'endpoint': 'URL/URI descrita pelo banco. Nunca é chamada pelo monitor.',
    'path': 'Caminho extraído de endpoint; preserva parâmetros de rota declarados.',
    'family': 'Primeiro segmento depois de /open-banking/; usado como classificação analítica.',
    'calls': 'invocations.currentDay; contador cumulativo declarado do dia, int64 não negativo ou nulo.',
    'errors': 'errors.currentDay; sem discriminação dos status HTTP de origem.',
    'rejections': 'rejections.currentDay; não permite inferir sozinho a causa ou código de rejeição.',
    'mean_ms': 'averageResponse.currentDay, em milissegundos. Média declarada, não p95.',
    'error_pct': '100 × errors/calls, apenas com chamadas positivas e numerador válido ≤ chamadas; caso contrário nulo.',
    'rejection_pct': '100 × rejections/calls sob os mesmos critérios, com denominador válido próprio.',
    'uptime': 'availability.uptime.uptimeRate convertido para razão finita em [0,1]; interface multiplica por 100.',
    'source_complete': 'Cobertura reconciliada da captura Admin que produziu a linha; não atesta qualidade de todos os campos.',
    'fresh': 'Linha da mesma execução que o último ciclo. Só tem valor útil em current_rows; na projeção histórica observations fica nulo. Não mede idade do relógio.',
}

OBSERVATION_EXTRAS = [
    ('day_basis','string','Explica qual relógio fundamentou day; não modifica requestTime.'),
    ('source_sha','SHA-256','Hash do corpo bronze de origem; os bytes podem expirar da retenção.'),
    ('json_path','string','Posição $.data[n] no corpo identificado pelo hash.'),
    ('request_time','string/nulo','requestTime original, sem correção automática de fuso.'),
    ('clock_offset_seconds','número/nulo','observed_at − requestTime; limiar clock_skew_seconds configurável.'),
    ('average_tps / peak_tps','int64/nulo','averageTps / peakTps atuais declarados; não são calculados a partir de chamadas.'),
    ('general_uptime','razão/nulo','generalUptimeRate declarado, independente do uptime do endpoint.'),
    ('downtime_seconds / general_downtime / scheduled_outage','int64/nulo','Segundos declarados em partialDowntime / generalDowntime / scheduledOutage.'),
    ('previous','objeto de arrays','Até sete posições por calls, errors, rejections, mean_ms, average_tps e peak_tps; D−1 primeiro.'),
    ('baseline_mean_ms','número/nulo','Mediana das médias diárias anteriores positivas; mínimo baseline_minimum_days configurável.'),
    ('recurrent_days','inteiro','Dias anteriores com chamadas ≥minimum_calls e erro ≥error_attention_pct; limiares compartilhados com as regras.'),
    ('quality','array de strings','Ocorrências de contrato/consistência; não reescreve o valor informado.'),
    ('fingerprint','SHA-256','Seis métricas atuais, uptime, downtime_seconds e previous; exclui requestTime. Não é checksum do JSON completo.'),
    ('interval_from / interval_to','UTC/nulo','Instantes das duas observações comparadas, e não janela oficial de agregação da instituição.'),
    ('interval_seconds','número/nulo','Diferença entre os instantes; tempo não crescente invalida o intervalo.'),
    ('interval_calls / interval_errors / interval_rejections','int64/nulo','Diferenças aceitas dos cumulativos; indisponíveis quando a classificação não é valid.'),
    ('interval_error_pct / interval_rejection_pct','percentual/nulo','Taxas dos deltas aceitos; sem denominador positivo ficam nulas.'),
    ('interval_state','enum','Motivo preciso de comparação aceita ou suspensa; ver a tabela de estados.'),
    ('interval_error_state / interval_rejection_state','enum','Comparabilidade de cada numerador com chamadas; impede que reset de rejeições esconda uma taxa de erro válida. Latência tem elegibilidade independente.'),
]

PROBE_FIELDS = [
    ('page / attempt','inteiro','Página solicitada e tentativa a partir de 1.'),
    ('observed_at','UTC','Início da tentativa HTTP, distinto do início do ciclo e da fonte.'),
    ('url','URL','Admin e parâmetros solicitados. Redirecionamentos não são seguidos.'),
    ('status','inteiro','HTTP recebido; 0 quando não houve resposta HTTP.'),
    ('duration_ms','número','Tempo da tentativa até leitura do corpo ou erro; não é média do serviço nem duração total do ETL.'),
    ('http_date','string/nulo','Cabeçalho Date recebido, sem substituí-lo por requestTime.'),
    ('source_sha / bytes','hash/inteiro','Corpo completo preservado e seu tamanho. Podem estar ausentes em transporte/limite de tamanho.'),
    ('error','string/nulo','Condição final da tentativa; tentativas transitórias permanecem no histórico mesmo se a última tiver sucesso.'),
]

INCIDENT_FIELDS = [
    ('id','hash truncado','Ocorrência identificada por entidade + regra + run de abertura; reabertura após resolução cria outro ID.'),
    ('entity_id / rule','strings','Entidade do serviço ou source:<reporter_id>, mais nome da regra detectada.'),
    ('reporter_id / reporter / endpoint','string/nulo','ID estável usado no filtro, rótulo atual e endpoint; rótulos antigos são reconciliados pelo ID. Coleta não tem endpoint de serviço.'),
    ('opened_at / opened_run','UTC / ID','Primeira detecção observada; não é necessariamente o início real da falha.'),
    ('last_seen','UTC','Última detecção acima do limiar; não é a última coleta bem-sucedida.'),
    ('evaluated_at','UTC','Última avaliação conclusiva de detecção/recuperação; pode ficar antiga durante ausência de dados.'),
    ('samples','inteiro','Total de detecções desta ocorrência, inclusive sequências separadas por recuperação parcial.'),
    ('consecutive_samples','inteiro','Tamanho da sequência atual de detecções; uma amostra sem sinal interrompe a sequência.'),
    ('confirmed','booleano','Última sequência detectada atingiu confirmation_samples; não prova erros novos entre os ciclos.'),
    ('recovery_samples','inteiro','Amostras avaliáveis consecutivas abaixo do limiar; amostra desconhecida zera a sequência.'),
    ('status / severity','enum','open / recovering / resolved e attention / critical; severidade pode variar na mesma ocorrência.'),
    ('evidence','string','Numerador, denominador ou contexto que justificou a última detecção.'),
    ('resolved_at','UTC opcional','Registrado apenas depois de completar recovery_samples configurado.'),
]


def generate(payload, output, warehouse=None):
    template = (HERE / 'manual-template.html').read_text(encoding='utf-8')
    template = template.replace('@' * 2 + 'SUPPLEMENT' + '@' * 2,
                                (HERE / 'manual-supplement.html').read_text(encoding='utf-8'))
    def text(v):
        return escape(str(v))
    def table(headers, values):
        return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>'+text(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+text(v)+'</td>' for v in row)+'</tr>' for row in values)+'</tbody></table></div>'
    from .build import SCHEMA
    dictionary = '<h3>Projeção física Arrow: current_rows e observations</h3>' + table(['Campo','Tipo Arrow','Semântica / nulos'],[(f.name,str(f.type),FIELD_HELP[f.name]) for f in SCHEMA])
    dictionary += '<h3>Campos adicionais da observação no estado/JSON</h3>' + table(['Campo','Tipo lógico','Semântica'],OBSERVATION_EXTRAS)
    dictionary += '<h3>Tentativas HTTP: runs[].reports[].probes[]</h3>' + table(['Campo','Tipo lógico','Semântica'],PROBE_FIELDS)
    dictionary += '<h3>Ocorrências: incidents[]</h3>' + table(['Campo','Tipo lógico','Semântica'],INCIDENT_FIELDS)
    physical = []
    if warehouse is not None:
        import duckdb
        db = duckdb.connect(str(warehouse), read_only=True)
        try:
            for name in ('current_rows','observations','report_summary','family_summary','observation_trends'):
                count = db.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
                fields = db.execute(f'DESCRIBE {name}').fetchall()
                physical.append('<details><summary>'+name+' · '+str(count)+' linhas</summary>'+table(['Coluna','Tipo DuckDB'],[(r[0],r[1]) for r in fields])+'</details>')
        finally:
            db.close()
    sources_code, hashes = [], []
    root = HERE.parents[1]
    for name in ('config/rules.json','config/reporters.json','config/catalog-evidence.json','requirements.lock','.github/workflows/pages.yml','.github/workflows/ci.yml'):
        path = root/name
        if path.is_file():
            raw = path.read_bytes(); hashes.append((name,sha(raw)))
            sources_code.append('<details><summary>'+text(name)+'</summary><pre><code>'+text(raw.decode('utf-8'))+'</code></pre></details>')
    sources = table(['Reporte', 'Empresa / CNPJ', 'URL Admin'], [(r['label'], r['company']+' / '+r['cnpj'], r['url']) for r in payload['reporters']])
    rules = table(['Parâmetro', 'Valor configurado'], payload['rules'].items())
    evidence = table(['Reporte', 'HTTP', 'Identidades', 'Cobertura', 'Diagnóstico'], [(r['label'],r['status'],r['records'],r['coverage'], ', '.join(r['issues']) or 'Sem flags de coleta') for r in payload['runs'][-1]['reports']])
    modules = [('collect.py','HTTP, limites, retry, paginação e bronze'), ('contracts.py','Validação segura das URIs declaradas'), ('rules.py','Configuração tipada e limites compartilhados'), ('analysis.py','Contratos, deltas, histórico e incidentes'), ('storage.py','Hash, escrita atômica e exclusão mútua'), ('build.py','Arrow, DuckDB, Parquet e publicação estática'), ('marts.sql','Definições únicas de agregação SQL'), ('pipeline.py','Coleta, build e commit de estado'), ('archive.py','Pacote limitado, integridade e restore seguro'), ('cli.py','Operação local padronizada'), ('documentation.py','Este manual autocontido'), ('web/app.js','Filtros, gráficos, navegação, detalhes e exportação'), ('scripts/cloud_pipeline.py','Restore, candidato, confirmação e retenção remotos')]
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
    substitutes.update(DICTIONARY=dictionary,
                       PHYSICAL_SCHEMAS=''.join(physical) or '<p>Sem warehouse nesta geração; consulte o contrato Arrow e o SQL incorporado.</p>',
                       OPERATING_SOURCES=table(['Arquivo incorporado','SHA-256'],hashes)+''.join(sources_code),
                       DOC_REVISION=DOC_REVISION, CODE_REVISION=text(os.getenv('GITHUB_SHA','Checkout local; consultar git rev-parse HEAD')),
                       RUN_COUNT=str(payload['meta']['retained_runs']), POINT_COUNT=str(payload['meta']['retained_observations']),
                       DISPLAY_RUN_COUNT=str(len(payload['runs'])), DISPLAY_POINT_COUNT=str(len(payload['points'])),
                       FIRST_OBSERVED=text(payload['meta']['history_first_observed_at']))
    for key, value in substitutes.items():
        template = template.replace('@@'+key+'@@',value)
    if re.search(r'@@[A-Z_]+@@', template):
        raise ValueError('Manual contém placeholder não preenchido')
    atomic(output, template.encode())
    return Path(output)
