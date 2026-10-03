import gzip
import json

import httpx2
import pytest
from typesafe_sdk import Noul, NoulCriteria, Score, TypeSafeError

from wagtail_jev.clef import make_client

QUESTIONS = {
    "q": Noul(instructions="Is it about python?", criteria=NoulCriteria(true="about python", false="not about python")),
    "r": Score(instructions="How easy?", criteria=["easy", "hard"]),
}
RESULT = {
    "model": "clef",
    "answers": {
        "q": {"type": "noul", "noul": 0.8},
        "r": {
            "type": "score",
            "score": 0.9,
            "legend": {"0": "easy", "1": "hard"},
            "probabilities": {"0": 0.1, "1": 0.9},
            "confidence": 0.8,
        },
    },
    "usage": {"input_tokens": 12, "output_tokens": 0},
}


def envelope(result=None, errors=()):
    return {"result": result, "success": not errors, "errors": list(errors), "messages": []}


def workers_ai(status, body, *, gzipped=False):
    """A Workers AI stand-in that records each request and sends ``body`` (JSON unless bytes)."""
    received = []

    def handle(request):
        received.append(request)
        if isinstance(body, bytes):
            return httpx2.Response(status, content=body, headers={"Content-Type": "text/html"})
        if gzipped:
            content = gzip.compress(json.dumps(body).encode())
            return httpx2.Response(
                status, content=content, headers={"Content-Type": "application/json", "Content-Encoding": "gzip"}
            )
        return httpx2.Response(status, json=body)

    return httpx2.MockTransport(handle), received


def clef(transport, model="clef"):
    return make_client(account_id="acct", api_token="cf-token", model=model, timeout=5, transport=transport)


@pytest.mark.parametrize("model", ["clef", "clef-flash"])
def test_clef_sends_jevs_request_to_workers_ai_and_answers_from_the_envelope(model):
    transport, received = workers_ai(200, envelope(RESULT))

    response = clef(transport, model).system_one({"text": "hello"}, QUESTIONS)

    [request] = received
    assert str(request.url) == f"https://api.cloudflare.com/client/v4/accounts/acct/ai/run/@cf/cloudflare/{model}"
    assert request.headers["Authorization"] == "Bearer cf-token"
    body = json.loads(request.content)
    assert (body["model"], body["state"], set(body["questions"])) == (model, {"text": "hello"}, {"q", "r"})
    assert response.nouls["q"].noul == 0.8
    assert response.scores["r"].probabilities == {0: 0.1, 1: 0.9}


def test_a_gzipped_envelope_is_unwrapped_once():
    # Cloudflare usually compresses its replies; the unwrapped body must not claim to be gzip.
    transport, _ = workers_ai(200, envelope(RESULT), gzipped=True)
    assert clef(transport).system_one("text", QUESTIONS).nouls["q"].noul == 0.8


def test_cloudflare_errors_carry_cloudflares_messages():
    transport, _ = workers_ai(
        400, envelope(errors=[{"code": 5006, "message": "questions: too many"}, {"code": 1, "message": "and more"}])
    )
    with pytest.raises(TypeSafeError, match=r"400.*questions: too many; and more"):
        clef(transport).system_one("text", QUESTIONS)


def test_a_reply_that_is_not_cloudflares_json_is_a_typesafe_error():
    # e.g. a proxy's error page: the view and jev_tag_pages only catch TypeSafeError.
    transport, _ = workers_ai(400, b"<html>bad gateway</html>")
    with pytest.raises(TypeSafeError, match="bad gateway"):
        clef(transport).system_one("text", QUESTIONS)


@pytest.mark.parametrize(
    "missing, setting",
    [("account_id", "WAGTAIL_JEV_CLEF_ACCOUNT_ID"), ("api_token", "WAGTAIL_JEV_CLEF_API_TOKEN")],
)
def test_a_missing_account_or_token_names_the_setting(monkeypatch, missing, setting):
    # The SDK would otherwise fall back to TYPESAFE_API_KEY and send it to Cloudflare.
    monkeypatch.setenv("TYPESAFE_API_KEY", "typesafe-key")
    config = {"account_id": "acct", "api_token": "cf-token", missing: None}
    with pytest.raises(TypeSafeError, match=setting):
        make_client(**config, model="clef", timeout=5)
