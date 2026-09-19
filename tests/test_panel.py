import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from wagtail.models import Page

from tests.testapp.models import ArticlePage
from wagtail_jev.panels import JevRatingFieldPanel, JevRatingPanel


@pytest.mark.django_db
def test_edit_view_renders_one_suggest_button_per_tag_field(client):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    root = Page.objects.get(depth=1)
    page = root.add_child(instance=ArticlePage(title="Hello", slug="hello"))

    response = client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))

    assert response.status_code == 200
    html = response.content.decode()
    assert html.count("Let Jev suggest tags") == 2
    assert 'data-jev-suggest-field-value="tags"' in html
    assert 'data-jev-suggest-field-value="feeling_tags"' in html
    assert 'data-jev-suggest-model-value="testapp.ArticlePage"' in html
    assert html.count("wagtail_jev/js/jev-suggest-controller.js") == 1


@pytest.mark.django_db
def test_edit_view_renders_the_article_rating_button_once(client):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    root = Page.objects.get(depth=1)
    page = root.add_child(instance=ArticlePage(title="Hello", slug="hello"))

    response = client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))

    assert response.status_code == 200
    html = response.content.decode()
    assert html.count('data-jev-rate-field-value=""') == 1
    assert 'data-jev-rate-model-value="testapp.ArticlePage"' in html
    assert 'data-jev-rate-keys-value="readability,mood"' in html
    assert html.count("wagtail_jev/js/jev-rate-controller.js") == 1


@pytest.mark.django_db
def test_edit_view_renders_one_rating_button_per_wrapped_field(client):
    user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    root = Page.objects.get(depth=1)
    page = root.add_child(instance=ArticlePage(title="Hello", slug="hello"))

    response = client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))

    assert response.status_code == 200
    html = response.content.decode()
    assert html.count('data-controller="jev-rate"') == 3
    intro = _controller_block(html, "intro")
    assert 'data-jev-rate-keys-value="readability"' in intro
    assert "Rate Readability with Jev" in intro
    body = _controller_block(html, "body")
    assert 'data-jev-rate-keys-value="readability,mood"' in body
    assert "Rate with Jev" in body
    # The normal widgets still render above the buttons.
    assert 'data-contentpath="intro"' in html and 'data-contentpath="body"' in html
    assert html.count("wagtail_jev/js/jev-rate-controller.js") == 1


def _controller_block(html, field_name):
    start = html.index(f'data-jev-rate-field-value="{field_name}"')
    return html[start : html.index("</button>", start)]


def test_rating_field_panel_with_an_unknown_key_fails_at_bind_time():
    with pytest.raises(LookupError, match="nope"):
        JevRatingFieldPanel("intro", keys=["nope"]).bind_to_model(ArticlePage)


@pytest.mark.parametrize("field_name", ["live", "tags"])
def test_rating_field_panel_on_an_unsupported_field_fails_at_bind_time(field_name):
    with pytest.raises(LookupError, match=field_name):
        JevRatingFieldPanel(field_name, keys=["mood"]).bind_to_model(ArticlePage)


def test_rating_field_panel_without_the_mixin_fails_at_bind_time():
    with pytest.raises(ImproperlyConfigured, match="JevTaggableMixin"):
        JevRatingFieldPanel("title", keys=["mood"]).bind_to_model(Page)


def test_rating_panel_with_an_unknown_key_fails_at_bind_time():
    with pytest.raises(LookupError, match="nope"):
        JevRatingPanel(keys=["nope"]).bind_to_model(ArticlePage)


def test_rating_panel_without_the_mixin_fails_at_bind_time():
    with pytest.raises(ImproperlyConfigured, match="JevTaggableMixin"):
        JevRatingPanel().bind_to_model(Page)


@pytest.mark.django_db
def test_rating_panel_renders_only_its_key_subset(rf):
    panel = JevRatingPanel(keys=["mood"]).bind_to_model(ArticlePage)
    page = ArticlePage(title="Hello")
    form = panel.get_form_class()(instance=page)

    html = panel.get_bound_panel(instance=page, request=rf.get("/"), form=form).render_html()

    assert 'data-jev-rate-keys-value="mood"' in html
    assert 'data-jev-rate-model-value="testapp.ArticlePage"' in html
