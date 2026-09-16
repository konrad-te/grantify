"""Connect the web form, profile extraction, eligibility checks and ranked results."""

from contextlib import asynccontextmanager
import json
from typing import Annotated, AsyncIterator, Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, PROJECT_DIR, SessionLocal, engine
from app.llm import LLMError, extract_profile, score_grants
from app.matching import check_eligibility, profile_problems, rank_scores
from app.models import Grant
from app.seed import seed_grants


load_dotenv(PROJECT_DIR / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare the database before FastAPI starts accepting requests.

    Create any missing tables and seed them if empty. The session closes
    before yield, which hands control back to FastAPI to serve the app."""
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed_grants(session)
    yield


app = FastAPI(title="Gratify", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=PROJECT_DIR / "app" / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Render the initial form with no profile, results or errors yet."""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.post("/match", response_class=HTMLResponse)
def find_funding(request: Request, description: Annotated[str, Form()] = ""):
    """Serve normal HTML, or progress events for the small browser enhancement."""
    events = matching_events(request, description)
    if "application/x-ndjson" in request.headers.get("accept", ""):
        return StreamingResponse(
            (json.dumps(event) + "\n" for event in events),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )
    for event in events:
        if event["type"] == "complete":
            return HTMLResponse(event["html"], status_code=event["status"])


def matching_events(request: Request, description: str) -> Iterator[dict]:
    """Turn a submitted description into a results page.

    Validate the text, ask Ollama for a profile, then check that required
    details are present. Load grants, apply Python eligibility rules and
    ask Ollama to score the survivors. Join sorted scores to grant details
    for the template. Input problems return HTTP 422; AI or database
    failures return HTTP 503 with a readable message on the same page."""
    description = description.strip()
    # Context is the collection of values Jinja uses to fill in the HTML page.
    context = {"description": description}
    status_code = 200
    try:
        if not 20 <= len(description) <= 5000:
            context["errors"] = ["Enter a company and project description between 20 and 5,000 characters."]
            status_code = 422
        else:
            # Extract first, then stop early if the profile is not ready for matching.
            profile = extract_profile(description)
            context["profile"] = profile.model_dump(exclude={"source_phrases"})
            yield {"type": "profile", "profile": profile.model_dump()}
            problems = profile_problems(profile)
            if problems:
                context["errors"] = problems
                status_code = 422
            else:
                # Read the grants and close the database session before waiting for AI.
                with SessionLocal() as session:
                    grants = list(session.scalars(select(Grant).order_by(Grant.id)))
                eligible_grants = []
                eligibility_by_grant_id = {}
                excluded = []
                for grant in grants:
                    eligibility = check_eligibility(profile, grant)
                    if eligibility.eligible:
                        eligible_grants.append(grant)
                        eligibility_by_grant_id[grant.id] = eligibility
                    else:
                        excluded.append({"grant": grant, "reasons": eligibility.reasons})
                context["excluded"] = excluded
                # Score only survivors, then attach full grant details to each sorted score.
                scores = rank_scores(score_grants(description, profile, eligible_grants))
                grants_by_id = {grant.id: grant for grant in eligible_grants}
                context["results"] = [
                    {
                        "grant": grants_by_id[score.grant_id],
                        "eligibility": eligibility_by_grant_id[score.grant_id],
                        "relevance": score,
                    }
                    for score in scores
                ]
    except LLMError as exc:
        context["errors"] = [str(exc)]
        status_code = 503
    except SQLAlchemyError:
        context["errors"] = ["Could not read the local grant database. Restart the app and try again."]
        status_code = 503
    html = templates.get_template("index.html").render(request=request, **context)
    yield {"type": "complete", "html": html, "status": status_code}
