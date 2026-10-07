import json

import httpx2
import pytest
from typesafe_sdk import Noul, NoulCriteria, Score, TypeSafeError

from wagtail_jev.decisions import DecisionsClient

QUESTIONS = {
    "q": Noul(instructions="Is it about python?", criteria=NoulCriteria(true="about python", false="not about python")),
    "r": Score(instructions="How easy?", criteria=["easy", "hard"]),
}
DECISION = {
    "model": "gpt-6-luna",
    "answers": [
        {"type": "predicate", "name": "q", "probability": 0.8},
        {
            "type": "score",
            "name": "r",
            "score": 0.9,
            "probabilities": [
                {"value": 0, "label": "0", "probability": 0.1},
                {"value": 1, "label": "1", "probability": 0.9},
            ],
            "confidence": 0.8,
        },
    ],
    "usage": {"input_tokens": 42, "output_tokens": 0, "total_tokens": 42},
}


def openai_api(status=200, body=DECISION):
    """An OpenAI stand-in that records each request and sends ``body`` (JSON unless bytes),
    or raises it when it is an exception."""
    received = []

    def handle(request):
        received.append(request)
        if isinstance(body, Exception):
            raise body
        if isinstance(body, bytes):
            return httpx2.Response(status, content=body, headers={"Content-Type": "text/html"})
        return httpx2.Response(status, json=body)

    return httpx2.MockTransport(handle), received


def openai(transport, **config):
    return DecisionsClient(**{"api_key": "sk-test", "model": "gpt-6-luna", "timeout": 5, "transport": transport, **config})


def test_questions_go_to_decisions_as_predicates_and_scores_and_come_back_as_nouls_and_scores():
    transport, received = openai_api()

    response = openai(transport).system_one("Django ORM tips\n\nselect_related", QUESTIONS)

    [request] = received
    assert str(request.url) == "https://api.openai.com/v1/decisions"
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert json.loads(request.content) == {
        "model": "gpt-6-luna",
        "input": "Django ORM tips\n\nselect_related",
        "questions": [
            {
                "type": "predicate",
                "name": "q",
                "instructions": "Is it about python?\nTrue: about python\nFalse: not about python",
            },
            {
                "type": "score",
                "name": "r",
                "instructions": "How easy?",
                "levels": [{"label": "0", "description": "easy"}, {"label": "1", "description": "hard"}],
            },
        ],
    }
    assert response.nouls["q"].noul == 0.8
    assert response.scores["r"].probabilities == {0: 0.1, 1: 0.9}


def test_another_base_url_serves_european_data_residency():
    transport, received = openai_api()
    openai(transport, base_url="https://eu.api.openai.com/v1").system_one("text", QUESTIONS)
    assert str(received[0].url) == "https://eu.api.openai.com/v1/decisions"


def test_a_refused_question_fails_the_request_naming_it():
    # Tag fields and Qualities read an answer for every question they asked.
    refused = {**DECISION, "answers": [DECISION["answers"][0], {"type": "refusal", "name": "r"}]}
    transport, _ = openai_api(body=refused)
    with pytest.raises(TypeSafeError, match="OpenAI declined to answer r"):
        openai(transport).system_one("text", QUESTIONS)


def test_a_missing_answer_fails_the_request_naming_it():
    transport, _ = openai_api(body={**DECISION, "answers": DECISION["answers"][:1]})
    with pytest.raises(TypeSafeError, match="OpenAI did not answer r"):
        openai(transport).system_one("text", QUESTIONS)


def test_openai_errors_carry_openais_message():
    error = {"error": {"message": "Invalid model 'gpt-5'", "type": "invalid_request_error", "code": None}}
    transport, _ = openai_api(400, error)
    with pytest.raises(TypeSafeError, match=r"OpenAI answered 400: Invalid model 'gpt-5'"):
        openai(transport).system_one("text", QUESTIONS)


def test_a_reply_that_is_not_openais_json_is_a_typesafe_error():
    # e.g. a proxy's error page: the view and jev_tag_pages only catch TypeSafeError.
    transport, _ = openai_api(502, b"<html>bad gateway</html>")
    with pytest.raises(TypeSafeError, match="502.*bad gateway"):
        openai(transport).system_one("text", QUESTIONS)


@pytest.mark.parametrize(
    "failure, message",
    [
        (httpx2.ReadTimeout("timed out"), r"OpenAI did not answer within 5s"),
        (httpx2.ConnectError("name or service not known"), "Could not reach OpenAI: name or service not known"),
    ],
)
def test_network_failures_are_typesafe_errors(failure, message):
    transport, _ = openai_api(body=failure)
    with pytest.raises(TypeSafeError, match=message):
        openai(transport).system_one("text", QUESTIONS)


def test_a_missing_api_key_names_the_setting():
    with pytest.raises(TypeSafeError, match="WAGTAIL_JEV_OPENAI_API_KEY"):
        DecisionsClient(api_key=None, model="gpt-6-luna")
