import pytest
from typesafe_sdk import NoulAnswer, SystemOneResponse, Usage


class FakeClient:
    """Answers each Noul with a probability looked up from the tag name in its question."""

    def __init__(self, probabilities):
        self.probabilities = probabilities
        self.calls = []

    def system_one(self, state, questions, **kwargs):
        self.calls.append((state, questions))
        answers = {}
        for key, question in questions.items():
            tag = next(t for t in self.probabilities if repr(t) in question.instructions)
            answers[key] = NoulAnswer(type="noul", noul=self.probabilities[tag])
        return SystemOneResponse(
            model="jev-test", answers=answers, usage=Usage(input_tokens=1, output_tokens=1)
        )

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


@pytest.fixture
def fake_client(monkeypatch):
    def make(probabilities):
        client = FakeClient(probabilities)
        monkeypatch.setattr("wagtail_jev.classifier.get_client", lambda: client)
        return client

    return make
