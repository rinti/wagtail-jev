import json

import pytest
from typesafe_sdk import NoulAnswer, Score, ScoreAnswer, SystemOneResponse, Usage


def contentstate(text: str) -> str:
    """What the Draftail rich text editor posts for one paragraph: contentstate JSON, not HTML."""
    block = {"key": "a1b2c", "text": text, "type": "unstyled", "depth": 0, "inlineStyleRanges": [], "entityRanges": []}
    return json.dumps({"blocks": [block], "entityMap": {}})


class FakeClient:
    """Answers each Noul with a probability looked up from the tag name in its question,
    and each Score with the per-level distribution configured under its question key."""

    def __init__(self, probabilities, distributions=None):
        self.probabilities = probabilities
        self.distributions = distributions or {}
        self.calls = []

    def system_one(self, state, questions, **kwargs):
        self.calls.append((state, questions))
        answers = {}
        for key, question in questions.items():
            if isinstance(question, Score):
                answers[key] = self._score_answer(key, question)
            else:
                tag = next(t for t in self.probabilities if repr(t) in question.instructions)
                answers[key] = NoulAnswer(type="noul", noul=self.probabilities[tag])
        return SystemOneResponse(
            model="jev-test", answers=answers, usage=Usage(input_tokens=1, output_tokens=1)
        )

    def _score_answer(self, key, question):
        distribution = self.distributions[key]
        assert len(distribution) == len(question.criteria)
        return ScoreAnswer(
            type="score",
            score=sum(i * p for i, p in enumerate(distribution)),
            confidence=max(distribution),
            legend={i: c for i, c in enumerate(question.criteria)},
            probabilities={i: p for i, p in enumerate(distribution)},
        )

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


@pytest.fixture
def fake_client(monkeypatch):
    def make(probabilities=None, distributions=None):
        client = FakeClient(probabilities or {}, distributions)
        monkeypatch.setattr("wagtail_jev.client.get_client", lambda: client)
        return client

    return make
