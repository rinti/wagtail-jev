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
