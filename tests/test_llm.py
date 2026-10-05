"""Replace Ollama with fake HTTP replies to check requests, validation and errors."""

import json

import httpx
import pytest

from app import llm
from app.schemas import RelevanceBatch


RealClient = httpx.Client


def use_fake_ollama(monkeypatch, handler):
    """Route the request through an in-memory HTTP handler instead of local Ollama."""
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        llm.httpx,
        "Client",
        lambda **kwargs: RealClient(transport=transport, **kwargs),
    )


@pytest.mark.parametrize("ids", [[1, 1], [], [999]])
def test_scoring_rejects_duplicate_missing_or_unknown_ids(
    monkeypatch, profile, grant, ids, make_relevance_score
):
    """Supply each bad ID list and confirm scoring rejects an inconsistent batch."""
    batch = RelevanceBatch(results=[make_relevance_score(i, 87) for i in ids])
    monkeypatch.setattr(llm, "_structured_request", lambda *args: batch)
    with pytest.raises(llm.LLMError, match="incomplete or inconsistent"):
        llm.score_grants("Company description", profile, [grant])


def test_no_grants_requires_no_ollama_request(monkeypatch, profile):
    """Confirm an empty shortlist returns immediately without contacting Ollama."""
    request = lambda *args, **kwargs: pytest.fail("Ollama should not be called")
    monkeypatch.setattr(llm, "_structured_request", request)
    assert llm.score_grants("Company description", profile, []) == []


def test_scoring_sends_all_factor_inputs(monkeypatch, profile, grant, make_relevance_score):
    """Give the scorer the actual values needed to explain all three factors."""
    captured = {}

    def structured_request(instructions, data, schema):
        captured["instructions"] = instructions
        captured["data"] = json.loads(data)
        captured["schema"] = schema.model_json_schema()
        return RelevanceBatch(results=[make_relevance_score(grant.id, 80)])

    monkeypatch.setattr(llm, "_structured_request", structured_request)
    result = llm.score_grants("Company description", profile, [grant])

    sent_grant = captured["data"]["grants"][0]
    assert "countries" not in sent_grant
    assert "company_sizes" not in sent_grant
    assert sent_grant["minimum_funding"] == 20000
    assert sent_grant["maximum_funding"] == 300000
    relevance_properties = captured["schema"]["$defs"]["RelevanceScore"]["properties"]
    assert "industry_match" in relevance_properties
    assert "project_type_match" in relevance_properties
    assert "funding_fit" in relevance_properties
    assert "company_size_match" not in relevance_properties
    assert "geographic_match" not in relevance_properties
    assert "score" not in relevance_properties
    assert "Do not reassess eligibility" in captured["instructions"]
    assert "weighted score" in captured["instructions"]
    factor_properties = captured["schema"]["$defs"]["RelevanceFactor"]["properties"]
    assert "confidence" in factor_properties
    assert "clarification" in factor_properties
    assert "do not subtract points or cap relevance" in captured["instructions"]
    assert result[0].score == 80


def test_ollama_structured_request_is_validated(monkeypatch, profile):
    """Return a valid fake profile and verify the Ollama request and parsed result."""
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.test:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    captured = {}

    def handler(request):
        captured["request"] = request
        return httpx.Response(200, json={
            "model": "test-model",
            "done": True,
            "message": {"role": "assistant", "content": json.dumps(profile.model_dump())},
        })

    use_fake_ollama(monkeypatch, handler)

    result = llm.extract_profile("Polish manufacturing SME")
    assert result.country == "Poland"
    assert result.company_size == "SME"
    # The HTTP payload is valid, but its invented numbers and currency are discarded.
    assert result.employees is result.project_budget is result.currency is None
    assert result.source_phrases == ["Polish", "SME"]
    request = captured["request"]
    assert str(request.url) == "http://ollama.test:11434/api/chat"
    payload = json.loads(request.content)
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["format"]["title"] == "CompanyProfile"
    assert "evidence" in payload["format"]["required"]
    evidence_schema = payload["format"]["$defs"]["ProfileEvidence"]
    assert set(evidence_schema["required"]) == set(evidence_schema["properties"])
    assert "project_goal" in payload["format"]["required"]
    assert payload["options"]["temperature"] == 0
    assert "Extract a company" in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Polish manufacturing SME"


@pytest.mark.parametrize("payload", [
    {},
    {"message": {}},
    {"done": False, "message": {"content": "{}"}},
    {"done": True, "message": {"content": ""}},
    {"done": True, "message": {"content": "not json"}},
    {"done": True, "message": {"content": '{"employees": -5}'}},
])
def test_incomplete_or_invalid_ollama_output(monkeypatch, payload):
    """Check that empty, malformed and invalid Ollama replies become LLMError."""
    use_fake_ollama(monkeypatch, lambda request: httpx.Response(200, json=payload))

    with pytest.raises(llm.LLMError):
        llm.extract_profile("Company description")


def test_missing_ollama_model_has_install_command(monkeypatch):
    """Turn Ollama's model-not-found response into a useful pull instruction."""
    use_fake_ollama(
        monkeypatch,
        lambda request: httpx.Response(404, json={"error": "model not found"}),
    )

    with pytest.raises(llm.LLMError, match=r"ollama pull qwen3:8b"):
        llm.extract_profile("Company description")


def test_other_ollama_http_errors_are_readable(monkeypatch):
    """Turn other HTTP failures into a readable local-service error."""
    use_fake_ollama(
        monkeypatch,
        lambda request: httpx.Response(500, json={"error": "Test failure"}),
    )

    with pytest.raises(llm.LLMError, match="Ollama rejected"):
        llm.extract_profile("Company description")


def test_ollama_network_error_is_readable(monkeypatch):
    """Simulate a connection failure and confirm the message names local Ollama."""
    def handler(request):
        raise httpx.ConnectError("Test connection failure", request=request)

    use_fake_ollama(monkeypatch, handler)

    with pytest.raises(llm.LLMError, match="Could not reach Ollama"):
        llm.extract_profile("Company description")


def test_ollama_timeout_is_not_reported_as_connection_failure(monkeypatch):
    """Explain a slow local model accurately instead of claiming Ollama is offline."""
    def handler(request):
        raise httpx.ReadTimeout("Test timeout", request=request)

    use_fake_ollama(monkeypatch, handler)

    with pytest.raises(llm.LLMError, match="took longer than two minutes"):
        llm.extract_profile("Company description")
