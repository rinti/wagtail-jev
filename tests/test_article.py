import pytest
from django.http import QueryDict
from taggit.models import Tag
from wagtail.models import Page
from wagtail.rich_text import RichText

from tests.conftest import contentstate
from tests.testapp.models import ArticlePage
from wagtail_jev.article import Article, Excerpt


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
            "intro": contentstate("How to build wheels"),
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


@pytest.mark.django_db
def test_excerpt_from_a_saved_page_is_one_flattened_field_and_nothing_else():
    root = Page.objects.get(depth=1)
    page = root.add_child(
        instance=ArticlePage(
            title="T",
            slug="t",
            intro="<p>Lead <b>in</b></p>",
            body=[("heading", "H"), ("paragraph", RichText("<p>Body text</p>"))],
        )
    )
    page = ArticlePage.objects.get(pk=page.pk)
    assert Excerpt.from_page(page, "intro") == Excerpt(text="Lead in")
    assert Excerpt.from_page(page, "body") == Excerpt(text="H\nBody text")
    assert Excerpt.from_page(page, "title") == Excerpt(text="T")


@pytest.mark.django_db
def test_excerpt_from_form_data_rebuilds_unsaved_stream_and_rich_text():
    data = QueryDict(mutable=True)
    data.update(
        {
            "title": "Python packaging",
            "intro": contentstate("How to build wheels"),
            "body-count": "1",
            "body-0-type": "heading",
            "body-0-value": "Setup",
            "body-0-order": "0",
            "body-0-deleted": "",
        }
    )
    assert Excerpt.from_form_data(ArticlePage, "intro", data) == Excerpt(text="How to build wheels")
    assert Excerpt.from_form_data(ArticlePage, "body", data) == Excerpt(text="Setup")


def test_excerpt_from_form_data_with_the_field_missing_is_blank():
    assert Excerpt.from_form_data(ArticlePage, "intro", QueryDict()) == Excerpt(text="")
    assert Excerpt.from_form_data(ArticlePage, "body", QueryDict()) == Excerpt(text="")


@pytest.mark.parametrize("field_name", ["nope", "live", "tags"])
def test_excerpt_rejects_unknown_and_unsupported_fields(field_name):
    with pytest.raises(LookupError, match=field_name):
        Excerpt.from_form_data(ArticlePage, field_name, QueryDict())
    with pytest.raises(LookupError, match=field_name):
        Excerpt.from_page(ArticlePage(title="T"), field_name)
