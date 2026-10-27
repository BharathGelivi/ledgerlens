"""Local payment-data investigation workspace. No payment operations."""
import json
import os
import threading
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from pipeline import DATA, ROOT, active_database, connect, run

app = FastAPI(title='LedgerLens', description='Traceable payment-data investigations')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])
app.mount('/assets', StaticFiles(directory=ROOT / 'web'), name='assets')
job = {'running': False, 'error': None}
job_lock = threading.Lock()


@app.middleware('http')
async def local_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response


def rows(db, sql, parameters=None):
    result = db.execute(sql, parameters or [])
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, [str(v) if isinstance(v, Decimal) else v for v in row]))
            for row in result.fetchall()]


def database():
    if not active_database().exists():
        raise HTTPException(503, 'Build a dataset with pipeline.py before opening this workspace.')
    return connect(read_only=True)


def history():
    files = sorted((DATA / 'runs').glob('*/run.json'), reverse=True)[:30]
    return [json.loads(path.read_text(encoding='utf-8')) for path in files]


@app.get('/')
def index():
    return FileResponse(ROOT / 'web' / 'index.html')


@app.get('/activity')
def activity():
    with database() as db:
        return {'dataset': db.execute('select dataset from dataset_metadata').fetchone()[0],
                'note': 'Signed completed activity, not revenue or an account balance.',
                'rows': rows(db, 'select * from daily_activity order by activity_date_utc, currency')}


@app.get('/quality')
def quality():
    with database() as db:
        return {table: db.execute(f'select count(*) from {table}').fetchone()[0]
                for table in ('raw_records', 'valid_records', 'quarantine', 'payments')}


@app.get('/workspace')
def workspace():
    from briefing import ai_settings
    with database() as db:
        counts = {table: db.execute(f'select count(*) from {table}').fetchone()[0]
                  for table in ('raw_records', 'valid_records', 'quarantine', 'payments', 'conflicts')}
        recent = history()
        pointer = DATA / 'active.json'
        active = json.loads(pointer.read_text())['run_id'] if pointer.exists() else None
        active_run = next((r for r in recent if r['run_id'] == active), None)
        tests = []
        if active:
            result_file = DATA / 'runs' / active / 'dbt' / 'run_results.json'
            if result_file.exists():
                tests = [{'name': r['unique_id'].split('.')[2], 'status': r['status'],
                          'seconds': r['execution_time']} for r in json.loads(result_file.read_text())['results']
                         if r['unique_id'].startswith('test.')]
        return {'counts': counts, 'dataset': db.execute('select dataset from dataset_metadata').fetchone()[0],
                'activity': rows(db, 'select * from daily_activity order by activity_date_utc, currency'),
                'statuses': rows(db, 'select status, count(*) as records from payments group by 1 order by 1'),
                'currencies': rows(db, 'select distinct currency from payments order by 1'),
                'source_latest_update_utc': db.execute('select max(updated_at) from valid_records').fetchone()[0],
                'published_run': active_run, 'runs': recent, 'tests': tests, 'job': dict(job),
                'ai_connected': bool(ai_settings())}


@app.get('/transactions')
def transactions(search: str = Query('', max_length=100), status: str = Query('', max_length=1),
                 currency: str = Query('', max_length=3), page: int = Query(1, ge=1, le=100000)):
    if status and status not in ('S', 'P', 'D', 'V'):
        raise HTTPException(422, 'Unknown transaction status')
    conditions, parameters = ['transaction_id ilike ?'], ['%' + search + '%']
    for column, value in [('status', status), ('currency', currency)]:
        if value:
            conditions.append(column + ' = ?')
            parameters.append(value)
    where = ' and '.join(conditions)
    with database() as db:
        return {'total': db.execute('select count(*) from payments where ' + where, parameters).fetchone()[0],
                'page': page, 'rows': rows(db, 'select * from payments where ' + where +
                 ' order by updated_at desc, transaction_id, event_code limit 30 offset ?',
                 parameters + [(page - 1) * 30])}


@app.get('/trace')
def trace(transaction_id: str = Query(..., min_length=1, max_length=100),
          event_code: str = Query(..., pattern=r'^T\d{4}$')):
    with database() as db:
        versions = rows(db, '''select v.*, coalesce(sum(s.occurrences),0) as times_observed
            from valid_records v left join record_sightings s using(record_hash)
            where v.transaction_id=? and v.event_code=?
            group by all order by v.updated_at, v.record_hash''', [transaction_id, event_code])
        if not versions:
            raise HTTPException(404, 'No record with that transaction/event key')
        return {'versions': versions, 'current': rows(db,
                'select * from payments where transaction_id=? and event_code=?', [transaction_id, event_code]),
                'conflicts': rows(db, 'select * from conflicts where transaction_id=? and event_code=?',
                                  [transaction_id, event_code]),
                'meaning': 'Preserved versions → validated history → latest unambiguous state → currency/day summary.'}


@app.get('/issues')
def issues():
    with database() as db:
        return {'quarantine': rows(db, 'select record_hash, reason from quarantine order by record_hash limit 100'),
                'conflicts': rows(db, 'select * from conflicts order by updated_at desc limit 100')}


@app.get('/export')
def export():
    parquet = active_database().parent / 'daily_activity.parquet'
    if not parquet.exists():
        raise HTTPException(404, 'No published Parquet export yet')
    return FileResponse(parquet, filename='ledgerlens-daily-activity.parquet')


def same_origin(request):
    host = request.headers.get('host', '').split(':')[0]
    if host not in ('127.0.0.1', 'localhost') or request.headers.get('x-ledgerlens') != 'workspace':
        raise HTTPException(403, 'Use the local LedgerLens workspace for this operation')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin operations are disabled')


def rebuild(source):
    try:
        run(source)
    except Exception as error:
        job['error'] = 'Refresh failed (' + type(error).__name__ + '). Last published data remains available.'
    finally:
        job['running'] = False


@app.post('/replay')
def replay(request: Request, background: BackgroundTasks):
    same_origin(request)
    source = active_database().parent / 'input.json'
    if not source.exists():
        raise HTTPException(409, 'Run pipeline.py once to establish a replayable source snapshot')
    with job_lock:
        if job['running']:
            raise HTTPException(409, 'A refresh is already running')
        job.update(running=True, error=None)
    background.add_task(rebuild, source)
    return {'message': 'Replay started; the last passing dataset stays available while this runs.'}


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.post('/investigate')
def investigate(question: Question, request: Request):
    same_origin(request)
    from briefing import explain, aggregate_payload, ai_settings
    evidence = aggregate_payload()
    if not ai_settings():
        return {'mode': 'sql-evidence', 'answer': 'SQL evidence is ready below. Connect an AI API account to generate an explanation.',
                'evidence': evidence, 'question': question.question}
    try:
        return {'mode': 'cloud-ai', 'answer': explain(question.question, evidence), 'evidence': evidence,
                'question': question.question}
    except (RuntimeError, ValueError, OSError):
        raise HTTPException(502, 'AI explanation failed. SQL evidence remains available; check account/model access.') from None
