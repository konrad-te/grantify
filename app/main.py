"""Serve an explicit project form and deterministic demo funding comparisons."""
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException
from app import ai_form, llm
from app.documents import DocumentError, MAX_FILE_BYTES, extract_document
from app.database import PROJECT_DIR
from app.structured import OPTIONS, read_form
from app.catalogue import load_catalogue, load_demo_catalogue, shortlist, DEMO_DATE
from app.followups import assess_answers
from app.readiness import review_project, review_project_ai

load_dotenv(PROJECT_DIR / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_catalogue()  # Fail early on malformed source data; leave the old demo DB untouched.
    load_demo_catalogue()
    yield


app = FastAPI(title="Gratify", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=PROJECT_DIR / "app" / "templates")


def mode_context(request):
    from app.catalogue import current_date
    demo = request.query_params.get('mode') == 'demo'
    return {'demo_mode': demo, 'mode_query': '?mode=demo' if demo else '',
            'reference_date': DEMO_DATE if demo else current_date()}


def demo_examples():
    data = json.loads((PROJECT_DIR / 'app/static/test-projects.json').read_text(encoding='utf-8'))
    return [case for case in data['cases'] if case.get('demo')]


def render(request, *, status=200, **context):
    examples = demo_examples()
    if 'selected_example' not in context:
        context['selected_example'] = next(
            (case for case in examples if case['description'] == context.get('description')), None)
    return templates.TemplateResponse(request=request, name="index.html", status_code=status,
        context={"options": OPTIONS, "values": {}, "field_errors": {},
                 **mode_context(request), 'demo_examples': examples,
                 'example_date': DEMO_DATE, **context})


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if request.query_params.get('example'):
        case = next((c for c in demo_examples() if c['id'] == request.query_params['example']), None)
        if case is None:
            raise StarletteHTTPException(status_code=404, detail='Unknown presentation example')
        use_form = request.query_params.get('mode') == 'demo' and request.query_params.get('prefill') == 'yes'
        return render(request, description=case['description'],
            values=case['expected_form'] if use_form else {},
            review_required=use_form, sample_form=use_form, selected_example=case)
    return render(request)


@app.get('/catalogue', response_class=HTMLResponse)
def catalogue_page(request: Request):
    from app.catalogue import availability
    mode = mode_context(request)
    programmes = load_demo_catalogue() if mode['demo_mode'] else load_catalogue()
    return templates.TemplateResponse(request=request, name='catalogue.html', context={
        **mode, 'programmes': programmes,
        'statuses': {p.id: availability(p, mode['reference_date'])[1] for p in programmes}})


@app.post("/prepare-profile", response_class=HTMLResponse)
async def prepare_profile(request: Request):
    form = await request.form(max_fields=5, max_files=0)
    description = str(form.get("description", "")).strip()
    if len(form.getlist("description")) != 1 or not 10 <= len(description) <= 5000:
        return render(request, status=422, description=description[:5000],
            preparation_error="Describe your project using 10 to 5,000 characters.", description_open=True)
    return await prepare_description(request, description)


@app.post("/prepare-document", response_class=HTMLResponse)
async def prepare_document(request: Request):
    try:
        async with request.form(max_fields=2, max_files=1) as form:
            upload = form.get("project_document")
            if not isinstance(upload, UploadFile) or not upload.filename:
                raise DocumentError("Choose a project document before preparing the form.")
            if upload.size is not None and upload.size > MAX_FILE_BYTES:
                raise DocumentError("The file is too large. Choose a document smaller than 5 MB.")
            data = await upload.read(MAX_FILE_BYTES + 1)
            description = await run_in_threadpool(extract_document, upload.filename, data)
            filename = upload.filename.replace("\\", "/").split("/")[-1][:200]
    except DocumentError as exc:
        return render(request, status=422, upload_error=str(exc), description_open=True)
    except StarletteHTTPException as exc:
        if exc.status_code != 400:
            raise
        return render(request, status=422, upload_error="Upload one project document at a time using the file picker.", description_open=True)
    return await prepare_description(request, description, uploaded_filename=filename)


async def prepare_description(request, description, **context):
    """Both text entry and uploads use one extraction call and the same review."""
    try:
        draft = await run_in_threadpool(ai_form.extract_form, description)
        values, evidence, missing, warnings = ai_form.prepare_form(description, draft)
    except llm.LLMError as exc:
        return render(request, status=503, description=description, description_open=True,
            preparation_error=str(exc), **context)
    return render(request, values=values, description=description, prepared=True,
        evidence=evidence, missing=missing, preparation_warnings=warnings, review_required=True, **context)


@app.post("/match", response_class=HTMLResponse)
async def find_funding(request: Request):
    form = await request.form(max_fields=50, max_files=0)
    values, errors, project = read_form(form)
    review_required = form.get("review_required") == "yes"
    description = str(form.get("draft_description", ""))[:5000]
    review_context = dict(description=description, review_required=review_required)
    if review_required and form.get("review_confirmed") != "yes":
        errors["review_confirmed"] = "Review the proposed answers and confirm them before finding funding."
    if errors:
        return render(request, status=422, values=values, field_errors=errors, **review_context)
    try:
        mode = mode_context(request)
        programmes = load_demo_catalogue() if mode['demo_mode'] else load_catalogue()
        groups = shortlist(project, programmes, mode['reference_date'])
        return render(request, values=values, programme_groups=groups, **review_context)
    except (OSError, ValueError):
        return render(request, status=503, values=values,
            **review_context,
            service_error="Could not read the programme catalogue. Please try again.")


@app.post("/check-programme", response_class=HTMLResponse)
async def check_programme(request: Request):
    """Narrow one shortlist lead using self-reported, source-backed answers."""
    form = await request.form(max_fields=60, max_files=0)
    values, errors, project = read_form(form)
    description = str(form.get("draft_description", ""))[:5000]
    review_context = {
        "description": description,
        "review_required": form.get("review_required") == "yes",
    }
    if errors:
        return render(request, status=422, values=values, field_errors=errors, **review_context)
    try:
        mode = mode_context(request)
        programmes = load_demo_catalogue() if mode["demo_mode"] else load_catalogue()
        groups = shortlist(project, programmes, mode["reference_date"])
    except (OSError, ValueError):
        return render(request, status=503, values=values, **review_context,
            service_error="Could not read the programme catalogue. Please try again.")
    programme_id = str(form.get("programme_id", ""))
    if len(form.getlist("programme_id")) != 1:
        raise StarletteHTTPException(status_code=400, detail="Choose one programme")
    row = next((item for group in ("candidates", "upcoming") for item in groups[group]
                if item["programme"].id == programme_id), None)
    if not row or not row["followups"]:
        raise StarletteHTTPException(status_code=400, detail="No follow-up questions for this programme")
    answers = {}
    answer_errors = []
    deep_review = programme_id == "eic-accelerator"
    for question in row["followups"]:
        evidence_field = f"evidence_{question.key}"
        unknown_field = f"unknown_{question.key}"
        evidence_values = form.getlist(evidence_field)
        unknown_values = form.getlist(unknown_field)
        evidence = str(evidence_values[0]).strip() if len(evidence_values) == 1 else ""
        unknown = unknown_values == ["yes"]
        answers[question.key] = {"status": "unknown" if unknown or not evidence else "supplied",
                                 "evidence": evidence[:800]}
        if len(evidence_values) != 1 or len(unknown_values) > 1:
            answer_errors.append(question.prompt)
        elif unknown and evidence:
            answer_errors.append(question.prompt)
        elif unknown:
            answers[question.key] = {"status": "unknown", "evidence": ""}
        elif (0 if deep_review else 20) <= len(evidence) <= 800:
            answers[question.key] = {"status": "supplied", "evidence": evidence}
        else:
            answer_errors.append(question.prompt)
    context = dict(values=values, programme_groups=groups, followup_programme_id=programme_id,
                   followup_answers=answers, **review_context)
    if answer_errors:
        return render(request, status=422,
                      followup_error=(
                          "Use one answer per question, up to 800 characters. Leave an answer blank if you do not know."
                          if deep_review else
                          "For each question, provide at least 20 characters of evidence or "
                          "choose “I don’t have this evidence yet.” Do not select both."
                      ),
                      **context)
    if deep_review:
        try:
            use_ai = form.get("review_method") == "ai"
            reviewer = review_project_ai if use_ai else review_project
            review = await run_in_threadpool(reviewer, description, answers, project)
        except llm.LLMError as exc:
            return render(request, status=503, followup_error=str(exc), **context)
        return render(request, readiness_review=review, **context)
    return render(request,
                  followup_assessment=assess_answers(programme_id, row["followups"], answers),
                  **context)
