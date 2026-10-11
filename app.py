"""Stateless Swedish text sonification; uploaded texts are never persisted."""
import base64
import csv
import io
from pathlib import Path
import tempfile
import threading
import zipfile

from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from vendor import engine
from sonification import sonify

ROOT = Path(__file__).parent
MAX_BYTES = 2 * 1024 * 1024
MAX_CHARS = 120_000
MAX_WORDS = 12_000
_slots = threading.BoundedSemaphore(2)
app = FastAPI(title='Textklang', docs_url=None, redoc_url=None)

@app.middleware('http')
async def headers(request, call_next):
    # Bound the entire incoming request before multipart parsing, including
    # chunked requests. Files are never accepted beyond this memory budget.
    if request.method == 'POST':
        messages, received = [], 0
        while True:
            message = await request._receive()
            if message['type'] == 'http.disconnect':
                return JSONResponse({'detail': 'Uppladdningen avbröts.'}, status_code=400)
            received += len(message.get('body', b''))
            if received > MAX_BYTES + 65536:
                return JSONResponse({'detail': 'Filen är för stor. Max 2 MB.'}, status_code=413)
            messages.append(message)
            if not message.get('more_body', False):
                break
        original = request._receive
        async def replay_receive():
            if messages:
                return messages.pop(0)
            return await original()
        request._receive = replay_receive
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')

@app.get('/api/health')
def health():
    return {'status': 'ok', 'engine': '2.10'}

def extract_docx(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 1000 or sum(i.file_size for i in infos) > 10 * 1024 * 1024:
                raise ValueError('Dokumentet är för stort efter uppackning.')
        doc = Document(io.BytesIO(data))
        # Preserve paragraph/table order, including nested tables.
        def blocks(container):
            for block in container.iter_inner_content():
                if hasattr(block, 'text'):
                    yield block.text
                else:
                    for row in block.rows:
                        seen = set()
                        for cell in row.cells:
                            if cell._tc not in seen:
                                seen.add(cell._tc)
                                yield from blocks(cell)
        return '\n'.join(blocks(doc))
    except Exception as exc:
        raise HTTPException(422, 'DOCX-filen kunde inte läsas. Använd ett giltigt Word-dokument eller TXT.') from exc

def analyze(text):
    if not _slots.acquire(blocking=False):
        raise HTTPException(503, 'Analysen är upptagen. Försök igen om en stund.')
    try:
        if not text.strip() or not engine.tokenize(text):
            raise HTTPException(422, 'Lägg in en text med minst ett ord.')
        if len(text) > MAX_CHARS or len(engine.tokenize(text)) > MAX_WORDS:
            raise HTTPException(413, 'Texten är för lång. Max 12 000 ord och 120 000 tecken.')
        report = engine.build_report(text, 'sv')
        with tempfile.TemporaryDirectory(prefix='textklang-') as directory:
            output = Path(directory) / 'analysis.wav'
            info, events = sonify(text, output)
            audio = base64.b64encode(output.read_bytes()).decode('ascii')
        info.pop('wav', None)
        report['audio'] = info
        report['timeline'] = events
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(['feature', 'value'])
        writer.writerows(report['features'].items())
        return {'report': report, 'audio_base64': audio, 'csv': stream.getvalue()}
    finally:
        _slots.release()

@app.post('/api/analyze')
async def analyze_endpoint(text: str = Form(''), file: UploadFile | None = File(None)):
    if file is not None and file.filename:
        try:
            data = await file.read(MAX_BYTES + 1)
        finally:
            await file.close()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, 'Filen är för stor. Max 2 MB.')
        suffix = Path(file.filename).suffix.lower()
        if suffix == '.txt':
            try:
                text = data.decode('utf-8-sig')
            except UnicodeDecodeError as exc:
                raise HTTPException(422, 'TXT-filen behöver vara UTF-8-kodad.') from exc
        elif suffix == '.docx':
            text = await run_in_threadpool(extract_docx, data)
        else:
            raise HTTPException(422, 'Välj en TXT- eller DOCX-fil.')
    return await run_in_threadpool(analyze, text)

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
