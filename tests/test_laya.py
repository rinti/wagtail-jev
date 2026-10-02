import json
import socket
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest
from typesafe_sdk import Noul, NoulCriteria, Score, SystemOneResponse

from wagtail_jev import laya as laya_module
from wagtail_jev.laya import LayaClient, LayaError, LayaUnavailable, to_laya_question, to_response

NOUL = Noul(instructions="Is `state` about python?", criteria=NoulCriteria(true="about python", false="not about python"))
QUESTIONS = {"q": NOUL}
LAYA_QUESTIONS = {
    "q": {
        "type": "noul",
        "instructions": "Is `state` about python?",
        "criteria": {"true": "about python", "false": "not about python"},
        "labels": {"true": "A", "false": "B"},
    }
}
PAYLOAD = {
    "model": "english",
    "answers": {"q": {"type": "noul", "noul": 0.5, "confidence": 0.5, "answer_confidence": 0.5}},
    "usage": {"input_tokens": 10, "output_tokens": 1},
}


# --- conversion ---------------------------------------------------------------


def test_nouls_become_laya_dicts_with_neutral_labels():
    assert to_laya_question(NOUL) == LAYA_QUESTIONS["q"]


def test_each_noul_gets_its_own_labels_dict():
    a, b = to_laya_question(NOUL), to_laya_question(NOUL)
    a["labels"]["true"] = "changed"
    assert b["labels"] == {"true": "A", "false": "B"}


def test_scores_and_plain_dicts_pass_through_without_labels():
    assert to_laya_question(Score(instructions="How easy?", criteria=["easy", "hard"])) == {
        "type": "score",
        "instructions": "How easy?",
        "criteria": ["easy", "hard"],
    }
    assert to_laya_question({"type": "score", "criteria": ["a", "b"]}) == {"type": "score", "criteria": ["a", "b"]}


def test_payload_becomes_a_real_system_one_response():
    response = to_response(
        {
            "model": "multilingual",
            "answers": {
                "q": {"type": "noul", "noul": 0.91, "answer_confidence": 0.91},
                "r": {
                    "type": "score",
                    "score": 0.9,
                    "legend": {"0": "easy", "1": "hard"},
                    "probabilities": {"0": 0.1, "1": 0.9},
                    "confidence": 0.4,
                    "answer_confidence": 0.9,
                },
                "c": {"type": "choice", "choice": "x", "probabilities": {"x": 1.0}},
            },
            "usage": {"input_tokens": 12, "output_tokens": 2},
        }
    )
    assert isinstance(response, SystemOneResponse)
    assert response.model == "multilingual"
    assert response.nouls["q"].noul == 0.91
    assert response.scores["r"].probabilities == {0: 0.1, 1: 0.9}
    assert response.scores["r"].legend == {0: "easy", 1: "hard"}
    assert "c" not in response.answers


def test_missing_model_and_usage_are_filled_in():
    response = to_response({"answers": {"q": {"type": "noul", "noul": 0.2}}})
    assert response.model == "laya"
    assert response.usage.input_tokens is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"answers": None},
        {"answers": {"q": {"type": "noul"}}},
        {"answers": {"q": {"type": "noul", "noul": "high"}}},
        {"answers": {"r": {"type": "score", "score": 1, "probabilities": {"x": 1.0}}}},
    ],
)
def test_malformed_payloads_raise_laya_error(payload):
    with pytest.raises(LayaError, match="cannot read"):
        to_response(payload)


# --- in-process ---------------------------------------------------------------


class FakeRouter:
    def __init__(self, fail=None, payload=PAYLOAD):
        self.calls = []
        self.fail = fail
        self.payload = payload

    def predict(self, state, questions, model=None):
        self.calls.append((state, questions, model))
        if self.fail:
            raise self.fail
        return self.payload


@pytest.fixture
def fake_laya(monkeypatch):
    """A stand-in ``laya`` package whose Router() records every instance it builds."""
    created = []
    module = types.ModuleType("laya")

    def Router():
        time.sleep(0.05)  # widen the race window for the concurrency test
        router = FakeRouter()
        created.append(router)
        return router

    module.Router = Router
    monkeypatch.setitem(sys.modules, "laya", module)
    monkeypatch.setattr(laya_module, "_router", None)
    return created


def test_in_process_converts_questions_and_passes_the_model(fake_laya):
    response = LayaClient(model="multilingual").system_one({"x": 1}, QUESTIONS)
    assert response.nouls["q"].noul == 0.5
    assert fake_laya[0].calls == [({"x": 1}, LAYA_QUESTIONS, "multilingual")]


def test_in_process_loads_the_model_once_per_process(fake_laya):
    LayaClient().system_one({}, QUESTIONS)
    LayaClient().system_one({}, QUESTIONS)
    assert len(fake_laya) == 1
    assert len(fake_laya[0].calls) == 2


def test_concurrent_first_requests_load_the_model_once(fake_laya):
    threads = [threading.Thread(target=LayaClient().system_one, args=({}, QUESTIONS)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(fake_laya) == 1
    assert len(fake_laya[0].calls) == 8


def test_missing_laya_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "laya", None)  # makes `import laya` raise ImportError
    monkeypatch.setattr(laya_module, "_router", None)
    with pytest.raises(LayaUnavailable, match=r'wagtail-jev\[laya\]'):
        LayaClient().system_one({}, QUESTIONS)


def test_laya_failing_to_start_is_unavailable(monkeypatch):
    module = types.ModuleType("laya")

    def Router():
        raise ValueError("LAYA_DEVICE 'tpu' is not a torch device")

    module.Router = Router
    monkeypatch.setitem(sys.modules, "laya", module)
    monkeypatch.setattr(laya_module, "_router", None)
    with pytest.raises(LayaUnavailable, match="could not start.*tpu"):
        LayaClient().system_one({}, QUESTIONS)


def test_a_broken_laya_install_is_unavailable(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name == "laya":
            raise OSError("dlopen(libtorch_cpu.dylib): image not found")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "laya", raising=False)
    monkeypatch.setattr(builtins, "__import__", broken_import)
    monkeypatch.setattr(laya_module, "_router", None)
    with pytest.raises(LayaUnavailable, match="could not start.*libtorch"):
        LayaClient().system_one({}, QUESTIONS)


def test_prediction_errors_become_laya_errors(fake_laya, monkeypatch):
    monkeypatch.setattr(laya_module, "_router", FakeRouter(fail=ValueError("question 'q' has no criteria")))
    with pytest.raises(LayaError, match="question 'q' has no criteria"):
        LayaClient().system_one({}, QUESTIONS)


@pytest.mark.parametrize(
    "answers",
    [{}, {"q": {"type": "score", "score": 1.0, "probabilities": {"0": 0.0, "1": 1.0}}}],
    ids=["missing", "another type"],
)
def test_a_question_without_an_answer_of_its_type_is_a_laya_error(monkeypatch, answers):
    # Otherwise the tag field or Quality hits a KeyError and the editor gets a 500, not a 502.
    monkeypatch.setattr(laya_module, "_router", FakeRouter(payload={"answers": answers}))
    with pytest.raises(LayaError, match="did not answer q"):
        LayaClient().system_one({}, QUESTIONS)


def test_the_client_is_a_context_manager(fake_laya):
    with LayaClient() as client:
        assert client.system_one({}, QUESTIONS).nouls["q"].noul == 0.5


# --- server -------------------------------------------------------------------


@pytest.fixture
def laya_server():
    """A real HTTP server on localhost that records requests and sends a configurable reply."""
    received = []
    reply = {"status": 200, "body": PAYLOAD}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            received.append(
                {"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(length))}
            )
            body = reply["body"]
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(reply["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(url=f"http://127.0.0.1:{server.server_port}", received=received, reply=reply)
    server.shutdown()
    server.server_close()


def test_server_mode_posts_converted_questions_model_and_key(laya_server):
    client = LayaClient(url=laya_server.url + "/", api_key="secret", model="multilingual", timeout=5)

    assert client.url == laya_server.url + "/v1/systemone"
    assert client.system_one({"x": 1}, QUESTIONS).nouls["q"].noul == 0.5
    assert laya_server.received == [
        {
            "path": "/v1/systemone",
            "auth": "Bearer secret",
            "body": {"state": {"x": 1}, "questions": LAYA_QUESTIONS, "model": "multilingual"},
        }
    ]


def test_server_mode_omits_model_and_key_when_unset(laya_server):
    LayaClient(url=laya_server.url, timeout=5).system_one("text", QUESTIONS)
    assert laya_server.received[0]["auth"] is None
    assert laya_server.received[0]["body"] == {"state": "text", "questions": LAYA_QUESTIONS}


def test_server_http_errors_carry_the_servers_detail(laya_server):
    laya_server.reply.update(status=413, body={"detail": "too many questions (65 > 64)"})
    with pytest.raises(LayaError, match=r"413.*too many questions \(65 > 64\)"):
        LayaClient(url=laya_server.url, timeout=5).system_one({}, QUESTIONS)


def test_server_invalid_json_is_a_laya_error(laya_server):
    laya_server.reply.update(body=b"<html>proxy error</html>")
    with pytest.raises(LayaError, match="invalid JSON"):
        LayaClient(url=laya_server.url, timeout=5).system_one({}, QUESTIONS)


def test_a_non_http_answer_is_a_laya_error():
    # e.g. WAGTAIL_JEV_LAYA_URL pointing at Redis or SSH: urllib raises http.client errors, not OSError.
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]

        def answer_garbage():
            conn, _ = server.accept()
            conn.recv(65536)
            conn.sendall(b"NOT HTTP AT ALL\r\n\r\n")
            conn.close()

        thread = threading.Thread(target=answer_garbage, daemon=True)
        thread.start()
        with pytest.raises(LayaError, match="invalid response"):
            LayaClient(url=f"http://127.0.0.1:{port}", timeout=5).system_one({}, QUESTIONS)
        thread.join(timeout=5)


def test_an_unreachable_server_is_unavailable():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # closed on exit: nothing listens here
    with pytest.raises(LayaUnavailable, match="Could not reach Laya"):
        LayaClient(url=f"http://127.0.0.1:{port}", timeout=2).system_one({}, QUESTIONS)


def test_a_server_that_does_not_answer_in_time_is_a_laya_error_not_unavailable():
    # A reachable but slow server (a CPU box, a big batch) should skip the page like a Jev
    # timeout does, not stop a bulk run as if Laya were down.
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        with pytest.raises(LayaError, match="did not answer within 0.5") as exc:
            LayaClient(url=f"http://127.0.0.1:{port}", timeout=0.5).system_one({}, QUESTIONS)
        assert not isinstance(exc.value, LayaUnavailable)
