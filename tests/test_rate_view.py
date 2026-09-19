import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from typesafe_sdk import Score, TypeSafeError

from tests.conftest import FakeClient

DISTRIBUTIONS = {"readability": [0.55, 0.0, 0.45], "mood": [0.1, 0.1, 0.8]}


@pytest.fixture
def admin_client(client, db):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    return client


def _form_data(**overrides):
    data = {
        "jev_model": "testapp.ArticlePage",
        "title": "Python packaging",
        "intro": "<p>How to build wheels</p>",
        "body-count": "1",
        "body-0-type": "heading",
        "body-0-value": "Setup",
        "body-0-order": "0",
        "body-0-deleted": "",
        "tags": "django",
    }
    data.update(overrides)
    return data


def test_rate_sends_one_score_per_key_built_from_form_data(admin_client, fake_client):
    client = fake_client(distributions=DISTRIBUTIONS)

    response = admin_client.post(reverse("wagtail_jev:rate"), _form_data(jev_keys=["readability"]))

    assert response.status_code == 200
    assert response.json() == {
        "ratings": [
            {
                "key": "readability",
                "label": "Easy",
                "probability": 0.55,
                "levels": [
                    {"label": "Easy", "probability": 0.55},
                    {"label": "Medium", "probability": 0.0},
                    {"label": "Hard", "probability": 0.45},
                ],
            }
        ]
    }
    assert len(client.calls) == 1
    state, questions = client.calls[0]
    assert state == {"article": {"title": "Python packaging", "body": "How to build wheels\n\nSetup"}}
    assert list(questions) == ["readability"]
    assert isinstance(questions["readability"], Score)


def test_rate_with_no_keys_rates_every_declared_quality(admin_client, fake_client):
    client = fake_client(distributions=DISTRIBUTIONS)

    response = admin_client.post(reverse("wagtail_jev:rate"), _form_data())

    assert response.status_code == 200
    assert [(r["key"], r["label"]) for r in response.json()["ratings"]] == [
        ("readability", "Easy"),
        ("mood", "Happy"),
    ]
    assert len(client.calls) == 1
    assert list(client.calls[0][1]) == ["readability", "mood"]


def test_rate_returns_ratings_in_declaration_order_whatever_the_key_order(admin_client, fake_client):
    fake_client(distributions=DISTRIBUTIONS)
    response = admin_client.post(reverse("wagtail_jev:rate"), _form_data(jev_keys=["mood", "readability"]))
    assert [r["key"] for r in response.json()["ratings"]] == ["readability", "mood"]


def test_rate_empty_article_makes_no_request_and_returns_no_ratings(admin_client, fake_client):
    client = fake_client(distributions=DISTRIBUTIONS)

    response = admin_client.post(
        reverse("wagtail_jev:rate"), {"jev_model": "testapp.ArticlePage", "title": " ", "intro": ""}
    )

    assert response.status_code == 200
    assert response.json() == {"ratings": []}
    assert client.calls == []


def test_rate_rejects_unknown_key_before_any_request(admin_client, fake_client):
    client = fake_client(distributions=DISTRIBUTIONS)
    response = admin_client.post(reverse("wagtail_jev:rate"), _form_data(jev_keys=["nope"]))
    assert response.status_code == 400
    assert "nope" in response.json()["error"]
    assert client.calls == []


def test_rate_rejects_unknown_model(admin_client, db):
    response = admin_client.post(reverse("wagtail_jev:rate"), {"jev_model": "nope.Nope"})
    assert response.status_code == 400


def test_rate_rejects_non_jev_model(admin_client, db):
    response = admin_client.post(reverse("wagtail_jev:rate"), {"jev_model": "wagtailcore.Page"})
    assert response.status_code == 400


def test_rate_returns_502_when_typesafe_fails(admin_client, monkeypatch, db):
    class FailingClient(FakeClient):
        def system_one(self, state, questions, **kwargs):
            raise TypeSafeError("jev is down")

    monkeypatch.setattr("wagtail_jev.classifier.get_client", lambda: FailingClient({}))

    response = admin_client.post(reverse("wagtail_jev:rate"), _form_data())

    assert response.status_code == 502
    assert "jev is down" in response.json()["error"]


def test_rate_requires_admin(client, db):
    response = client.post(reverse("wagtail_jev:rate"), {"jev_model": "testapp.ArticlePage"})
    assert response.status_code in (302, 403)
