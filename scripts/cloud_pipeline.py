"""GitHub lifecycle: restore approved, prepare draft, deploy, confirm, retain two."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from admin_metrics.archive import pack, restore
from admin_metrics.storage import write

ROOT=Path('data')


def gh(*args):
    return subprocess.run(['gh',*args],check=True,text=True,capture_output=True).stdout


def releases():
    pages=json.loads(gh('api','--paginate','--slurp','repos/{owner}/{repo}/releases?per_page=100'))
    return [r for page in pages for r in page]


def approved(items):
    return sorted([r for r in items if r['tag_name'].startswith('state-') and not r['draft'] and not r['prerelease']],key=lambda r:(r['published_at'],r['id']),reverse=True)


def download(tag):
    with tempfile.TemporaryDirectory(prefix='admin-restore-') as temporary:
        for pattern in ('state.zip','SHA256SUMS'):
            gh('release','download',tag,'--pattern',pattern,'--dir',temporary)
        return restore(Path(temporary)/'state.zip',Path(temporary)/'SHA256SUMS',ROOT)


def prepare(refresh=False):
    history=approved(releases())
    if history:
        download(history[0]['tag_name'])
    from admin_metrics.pipeline import run
    payload=run(ROOT,Path('site'),refresh=refresh or not history)
    # A presentation-only deploy must not create a fake observation or duplicate state.
    if not refresh and history:
        return ''
    tag='state-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
    destination=Path('.runtime/package'); destination.mkdir(parents=True,exist_ok=True)
    manifest=pack(ROOT,destination/'state.zip')
    body={'data_run_id':manifest['run_id'],'workflow_run_id':os.environ['GITHUB_RUN_ID'],
          'source_sha':os.environ['GITHUB_SHA'],'purpose':'approved-monitor-state'}
    write(destination/'release-body.json',body)
    gh('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title','Admin Metrics · '+tag,'--notes-file',str(destination/'release-body.json'))
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as stream:stream.write('candidate_tag='+tag+'\n')
    gh('release','upload',tag,str(destination/'state.zip'),str(destination/'SHA256SUMS'))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as stream:
            stream.write('## Observação Admin\n\nRun: `'+payload['meta']['run_id']+'`\n\n')
            for report in payload['runs'][-1]['reports']:
                stream.write(f"- {report['label']}: HTTP {report['status']}, {report['records']} identidades, issues: {report['issues']}\n")
    return tag


def promote(tag):
    release=json.loads(gh('release','view',tag,'--json','body,isDraft'))
    body=json.loads(release['body'])
    if not tag.startswith('state-') or body.get('purpose')!='approved-monitor-state':
        raise ValueError('Release fora do ciclo operacional')
    jobs=json.loads(gh('api',f"repos/{{owner}}/{{repo}}/actions/runs/{body['workflow_run_id']}/jobs?per_page=100"))['jobs']
    proof=next((j for j in jobs if j['name']=='deploy' and j['status']=='completed' and j['conclusion']=='success'),None)
    if not proof:
        raise ValueError('Não há recibo de deploy concluído com sucesso para este candidato')
    receipt={'data_run_id':body['data_run_id'],'workflow_run_id':body['workflow_run_id'],
             'deploy_job_id':proof['id'],'completed_at':proof['completed_at'],'source_sha':body['source_sha']}
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary)/'deployment-receipt.json';write(path,receipt)
        gh('release','upload',tag,str(path),'--clobber')
    gh('release','edit',tag,'--draft=false','--latest=false')
    for old in approved(releases())[2:]:
        gh('release','delete',old['tag_name'],'--yes','--cleanup-tag')


def discard(tag):
    record=json.loads(gh('release','view',tag,'--json','isDraft'))
    if not tag.startswith('state-') or not record['isDraft']:
        raise ValueError('Somente candidatos draft podem ser descartados')
    gh('release','delete',tag,'--yes','--cleanup-tag')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','promote','discard','restore'])
    parser.add_argument('--refresh',action='store_true');parser.add_argument('--tag')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.refresh)
    elif args.command=='promote':promote(args.tag)
    elif args.command=='discard':discard(args.tag)
    else:download(args.tag)
