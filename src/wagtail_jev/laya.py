"""Laya as an alternative to Jev: a client with ``TypeSafeClient``'s surface.

``LayaClient.system_one`` takes the same SDK question objects the rest of wagtail-jev
builds and returns a real ``SystemOneResponse``, so nothing above ``get_client()`` knows
which model answered. Laya runs in this process (one ``laya.Router`` per process, built on
first use) or behind ``python -m laya.serve`` when a URL is given. Both return Laya's
``/v1/systemone`` payload, which is converted here.

Every noul gets neutral labels: without them Laya's English checkpoint leans on the
wording of the default labels instead of the criteria, and Swedish collapses. The SDK's
``Noul`` does not allow extra fields, so the labels are added during conversion.

Loading the model takes seconds and holds a lot of memory, so it is built once, and one
prediction runs at a time under the same lock.
"""

from __future__ import annotations

import http.client
import json
import threading
import urllib.error
import urllib.request
from typing import Any, Mapping

from typesafe_sdk import NoulAnswer, ScoreAnswer, SystemOneResponse, TypeSafeError, Usage

NEUTRAL_LABELS = {"true": "A", "false": "B"}


class LayaError(TypeSafeError):
    """Laya could not answer; the message says why, in words an editor can act on."""


class LayaUnavailable(LayaError):
    """Laya cannot answer anything right now: not installed, failing to start, or its server
    unreachable. Retrying the next page will fail the same way, so bulk runs stop."""


_router = None
_lock = threading.Lock()


def _load_router():
    """The process-wide Router, built on first use. Call with ``_lock`` held."""
    global _router
    if _router is None:
        try:
            import laya

            _router = laya.Router()
        except ImportError as exc:
            raise LayaUnavailable(
                'Laya is not installed. Run pip install "wagtail-jev[laya]", '
                "or set WAGTAIL_JEV_LAYA_URL to a Laya server."
            ) from exc
        except Exception as exc:  # e.g. a libtorch that fails to load, or a bad LAYA_* setting
            raise LayaUnavailable(f"Laya could not start: {exc}") from exc
    return _router


class LayaClient:
    """Answers ``system_one`` requests with Laya, in this process or on a Laya server."""

    def __init__(self, *, url: str | None = None, api_key: str | None = None, model: str | None = None, timeout: float = 30.0):
        self.url = url.rstrip("/") + "/v1/systemone" if url else None
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def system_one(self, state: Any, questions: Mapping[str, Any], **kwargs) -> SystemOneResponse:
        laya_questions = {qid: to_laya_question(question) for qid, question in questions.items()}
        payload = self._post(state, laya_questions) if self.url else self._predict(state, laya_questions)
        return to_response(payload)

    def _predict(self, state: Any, questions: dict) -> dict:
        with _lock:
            router = _load_router()
            try:
                return router.predict(state, questions, model=self.model)
            except Exception as exc:
                raise LayaError(f"Laya failed: {exc}") from exc

    def _post(self, state: Any, questions: dict) -> dict:
        body = {"state": state, "questions": questions}
        if self.model:
            body["model"] = self.model
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise LayaError(f"Laya server answered {exc.code}: {_detail(exc)}") from exc
        except TimeoutError as exc:  # reachable but slow: skip this request, like a Jev timeout
            raise LayaError(f"Laya server did not answer within {self.timeout}s") from exc
        except OSError as exc:  # URLError: refused connections, DNS failures, connect timeouts
            raise LayaUnavailable(f"Could not reach Laya at {self.url}: {exc}") from exc
        except http.client.HTTPException as exc:  # not HTTP at all, or a connection cut mid-body
            raise LayaError(f"Laya server sent an invalid response: {exc!r}") from exc
        except ValueError as exc:
            raise LayaError(f"Laya server sent invalid JSON: {exc}") from exc

    def close(self) -> None:
        pass

    def __enter__(self) -> "LayaClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def to_laya_question(question: Any) -> dict:
    """An SDK question (or a question dict) as the dict Laya takes, nouls with neutral labels."""
    data = question.model_dump(mode="json") if hasattr(question, "model_dump") else dict(question)
    if data.get("type") == "noul":
        data["labels"] = dict(NEUTRAL_LABELS)
    return data


def to_response(payload: dict) -> SystemOneResponse:
    """Laya's payload as an SDK response; raises :class:`LayaError` when it cannot be read."""
    try:
        answers = {}
        for qid, answer in payload["answers"].items():
            if answer["type"] == "noul":
                answers[qid] = NoulAnswer(noul=float(answer["noul"]))
            elif answer["type"] == "score":
                answers[qid] = ScoreAnswer(
                    score=float(answer["score"]),
                    confidence=float(answer.get("answer_confidence", answer.get("confidence", 1.0))),
                    legend={int(level): text for level, text in answer.get("legend", {}).items()},
                    probabilities={int(level): float(p) for level, p in answer["probabilities"].items()},
                )
        usage = payload.get("usage") or {}
        return SystemOneResponse(
            model=str(payload.get("model") or "laya"),
            answers=answers,
            usage=Usage(input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens")),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as exc:  # pydantic's ValidationError is a ValueError
        raise LayaError(f"Laya sent an answer wagtail-jev cannot read: {exc!r}") from exc


def _detail(exc: urllib.error.HTTPError) -> str:
    """The server's ``detail`` message (FastAPI's error shape), or the HTTP reason."""
    try:
        body = json.loads(exc.read())
        return str(body.get("detail", body))
    except Exception:
        return str(exc.reason)
