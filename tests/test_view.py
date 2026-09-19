import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from taggit.models import Tag

from tests.testapp.models import FeelingTag


@pytest.fixture
def admin_client(client, db):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    return client


@pytest.fixture
def tags(db):
    for name in ["python", "django", "cooking"]:
        Tag.objects.create(name=name)
    for name in ["calm", "angry"]:
        FeelingTag.objects.create(name=name)


def test_suggest_uses_form_data_and_excludes_existing_tags(admin_client, tags, fake_client):
    client = fake_client({"python": 0.9, "cooking": 0.2})
    response = admin_client.post(
        reverse("wagtail_jev:suggest"),
        {
            "jev_model": "testapp.ArticlePage",
            "jev_field": "tags",
            "title": "Python packaging",
            "intro": "<p>How to build wheels</p>",
            "body-count": "1",
            "body-0-type": "heading",
            "body-0-value": "Setup",
            "body-0-order": "0",
            "body-0-deleted": "",
            "tags": "django",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"tags": [{"name": "python", "probability": 0.9}]}
    state, questions = client.calls[0]
    assert state["article"]["body"] == "How to build wheels\n\nSetup"
    assert state["existing_tags"] == ["django"]
    assert len(questions) == 2


def test_second_field_uses_its_own_tag_model_prompts_and_threshold(admin_client, tags, fake_client):
    client = fake_client({"calm": 0.85, "angry": 0.7})
    response = admin_client.post(
        reverse("wagtail_jev:suggest"),
        {"jev_model": "testapp.ArticlePage", "jev_field": "feeling_tags", "title": "Zen"},
    )
    assert response.status_code == 200
    # angry at 0.7 is above the global 0.6 but below this field's 0.8 threshold
    assert response.json() == {"tags": [{"name": "calm", "probability": 0.85}]}
    _, questions = client.calls[0]
    assert len(questions) == 2  # only FeelingTag rows, not the three topic tags
    assert all("mood" in q.instructions for q in questions.values())


def test_suggest_rejects_unknown_field(admin_client, db):
    response = admin_client.post(
        reverse("wagtail_jev:suggest"), {"jev_model": "testapp.ArticlePage", "jev_field": "nope"}
    )
    assert response.status_code == 400
    assert "nope" in response.json()["error"]


def test_suggest_rejects_unknown_model(admin_client, db):
    response = admin_client.post(reverse("wagtail_jev:suggest"), {"jev_model": "nope.Nope"})
    assert response.status_code == 400


def test_suggest_requires_admin(client, db):
    response = client.post(reverse("wagtail_jev:suggest"), {"jev_model": "testapp.ArticlePage"})
    assert response.status_code in (302, 403)


def test_suggest_rejects_non_jev_model(admin_client, db):
    response = admin_client.post(reverse("wagtail_jev:suggest"), {"jev_model": "wagtailcore.Page"})
    assert response.status_code == 400
