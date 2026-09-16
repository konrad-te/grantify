# Gratify

A small learning MVP that matches a company/project description to **12 fictional funding opportunities**. One FastAPI application serves a plain HTML form, reads grants from SQLite, filters eligibility with Python, and uses a local Ollama model for profile extraction and relevance scoring.

```text
Company description
→ structured profile extraction
→ deterministic eligibility filtering
→ AI relevance scoring
→ ranked funding opportunities
```

## Install and run (Windows PowerShell)

Use Python 3.11 or newer. Run these commands from the Gratify directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen3:8b
```

Ollama must be running at `http://localhost:11434`. The defaults require no
`.env` file. To override them, copy `.env.example` to `.env` and edit:

```dotenv
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

`.env` is ignored by Git, and existing environment variables take precedence.
Restart Gratify after changing these settings. The configured Ollama model must
support structured JSON output.

Start the app:

```powershell
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**. The database is created and seeded automatically on the first startup. No separate database server or setup command is needed.

If PowerShell prevents activation, use the virtual environment's executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate`; create `.env` with `cp .env.example .env`. The remaining commands are the same.

### Try this description

> Polish manufacturing SME with 35 employees. We want funding for a project that improves energy efficiency in our factory through motor upgrades and heat recovery. Estimated total project cost is EUR 150,000.

On a freshly seeded database this passes the hard rules for seven programmes. The AI scores three relevance factors for each survivor, and Python combines them using fixed weights to determine the ordering. The exact factor scores may vary. Five grants are excluded because of country, company size, budget or an expired deadline. A software programme can pass eligibility and still receive a low relevance score.

## Guided reading: how to explain the project

Read these sections in order. Each Python function now has a plain-language
docstring directly below its definition; longer functions also have comments
at the main transitions.

1. **Start with `app/main.py`:** `lifespan()` prepares the database, `home()`
   shows the form, and `find_funding()` connects the entire search workflow.
   The route decorators connect browser URLs to Python functions.
2. **Understand the data in `app/schemas.py` and `app/models.py`:**
   `CompanyProfile` is the extracted company information, `Grant` is a database
   row, `EligibilityResult` is a pass/fail decision with four visible checks,
   and `RelevanceScore` holds three explained AI factors whose weighted score is calculated by Python. Pydantic checks data values; SQLAlchemy maps
   database rows to Python objects.
3. **Follow `app/llm.py`:** `extract_profile()` makes the first AI request.
   `_structured_request()` handles the shared request and reply validation.
   `score_grants()` makes the second request after eligibility checks.
4. **Read `app/matching.py`:** `profile_problems()` checks whether enough
   information is available, `check_eligibility()` collects failing rules,
   and `rank_scores()` puts the strongest relevance scores first.
5. **See where the grants come from:** `app/database.py` configures SQLite;
   `seed_grants()` in `app/seed.py` inserts the fictional examples once.
6. **Follow the response into `app/templates/index.html`:** the route's
   `context` dictionary supplies the profile, results, exclusions and errors.
   `app/static/app.js` shows extraction, profile chips and comparison progress before revealing the results.
7. **Use the tests as worked examples:** start with `tests/test_matching.py`,
   then `tests/test_llm.py`, then `tests/test_app.py`. A fixture is reusable test
   setup, `parametrize` repeats a test for several inputs, and `monkeypatch`
   temporarily replaces a dependency so tests can control its behavior.

### A short explanation you can give aloud

“The user describes their company and project in a web form. Ollama turns that
text into structured fields. Python checks that the required information is
present, reads the fictional grants from SQLite, and filters them by country,
company size, deadline and budget. Ollama then scores the relevance of the
eligible grants across three visible factors. Python validates the returned grant IDs,
weights and sorts the scores, and renders the results page, including reasons for excluded grants. Eligibility
and relevance are separate: passing the rules does not guarantee a good fit
or funding approval.”

## Architecture: each major file

| File | What it does and why it exists | Input → output or change |
| --- | --- | --- |
| `app/main.py` | Starts FastAPI, loads settings, handles the two routes and connects the steps. This is the place to read the whole workflow. | GET `/` → form HTML. POST `/match` with description → results or readable errors. Startup → creates/seeds database. |
| `app/database.py` | Defines the SQLite connection, session factory and shared SQLAlchemy base. A session is a short-lived object used to query the database. | Project directory → connection to `gratify.db` inside this directory. |
| `app/models.py` | Describes the `grants` table. SQLAlchemy maps each row to a Python `Grant` object. | Stored columns → grant objects with country lists, ranges, deadlines and other fields. |
| `app/schemas.py` | Defines Pydantic data shapes and constraints for AI output and eligibility results. It also calculates the weighted final score from three validated factors and converts internal factor scores to plain labels. These are validation models, separate from database tables. | Structured data → validated profile, eligibility checks or relevance breakdown; invalid data raises an error. |
| `app/seed.py` | Adds the fictional examples so the application works without scraping or a real data provider. | An empty database session → 12 inserted grants. A populated database is left alone. |
| `app/matching.py` | Contains readable hard rules, creates the four eligibility checks, checks for missing profile details and sorts results. It makes no API calls. | Profile + grant + date → `eligible` boolean, check statuses and failure reasons. Scores → sorted scores. |
| `app/llm.py` | Contains the only external integration and both prompts. A small shared helper avoids repeating API setup and error handling. | Description → profile; description + profile + eligible grants → three explained relevance factors per grant. API/validation problems → user-readable `LLMError`. |
| `app/templates/index.html` | Jinja2 fills one HTML page with form values, the extracted profile, results and excluded grants. Text is escaped automatically. | Route context → HTML the browser can display. |
| `app/static/style.css` | Adds basic spacing, colours, responsive layout, focus outlines and the loading spinner animation. | HTML elements → readable presentation. |
| `app/static/app.js` | Enhances the form with a short matching sequence. It highlights verified excerpts from the input, builds chips from the extracted profile, and reveals the server-rendered shortlist. | One streamed form request → profile progress → results or a readable error. |
| `tests/conftest.py` | Provides reusable example inputs for tests. | Test request → independent sample profile and grant. |
| `tests/test_matching.py` | Checks hard rules, inclusive boundaries, missing inputs, relevance separation and ranking. | Known inputs → assertions against expected decisions. |
| `tests/test_app.py` | Checks the form-to-results flow using an isolated in-memory SQLite database and mocked AI functions. | Test HTTP requests → verified HTML, filtering order and error handling. |
| `tests/test_llm.py` | Checks ranking IDs, Ollama request configuration, validation and HTTP errors with fake responses. | Mock API responses → validated output or readable errors, without running a model. |
| `requirements.txt` | Lists the runtime and test dependencies with version bounds. | pip install → dependencies. |
| `.env.example` | Shows the optional local URL and model overrides. | Ollama settings → server configuration. |

`app/__init__.py` marks the directory as a Python package. `pytest.ini` tells pytest where the tests and imports are. `.gitignore` excludes credentials, the virtual environment, caches and the generated database.

Country, company-size, industry and project-type lists are stored in SQLite JSON columns. For twelve grants this is easier to understand than separate relationship tables; Python reads those lists directly.

## Lifecycle of one request

1. The user presses **Find funding**. A small script disables the button and shows the original description while extraction runs. It posts the form to `/match` with `Accept: application/x-ndjson`. The same route also supports ordinary HTML submissions when JavaScript is unavailable.
2. `main.py` strips surrounding whitespace and checks the description length (20–5,000 characters).
3. `llm.extract_profile()` sends the description to Ollama's local `/api/chat` endpoint. The request includes the JSON schema generated from the `CompanyProfile` Pydantic model, including optional exact `source_phrases` for highlighting. Unknown details should come back as `null`; negative budgets and invalid field values fail validation. The server sends the extracted profile as one progress event before scoring. The browser highlights only phrases found in the original text, then displays profile chips and a comparison message. The chips reflect the actual extraction, not a keyword-search simulation.
4. Python checks that country, size, industry, project type, total project budget and currency were provided. Missing details or a non-EUR budget produce a message asking the user to update the description. Employee count is optional. The extracted profile is displayed so the user can spot mistakes.
5. SQLAlchemy loads the twelve grant rows from SQLite. The database session closes before relevance scoring.
6. `check_eligibility()` runs on each grant. Country, company size, deadline and budget decide whether it passes. It returns four check statuses for the UI, and every failing rule contributes an explanation. Industry and project type are relevance signals, not hard exclusions in this demo.
7. `llm.score_grants()` sends **only eligible grants** to Ollama in a single batch. For each grant it returns explained scores for industry match, project goal match and funding fit, plus important missing information. It does not score country, company size or deadline. If none pass eligibility, this API call is skipped.
8. Pydantic validates every factor score, and Python checks that every expected grant ID appears exactly once. Missing, duplicate and invented IDs cause a readable error instead of a partial or mismatched ranking.
9. Python combines project fit (60%), industry match (25%) and funding fit (15%). When important information is missing, the overall score cannot exceed 94. Python sorts the final scores highest first, with grant ID as a stable tie-breaker. A final event carries the Jinja2-rendered HTML and result status. The browser reveals compact cards showing the name, score, funding, deadline, eligibility, main reason and top concern. Factor evidence, suggestions and arithmetic stay in a closed “View match details” section. Excluded grants stay in their own expandable section.

The browser uses a single streaming response containing newline-separated JSON events; there are no extra model calls, queues or saved jobs. Errors arrive in the final event and restore the form for retry. The animation adds only short transitions and respects reduced-motion preferences. Missing suggestion values—including model-generated strings such as `"Null"`—are normalized to empty values and never shown as advice.

### Understanding the relevance score

The weights are simple product choices: project fit dominates because a grant should support the activity the company actually plans. Industry adds context, while funding fit contributes less so that an affordable but unrelated grant cannot look like a strong match.

For example, project fit 20, industry match 90 and funding fit 80 produce:

```text
20 × 60% + 90 × 25% + 80 × 15% = 46.5 → 46/100
```

Python uses `round()` to round to the nearest integer (ties go to the nearest even integer). The card shows the exact contributions, rounded result and any 94-point cap for missing information. Rounding cannot produce 100 unless all three factors are 100. These weights are transparent rules for this MVP, not a statistically calibrated prediction of funding success.

Each factor requires the actual company need, what the grant supports, and a specific explanation. Weak matches should identify the unsupported goal or sector. Optional improvements must be realistic and conditional; the model should not invent grant conditions or recommend disguising a project. Numeric factor scores are available in the expandable calculation, while the main factor headings use readable labels.

An ordinary search uses two sequential API calls: extraction and batch scoring. Requests have a two-minute timeout each and no automatic retries because a multi-grant structured response can take time on local hardware. FastAPI runs the synchronous route in its worker thread pool, keeping the code linear and beginner-friendly. No queues, agents or extra services are involved.

## Python rules versus AI

**Deterministic Python:** form validation, missing-field checks, EUR requirement, country/size membership, deadline comparison, budget bounds, the four eligibility statuses, grant-ID verification, weighting the three relevance factors, converting factor numbers into labels, applying the missing-information cap, sorting and database access.

**AI:** interpreting the description into fields, scoring industry match, project goal match and funding fit, and writing a short explanation for each one. Schema validation verifies the shape of AI output, not whether its interpretation is true. Factor scores are subjective and can differ between requests. They do not change hard eligibility decisions.

The Ollama URL, model name, request format and error mapping all live in `app/llm.py`. The rest of the application only knows the `extract_profile()` and `score_grants()` functions, so the provider remains behind a small, clear boundary.

The integration uses Ollama's local chat API with a Pydantic-generated JSON schema and non-streaming responses. The description stays on the machine running Ollama; this app does not save searches or company profiles in SQLite.

## Demo assumptions

- All grants, ranges, deadlines and `example.com` source links are fictional. They are not current funding advice or real application links.
- All amounts are EUR. The demo compares **total project budget directly with the funding range**, inclusively. Real programmes may distinguish eligible costs, requested grant amount, co-funding rates and maximum awards; these are not modelled yet.
- Company size must be stated as SME (including micro/small/medium) or large. Employee count alone does not establish the classification.
- Deadlines remain open throughout the displayed date, using the server's local date. They are assigned relative to the first seed date and stored unchanged, so they eventually expire.
- Seed changes do not overwrite an existing database. To regenerate fictional data, stop the app, delete only `gratify.db` in the Gratify directory and restart.
- No user accounts, saved searches, scraping, deployment infrastructure or background jobs are included.

## Tests

```powershell
python -m pytest -q
```

Tests use in-memory SQLite and mocked Ollama responses. They do not alter your `gratify.db` or require Ollama to be running. A successful live search is still needed to verify the local model and real model behaviour.

## Troubleshooting

- **Cannot reach Ollama:** start the Ollama application or run `ollama serve`, then retry.
- **Model not found:** run `ollama pull qwen3:8b`.
- **Request rejected:** check `OLLAMA_URL`, `OLLAMA_MODEL` and the Ollama logs.
- **Missing profile details:** explicitly include the requested fields in the textarea. Use EUR for the budget.
- **No eligible programmes:** expand the excluded list to see which hard rules failed.

## Possible later improvements — not implemented

Start with real funding data and more accurate eligibility fields, then consider editable extracted profiles and saved searches. Funding APIs or ingestion, semantic search/embeddings or RAG, document analysis, application assistance, accounts and notifications can be added when needed. React, PostgreSQL, Docker and cloud deployment are future options, not requirements for learning this MVP.
