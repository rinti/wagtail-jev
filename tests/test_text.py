import pytest
from wagtail.rich_text import RichText

from tests.testapp.models import ArticlePage
from wagtail_jev.text import value_to_text


def test_rich_text_is_stripped():
    assert value_to_text(RichText("<p>Hello <b>world</b></p>")) == "Hello world"


@pytest.mark.django_db
def test_stream_value_collects_block_text():
    page = ArticlePage(
        title="T",
        body=[("heading", "Intro"), ("paragraph", RichText("<p>Body text</p>"))],
    )
    assert value_to_text(page.body) == "Intro\nBody text"


@pytest.mark.django_db
def test_mixin_jev_text_skips_title_and_joins_fields():
    page = ArticlePage(title="T", intro="<p>Lead</p>", body=[("heading", "H")])
    assert page.jev_text() == "Lead\n\nH"
