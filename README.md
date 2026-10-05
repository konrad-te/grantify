# Gratify

An English-language pilot for startups and SMEs exploring **European innovation, international R&D and environmental funding**. The catalogue contains **10 real programmes and call tracks**, with official English sources reviewed on **4 October 2026**. This is a conservative topic shortlist, not an eligibility decision or a live funding search.

## Run locally — Bash

Use Python 3.11 or newer from the project directory:

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Open [the app](http://127.0.0.1:8000) or [the presentation demo](http://127.0.0.1:8000/?mode=demo).
If a server was started without reload, restart it after changing code.

## Presenting the project

Presentation mode has a visible banner and uses a **frozen catalogue and fixed reference date, 2026-10-04**. It never moves real deadlines forward. The separate current-date mode checks today's date in Europe/Warsaw against the manually maintained catalogue; it does not fetch live programme updates.

Three English examples are available: software startup, innovative manufacturing, and recycling/water reuse.

- **Load description** lets you demonstrate the real AI preparation flow.
- **Load sample form** loads authored, editable example answers without AI. It is explicitly labelled as sample data, not AI output, and requires review before searching.
- Results show why each programme appeared, what needs checking, and its official English source. Closed calls are in a separate archive.
- The recycling example deliberately has only archived matches at the demo date. That is the correct result, not a broken search.
- Mode stays active through preparation, uploads, validation errors, results and catalogue navigation. Switching modes starts a fresh form.

See [the English presentation and testing guide](docs/PILOT_TESTS.md).

## Optional AI-assisted form

Manual entry, sample forms and matching work without Ollama. For **Prepare my form**, run the model configured by `OLLAMA_MODEL` in `.env` (default `qwen3:8b`); `OLLAMA_URL` defaults to `http://localhost:11434`. Existing environment variables override `.env`. For the default model:

```bash
ollama pull qwen3:8b
```

Preparation makes one structured extraction request. It does not send programme data or ask AI to rank funding. Quotes, numeric roles, currency and conservative activity vocabulary are checked. Missing or uncertain facts remain blank; employee count does not establish SME status. These checks do not prove semantic accuracy: review and correct every field before confirming. A failed model call preserves the description and allows manual entry. Preparing a new draft replaces previous answers.

Descriptions are limited to 5,000 characters. Gratify does not persist descriptions, uploaded files, suggestions or searches; the configured model service has its own data-handling behaviour.

### Document upload

Upload PDF, Word `.docx`, or UTF-8 `.txt`: maximum 5 MB and 5,000 extracted characters; PDFs up to 30 pages. Scans need OCR first and encrypted PDFs are rejected. DOCX body paragraphs and tables are supported, not embedded images, headers or footers. Oversized text is rejected rather than truncated. Extracted text uses the same AI preparation and review process. Document content is untrusted data, not instructions.

## Matching rules and limitations

1. The pilot focuses on startups and SMEs. Each record lists its **reviewed country coverage**. This is not a universal list of eligible countries: for example, EIC coverage is currently mapped only for EU countries and the UK, although other associated countries can qualify. Unmapped countries receive an explicit coverage explanation.
2. Selected activities must overlap editorial topic tags. Research partners, specific challenge topics, technology stage, prior EU-funded research, sector and ownership restrictions still require review.
3. Only a recorded cash-award maximum in the same currency is checked against the request. EUR and PLN are accepted without conversion. Unknown caps remain unassessed. An indicative grant amount or mixed grant/equity ceiling is not treated as a hard cap. Innowwide's fixed-grant structure, minimum eligible costs, company age and other conditions remain explicit manual checks.
4. Call dates come from linked official sources. Closed/cancelled calls are archived; upcoming calls are separate. Unknown opening dates or rolling/national funding routes do not imply an open call. Exact cutoff times must be checked at source.
5. Sources older than 30 days are labelled as needing a schedule recheck; known closed calls remain archived. The demo uses its fixed date and frozen source records.
6. Ranking uses activity overlap, then title and ID. There is no AI ranking or eligibility percentage. Industry, employees and intended outcomes are context, not eligibility filters.

Required form fields: company country, company size, industry, activities, requested funding, total cost and currency. Positive amounts use plain digits and up to two decimal places; requested funding cannot exceed total cost. Other selections require a description. Validation preserves entered answers.

The ten records cover EIC Accelerator, Pathfinder Open, Pathfinder Challenges, Transition, Eurostars, Innowwide, Eureka Network Projects, LIFE Circular Economy, LIFE Climate, and LIFE Clean Energy Transition–INDUSTRY. These include related tracks, archived calls and different support instruments—not ten unrelated or currently open grants.

## Maintaining the data

- `app/data/programmes.json`: active manually maintained European catalogue.
- `app/data/demo-europe-2026-10-04.json`: frozen presentation snapshot. Do not change this when refreshing current data.
- `app/data/archive/poland-2026-10-04.json`: preserved previous Polish catalogue.
- `app/static/test-projects.json`: 20 authored English descriptions, expected forms and outcomes.
- `app/catalogue.py`: source validation, country coverage, date and amount checks.
- `app/main.py`: preparation, review, demo mode, catalogue and matching routes.
- `app/ai_form.py`: structured extraction and evidence checks.
- `app/structured.py`: shared choices and server-side form validation.

Before refreshing an active record, open its official programme, country and schedule sources. Update facts and `reviewed_on`; leave unverified values null. The old SQLite demo and experimental scoring code are retained but are not searched or seeded by the web app. No database reset is needed.

## Verify

```bash
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m tools.evaluate_pilot
./.venv/Scripts/python.exe -m tools.evaluate_pilot --live --limit 3
```

The first evaluation uses authored form answers with the frozen snapshot and no AI. The `--live` evaluation sends fictional descriptions to the configured Ollama service and reports extraction differences too. Remove `--limit 3` to evaluate all 20 cases. Reports go to standard output; differences or service errors return a nonzero exit code. Passing deterministic tests does not establish live AI accuracy. English extraction is the intended use; other languages have not been validated.
