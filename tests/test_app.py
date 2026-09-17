"""Exercise the web workflow with a temporary database and fake AI responses."""

from unittest.mock import Mock
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base
from app.llm import LLMError
from app.models import Grant
from app.seed import seed_grants


@pytest.fixture
def client(monkeypatch):
    """Run the app against an in-memory database that is discarded after the test.

    Monkeypatch temporarily replaces the real database settings. TestClient
    runs startup so the sample grants are seeded, then shuts down the app."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "SessionLocal", sessionmaker(bind=engine))
    with TestClient(main.app) as client:
        yield client
    engine.dispose()


def test_home_and_static_assets(client):
    """Check that the form and its stylesheet and loading script are served."""
    page = client.get("/")
    assert "Find funding" in page.text
    assert "loading-status" in page.text
    assert "Your local model may need a little time" not in page.text
    assert client.get("/static/style.css").status_code == 200
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "Finding funding" in script.text


def test_seeding_is_idempotent(client):
    """Seed an already-seeded database again and confirm it still contains twelve grants."""
    with main.SessionLocal() as session:
        seed_grants(session)
        assert session.scalar(select(func.count()).select_from(Grant)) == 12


@pytest.mark.parametrize("streaming", [False, True])
def test_description_checklist_reflects_extracted_details(client, monkeypatch, profile, streaming):
    """Missing outcomes remain unchecked; zero employees still counts as provided."""
    home = client.get("/").text
    assert home.count('class="checklist-item"') == 8
    assert 'class="checklist-item is-found"' not in home
    profile.employees = 0
    profile.project_goal = None
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)
    monkeypatch.setattr(main, "score_grants", lambda *args: [])
    response = client.post(
        "/match", data={"description": "Polish manufacturing SME with a EUR 150,000 energy project."},
        headers={"Accept": "application/x-ndjson"} if streaming else {},
    )
    assert response.status_code == 200
    html = json.loads(response.text.splitlines()[-1])["html"] if streaming else response.text
    assert html.count('class="checklist-item is-found"') == 7
    assert 'Intended outcome or improvement<span class="checklist-status"> — Not identified' in html
    assert 'Number of employees<span class="checklist-status"> — Identified' in html


def test_form_filters_before_scoring_and_renders_ranked_results(
    client, monkeypatch, profile, make_relevance_score
):
    """Submit the form with fake AI results and verify filtering, ranking and displayed details."""
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)

    def score(description, extracted, grants):
        """Verify that only the seven eligible grants reach scoring, then supply predictable scores."""
        assert extracted == profile
        assert {grant.id for grant in grants} == set(range(1, 8))
        return [make_relevance_score(
            grant.id, 95 if grant.id == 2 else 40, ["Confirm annual revenue to assess the company's ability to finance the project."]
        ) for grant in grants]

    monkeypatch.setattr(main, "score_grants", score)
    response = client.post("/match", data={"description": "Polish manufacturing SME with a EUR 150,000 energy project."})
    assert response.status_code == 200
    assert response.text.index("Clean Production Fund") < response.text.index("Factory Energy Upgrade")
    assert "7 eligible opportunities" in response.text
    assert "5 excluded opportunities" in response.text
    assert "annual revenue" in response.text
    assert "Industry match" in response.text
    assert "Project explanation based on the inputs." in response.text
    assert "Relevance score: 95/100" in response.text
    assert "Country:</strong> Eligible" in response.text
    assert "Deadline:</strong> Open" in response.text
    assert "Energy efficiency" in response.text
    assert "Weight: 60%" in response.text
    assert "How the score is calculated" in response.text
    assert "Company Project need" in response.text
    assert "Grant Project scope" in response.text
    assert "Where it differs" in response.text
    assert "capped at" not in response.text
    assert '</dt><dd>Medium</dd>' in response.text
    assert 'aria-label="About assessment confidence"' in response.text
    assert "Needs clarification" in response.text
    assert "Important information is missing" not in response.text
    assert "100 requires every factor" not in response.text
    assert '<details class="match-details">' in response.text
    assert '<details class="match-details" open' not in response.text


def test_uncertainty_has_one_specific_section_and_separate_confidence(
    client, monkeypatch, profile, make_relevance_score
):
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)
    question = "Confirm <machinery replacement> costs because the programme does not explicitly cover this purchase."

    def score(description, extracted, grants):
        result = make_relevance_score(grants[0].id, 95, [question])
        result.project_type_match.confidence = "Medium"
        result.project_type_match.clarification = question
        result.project_type_match.improvement = question
        return [result]

    monkeypatch.setattr(main, "score_grants", score)
    response = client.post("/match", data={"description": "Polish manufacturing SME with a EUR 150,000 energy project."})
    assert "Relevance score: 95/100" in response.text
    assert "Very strong match" in response.text
    assert '</dt><dd>Medium</dd>' in response.text
    assert response.text.count("Needs clarification") == 1
    assert response.text.count("Confirm &lt;machinery replacement&gt;") == 1
    assert "Exact match" not in response.text
    assert "Exact fit" not in response.text
    assert "What could help:" not in response.text
    assert "Worth clarifying" not in response.text
    assert "Keep in mind" not in response.text
    assert "Within range" in response.text


def test_collapsed_card_shows_factor_reasons_and_hides_empty_clarifications(
    client, monkeypatch, profile, make_relevance_score
):
    from app.schemas import RelevanceScore

    monkeypatch.setattr(main, "extract_profile", lambda description: profile)
    reasons = [
        "The programme supports factory energy upgrades.",
        "Manufacturing is an explicitly supported industry.",
        "Your EUR 150,000 budget falls within the funding range.",
    ]

    def score(description, extracted, grants):
        data = make_relevance_score(grants[0].id, 95).model_dump()
        for field, reason in zip(("project_type_match", "industry_match", "funding_fit"), reasons):
            data[field].update(explanation=reason, clarification=[])
        data["missing_information"] = [None, "Null", "None", "", [], "[]"]
        return [RelevanceScore.model_validate(data)]

    monkeypatch.setattr(main, "score_grants", score)
    response = client.post("/match", data={"description": "Polish manufacturing SME with a EUR 150,000 energy project."})
    collapsed = response.text.split('<details class="match-details">')[0]
    assert all(reason in collapsed for reason in reasons)
    assert "Needs clarification" not in response.text
    assert "<dd>High</dd>" in collapsed
    assert 'aria-label="About assessment confidence"' in collapsed
    assert "How sure is this assessment?" in collapsed
    assert "This does not predict whether you will receive funding." in collapsed
    assert '<details class="info-tooltip"' not in collapsed
    assert 'class="confidence-info"' in collapsed
    assert 'role="tooltip" hidden' in collapsed


def test_profile_event_arrives_before_scoring(client, monkeypatch, profile):
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)
    scorer = Mock(return_value=[])
    monkeypatch.setattr(main, "score_grants", scorer)
    events = main.matching_events(Mock(), "A valid company description for testing")
    first = next(events)
    assert first["type"] == "profile"
    assert first["profile"]["country"] == "Poland"
    scorer.assert_not_called()
    events.close()


@pytest.mark.parametrize("fail_scoring", [False, True])
def test_stream_returns_profile_then_results_or_error(client, monkeypatch, profile, make_relevance_score, fail_scoring):
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)
    def score(description, extracted, grants):
        if fail_scoring:
            raise LLMError("The local model timed out. Please retry.")
        return [make_relevance_score(grant.id, 80) for grant in grants]
    monkeypatch.setattr(main, "score_grants", score)
    response = client.post("/match", data={"description": "Polish manufacturing SME with an energy project."},
                           headers={"Accept": "application/x-ndjson"})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["type"] for event in events] == ["profile", "complete"]
    assert events[-1]["status"] == (503 if fail_scoring else 200)
    assert ('timed out' if fail_scoring else '7 eligible opportunities') in events[-1]["html"]
    assert "What could help:" not in events[-1]["html"]
    assert "Needs clarification" not in events[-1]["html"]


def test_stream_validation_failure(client):
    response = client.post("/match", data={"description": "short"}, headers={"Accept": "application/x-ndjson"})
    event = json.loads(response.text)
    assert event["type"] == "complete"
    assert event["status"] == 422


def test_weak_project_explanation_is_visible_and_escaped(client, monkeypatch, profile, make_relevance_score):
    monkeypatch.setattr(main, "extract_profile", lambda description: profile)

    def score(description, extracted, grants):
        results = []
        for grant in grants:
            result = make_relevance_score(grant.id, 100)
            result.project_type_match.score = 10
            result.project_type_match.company_need = "Reduce factory energy consumption."
            result.project_type_match.grant_support = "Develop experimental software prototypes."
            result.project_type_match.explanation = "Equipment upgrades do not involve software research."
            result.project_type_match.improvement = "Look for an energy-efficiency programme. <script>bad()</script>"
            results.append(result)
        return results

    monkeypatch.setattr(main, "score_grants", score)
    response = client.post("/match", data={"description": "Polish manufacturing SME seeking energy upgrades for EUR 150000."})
    assert response.status_code == 200
    assert "Relevance score: 46/100" in response.text
    assert "Weak match" in response.text
    assert "Reduce factory energy consumption." in response.text
    assert "Develop experimental software prototypes." in response.text
    assert "Equipment upgrades do not involve software research." in response.text
    assert "What could help:" in response.text
    assert "&lt;script&gt;" in response.text
    assert "<script>bad()" not in response.text


def test_missing_profile_information_skips_scoring(client, monkeypatch, profile):
    """Remove the country and confirm the page asks for it without calling the scorer."""
    monkeypatch.setattr(main, "extract_profile", lambda description: profile.model_copy(update={"country": None}))
    scorer = Mock()
    monkeypatch.setattr(main, "score_grants", scorer)
    response = client.post("/match", data={"description": "Manufacturing SME with a EUR 150,000 project."})
    assert response.status_code == 422
    assert "include country" in response.text
    scorer.assert_not_called()


def test_no_eligible_grants(client, monkeypatch, profile):
    """Use an unsupported country and check that the page explains the empty shortlist."""
    monkeypatch.setattr(main, "extract_profile", lambda description: profile.model_copy(update={"country": "Canada"}))
    response = client.post("/match", data={"description": "Canadian manufacturing SME with a EUR 150,000 project."})
    assert response.status_code == 200
    assert "No sample programmes pass" in response.text


@pytest.mark.parametrize("description", ["", "   ", "short", "x" * 5001])
def test_invalid_form_does_not_call_ai(client, monkeypatch, description):
    """Check that empty, short and overlong descriptions are rejected before extraction."""
    extractor = Mock()
    monkeypatch.setattr(main, "extract_profile", extractor)
    assert client.post("/match", data={"description": description}).status_code == 422
    extractor.assert_not_called()


def test_api_error_is_readable_and_input_is_escaped(client, monkeypatch):
    """Check that an AI failure is readable and submitted HTML is displayed as escaped text."""
    monkeypatch.setattr(main, "extract_profile", Mock(side_effect=LLMError("Check your API key.")))
    description = "<script>alert('test')</script> Company description"
    response = client.post("/match", data={"description": description})
    assert response.status_code == 503
    assert "Check your API key." in response.text
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
