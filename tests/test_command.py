import pytest
from django.core.management import CommandError, call_command
from taggit.models import Tag
from wagtail.models import Page

from tests.testapp.models import ArticlePage, FeelingTag


@pytest.fixture
def page(db):
    Tag.objects.create(name="python")
    Tag.objects.create(name="cooking")
    FeelingTag.objects.create(name="calm")
    root = Page.objects.get(depth=1)
    return root.add_child(instance=ArticlePage(title="Py", slug="py", live=True))


def test_command_applies_all_fields_in_one_draft_revision(page, fake_client):
    fake_client({"python": 0.9, "cooking": 0.1, "calm": 0.95})

    call_command("jev_tag_pages", "testapp.ArticlePage", "--apply")

    page.refresh_from_db()
    latest = page.get_latest_revision_as_object()
    assert [t.name for t in latest.tags.all()] == ["python"]
    assert [t.name for t in latest.feeling_tags.all()] == ["calm"]
    assert page.revisions.count() == 1
    assert page.has_unpublished_changes
    assert list(ArticlePage.objects.get(id=page.id).tags.all()) == []


def test_command_field_option_limits_to_one_field(page, fake_client):
    client = fake_client({"python": 0.9, "cooking": 0.1, "calm": 0.95})

    call_command("jev_tag_pages", "testapp.ArticlePage", "--field", "feeling_tags", "--apply")

    assert len(client.calls) == 1
    latest = ArticlePage.objects.get(id=page.id).get_latest_revision_as_object()
    assert [t.name for t in latest.feeling_tags.all()] == ["calm"]
    assert list(latest.tags.all()) == []


def test_command_rejects_unknown_field(page):
    with pytest.raises(CommandError, match="nope"):
        call_command("jev_tag_pages", "testapp.ArticlePage", "--field", "nope")


def test_command_threshold_option_overrides_every_field(page, fake_client):
    fake_client({"python": 0.9, "cooking": 0.1, "calm": 0.95})

    call_command("jev_tag_pages", "testapp.ArticlePage", "--threshold", "0.92", "--apply")

    latest = ArticlePage.objects.get(id=page.id).get_latest_revision_as_object()
    assert list(latest.tags.all()) == []  # python at 0.9 no longer passes
    assert [t.name for t in latest.feeling_tags.all()] == ["calm"]


class _RaisingClient:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def system_one(self, state, questions, **kwargs):
        self.calls += 1
        raise self.error

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


def test_command_stops_at_once_when_laya_is_unavailable(page, monkeypatch):
    from wagtail_jev.laya import LayaUnavailable

    client = _RaisingClient(LayaUnavailable("Could not reach Laya at http://laya:8000/v1/systemone"))
    monkeypatch.setattr("wagtail_jev.client.get_client", lambda: client)

    with pytest.raises(CommandError, match="Could not reach Laya"):
        call_command("jev_tag_pages", "testapp.ArticlePage")
    assert client.calls == 1


def test_command_skips_a_page_on_other_laya_errors(page, monkeypatch, capsys):
    from wagtail_jev.laya import LayaError

    client = _RaisingClient(LayaError("Laya server answered 422: question 'tag_0' has no criteria"))
    monkeypatch.setattr("wagtail_jev.client.get_client", lambda: client)

    call_command("jev_tag_pages", "testapp.ArticlePage")

    assert capsys.readouterr().err.count("422") == 2  # one line per tag field, no crash
