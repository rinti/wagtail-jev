"""OpenAI's Decisions API as an alternative to Jev: a client with ``TypeSafeClient``'s surface.

``DecisionsClient.system_one`` takes the same SDK question objects the rest of wagtail-jev
builds and returns a real ``SystemOneResponse``, so nothing above ``get_client()`` knows
which model answered. The request goes to ``POST /v1/decisions``; this module converts
both ways.

A Noul becomes a ``predicate``. A predicate has only instructions, so the Noul's true and
false criteria are appended to them as two lines. A Score becomes a ``score`` whose levels
are labelled by their index, with the criteria as descriptions: the model judges the
descriptions, as Jev does, and never sees the editor's labels.

OpenAI answers in a list, each answer named after its question. It may decline to answer a
question (a ``refusal``); that fails the request, as a missing answer does, since tag fields
and Qualities need an answer to every question they asked.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import httpx2
from typesafe_sdk import NoulAnswer, ScoreAnswer, SystemOneResponse, TypeSafeError, Usage

DEFAULT_BASE_URL = "https://api.openai.com/v1"
# The SDK answer type each Decisions question type comes back as.
ANSWER_TYPES = {"predicate": "noul", "score": "score"}


class DecisionsError(TypeSafeError):
    """OpenAI could not answer; the message says why, in words an editor can act on."""


class DecisionsClient:
    """Answers ``system_one`` requests with OpenAI's Decisions API.

    ``transport`` carries the requests; tests pass an ``httpx2.MockTransport``. Raises
    :class:`DecisionsError` when ``api_key`` is missing.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        transport: httpx2.BaseTransport | None = None,
    ):
        if not api_key:
            raise DecisionsError(
                "No OpenAI API key. Set WAGTAIL_JEV_OPENAI_API_KEY or the OPENAI_API_KEY environment variable."
            )
        self.model = model
        self.timeout = timeout
        self._http = httpx2.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def system_one(self, state: Any, questions: Mapping[str, Any]) -> SystemOneResponse:
        decision_questions = [to_decision_question(qid, question) for qid, question in questions.items()]
        body = {"model": self.model, "input": state, "questions": decision_questions}
        try:
            response = self._http.post("/decisions", json=body)
        except httpx2.TimeoutException as exc:
            raise DecisionsError(f"OpenAI did not answer within {self.timeout}s") from exc
        except httpx2.HTTPError as exc:
            raise DecisionsError(f"Could not reach OpenAI: {exc}") from exc
        if response.is_error:
            raise DecisionsError(f"OpenAI answered {response.status_code}: {_detail(response)}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise DecisionsError(f"OpenAI sent invalid JSON: {exc}") from exc
        return _require_answers(decision_questions, to_response(payload))

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "DecisionsClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def to_decision_question(name: str, question: Any) -> dict:
    """An SDK question (or a question dict) as a named Decisions question.

    Raises :class:`ValueError` for question types wagtail-jev has no Decisions question for.
    """
    data = question.model_dump(mode="json") if hasattr(question, "model_dump") else dict(question)
    if data.get("type") == "noul":
        criteria = data.get("criteria") or {}
        lines = [_text(data.get("instructions"))]
        lines += [f"{outcome.title()}: {_text(criteria[outcome])}" for outcome in ("true", "false") if criteria.get(outcome)]
        return {"type": "predicate", "name": name, "instructions": "\n".join(line for line in lines if line)}
    if data.get("type") == "score":
        return {
            "type": "score",
            "name": name,
            "instructions": _text(data.get("instructions")),
            "levels": [{"label": str(i), "description": _text(c)} for i, c in enumerate(data["criteria"])],
        }
    raise ValueError(f"OpenAI's Decisions API has no question for a {data.get('type')!r} question")


def to_response(payload: dict) -> SystemOneResponse:
    """OpenAI's decision as an SDK response; raises :class:`DecisionsError` when it cannot be
    read or a question was refused."""
    try:
        answers, refused = {}, []
        for answer in payload["answers"]:
            if answer["type"] == "refusal":
                refused.append(str(answer.get("name")))
            elif answer["type"] == "predicate":
                answers[answer["name"]] = NoulAnswer(noul=float(answer["probability"]))
            elif answer["type"] == "score":
                levels = answer["probabilities"]
                answers[answer["name"]] = ScoreAnswer(
                    score=float(answer["score"]),
                    confidence=float(answer["confidence"]),
                    legend={int(level["value"]): level["label"] for level in levels},
                    probabilities={int(level["value"]): float(level["probability"]) for level in levels},
                )
        usage = payload.get("usage") or {}
        response = SystemOneResponse(
            model=str(payload.get("model") or "openai"),
            answers=answers,
            usage=Usage(input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens")),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as exc:  # pydantic's ValidationError is a ValueError
        raise DecisionsError(f"OpenAI sent an answer wagtail-jev cannot read: {exc!r}") from exc
    if refused:
        raise DecisionsError(f"OpenAI declined to answer {', '.join(refused)}")
    return response


def _require_answers(questions: list[dict], response: SystemOneResponse) -> SystemOneResponse:
    """``response``, once it is known to answer every question with an answer of its type, so
    tag fields and Qualities can look their answers up."""
    unanswered = [
        question["name"]
        for question in questions
        if getattr(response.answers.get(question["name"]), "type", None) != ANSWER_TYPES[question["type"]]
    ]
    if unanswered:
        raise DecisionsError(f"OpenAI did not answer {', '.join(unanswered)}")
    return response


def _text(value: Any) -> str:
    """SDK question content (text, a JSON object or an array) as the text Decisions takes."""
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value)


def _detail(response: httpx2.Response) -> str:
    """OpenAI's error message, or the start of the body when it is not OpenAI's JSON (a proxy's
    HTML page)."""
    try:
        return str(response.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return response.text[:200] or response.reason_phrase
