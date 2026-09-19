import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from wagtail.models import Page

from tests.testapp.models import ArticlePage


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
