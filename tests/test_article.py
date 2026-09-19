import pytest
from django.http import QueryDict
from taggit.models import Tag
from wagtail.models import Page
from wagtail.rich_text import RichText

from tests.testapp.models import ArticlePage
from wagtail_jev.article import Article


@pytest.mark.django_db
def test_from_page_skips_title_flattens_blocks_and_strips_html():
    page = ArticlePage(
        title="T",
        intro="<p>Lead <b>in</b></p>",
        body=[("heading", "H"), ("paragraph", RichText("<p>Body text</p>"))],
    )
    article = Article.from_page(page, "tags")
    assert article.title == "T"
    assert article.body == "Lead in\n\nH\nBody text"
    assert article.existing_tags == ()


@pytest.mark.django_db
def test_from_page_reads_existing_tags_of_the_named_field():
    Tag.objects.create(name="python")
    root = Page.objects.get(depth=1)
    page = root.add_child(instance=ArticlePage(title="T", slug="t"))
    page.tags.add("python")
    page.save()
    assert Article.from_page(page, "tags").existing_tags == ("python",)
    assert Article.from_page(page, "feeling_tags").existing_tags == ()
    assert Article.from_page(page).existing_tags == ()


def test_from_form_data_without_a_tag_field_carries_no_existing_tags():
    data = QueryDict("title=T&tags=django")
    assert Article.from_form_data(ArticlePage, data) == Article(title="T", body="")


@pytest.mark.django_db
def test_from_form_data_rebuilds_unsaved_stream_and_rich_text():
    data = QueryDict(mutable=True)
    data.update(
        {
            "title": "Python packaging",
            "intro": "<p>How to build wheels</p>",
            "body-count": "1",
            "body-0-type": "heading",
            "body-0-value": "Setup",
            "body-0-order": "0",
            "body-0-deleted": "",
            "tags": "django, python",
        }
    )
    article = Article.from_form_data(ArticlePage, data, field_name="tags")
    assert article.title == "Python packaging"
    assert article.body == "How to build wheels\n\nSetup"
    assert article.existing_tags == ("django", "python")


def test_from_form_data_tolerates_missing_fields():
    article = Article.from_form_data(ArticlePage, QueryDict(), field_name="tags")
    assert article == Article(title="", body="", existing_tags=())
