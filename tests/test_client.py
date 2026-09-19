import pytest
from typesafe_sdk import Noul, NoulCriteria

from tests.conftest import FakeClient
from wagtail_jev.client import ask, clip

QUESTIONS = {"q": Noul(instructions="about 'a'?", criteria=NoulCriteria(true="t", false="f"))}


class ClosingClient(FakeClient):
    closed = False

    def close(self):
        self.closed = True


class FailingClient(ClosingClient):
    def system_one(self, state, questions, **kwargs):
        raise RuntimeError("down")


def test_ask_opens_and_closes_its_own_connection(monkeypatch):
    client = ClosingClient({"a": 0.5})
    monkeypatch.setattr("wagtail_jev.client.get_client", lambda: client)

    response = ask({"x": 1}, QUESTIONS)

    assert response.nouls["q"].noul == 0.5
    assert client.calls == [({"x": 1}, QUESTIONS)]
    assert client.closed is True


def test_ask_closes_its_own_connection_on_error(monkeypatch):
    client = FailingClient({})
    monkeypatch.setattr("wagtail_jev.client.get_client", lambda: client)

    with pytest.raises(RuntimeError):
        ask({}, QUESTIONS)
    assert client.closed is True


def test_ask_leaves_a_given_connection_open():
    client = ClosingClient({"a": 0.5})
    ask({}, QUESTIONS, client=client)
    assert client.closed is False


def test_clip_applies_max_chars(settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    assert clip("0123456789") == "01234"
