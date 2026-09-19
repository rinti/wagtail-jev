import pytest
from taggit.models import Tag

from tests.testapp.models import ArticlePage, FeelingTag
from wagtail_jev.article import Article
from wagtail_jev.tag_field import JevTagField, PromptTemplates

ARTICLE = Article(title="Django ORM tips", body="select_related and friends")


@pytest.fixture
def tags(db):
    for name in ["python", "django", "cooking"]:
        Tag.objects.create(name=name)
    for name in ["calm", "angry"]:
        FeelingTag.objects.create(name=name)


def test_bind_resolves_unset_attributes_from_settings(settings):
    settings.WAGTAIL_JEV_THRESHOLD = 0.42
    settings.WAGTAIL_JEV_MAX_TAGS = 3
    settings.WAGTAIL_JEV_INSTRUCTIONS = "Is this about {tag}?"
    settings.WAGTAIL_JEV_CRITERIA_TRUE = "yes {tag}"
    settings.WAGTAIL_JEV_CRITERIA_FALSE = "no {tag}"

    tag_field = ArticlePage.jev_tag_field("tags")

    assert tag_field.threshold == 0.42
    assert tag_field.max_tags == 3
    assert tag_field.templates == PromptTemplates("Is this about {tag}?", "yes {tag}", "no {tag}")


def test_bind_prefers_the_field_config_over_settings(settings):
    settings.WAGTAIL_JEV_THRESHOLD = 0.1
    tag_field = ArticlePage.jev_tag_field("feeling_tags")
    assert tag_field.threshold == 0.8
    assert "mood" in tag_field.templates.instructions


def test_unknown_field_raises_lookup_error():
    with pytest.raises(LookupError, match="nope"):
        ArticlePage.jev_tag_field("nope")


def test_candidates_default_to_the_tag_model_behind_the_field(tags):
    assert ArticlePage.jev_tag_field("tags").candidates(ARTICLE) == ["cooking", "django", "python"]
    assert ArticlePage.jev_tag_field("feeling_tags").candidates(ARTICLE) == ["angry", "calm"]


def test_candidates_exclude_the_articles_existing_tags(tags):
    article = Article(title="t", body="b", existing_tags=("django",))
    assert ArticlePage.jev_tag_field("tags").candidates(article) == ["cooking", "python"]


def test_candidates_setting_overrides_the_tag_model(tags, settings):
    settings.WAGTAIL_JEV_CANDIDATES = "tests.test_tag_field.fixed_candidates"
    assert ArticlePage.jev_tag_field("tags").candidates(ARTICLE) == ["alpha", "beta"]


def test_field_config_candidates_override_everything(tags, settings):
    settings.WAGTAIL_JEV_CANDIDATES = "tests.test_tag_field.fixed_candidates"
    tag_field = JevTagField(candidates=lambda: ["only"]).bind(ArticlePage, "tags")
    assert tag_field.candidates(ARTICLE) == ["only"]


def test_candidates_fall_back_to_the_tag_model_setting_for_non_taggable_fields(tags, settings):
    settings.WAGTAIL_JEV_TAG_MODEL = "testapp.FeelingTag"
    tag_field = JevTagField().bind(ArticlePage, "title")
    assert tag_field.candidates(ARTICLE) == ["angry", "calm"]


def _field(candidates, **kwargs):
    return JevTagField(
        candidates=lambda: candidates,
        templates=PromptTemplates("Q {tag}", "T {tag}", "F {tag}"),
        **kwargs,
    ).bind(ArticlePage, "tags")


def test_score_returns_every_candidate_sorted_high_to_low(fake_client):
    client = fake_client({"python": 0.9, "django": 0.7, "cooking": 0.1})
    article = Article(title="Django ORM tips", body="...", existing_tags=("orm",))

    result = _field(["cooking", "django", "python"]).score(article)

    assert [(s.name, s.probability) for s in result] == [("python", 0.9), ("django", 0.7), ("cooking", 0.1)]
    state, questions = client.calls[0]
    assert state == {"article": {"title": "Django ORM tips", "body": "..."}, "existing_tags": ["orm"]}
    assert len(questions) == 3


def test_score_ignores_threshold_and_cap(fake_client):
    fake_client({"a": 0.95, "b": 0.05})
    assert [s.name for s in _field(["a", "b"], threshold=0.9, max_tags=1).score(ARTICLE)] == ["a", "b"]


def test_score_batches_candidates(fake_client, settings):
    settings.WAGTAIL_JEV_BATCH_SIZE = 2
    client = fake_client({"a": 0.1, "b": 0.2, "c": 0.3})
    result = _field(["a", "b", "c"]).score(ARTICLE)
    assert len(client.calls) == 2
    assert [s.name for s in result] == ["c", "b", "a"]


def test_score_dedupes_and_drops_blank_candidates(fake_client):
    client = fake_client({"a": 0.5})
    result = _field(["a", "", " ", "a"]).score(ARTICLE)
    assert [s.name for s in result] == ["a"]
    assert len(client.calls[0][1]) == 1


def test_empty_candidates_makes_no_request(fake_client):
    client = fake_client({})
    assert _field([]).score(ARTICLE) == []
    assert client.calls == []


def test_body_is_truncated_to_max_chars(fake_client, settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    client = fake_client({"a": 0.9})
    _field(["a"]).score(Article(title="t", body="0123456789"))
    assert client.calls[0][0]["article"]["body"] == "01234"


def test_questions_are_built_from_the_fields_templates(fake_client):
    client = fake_client({"python": 0.9})
    _field(["python"]).score(ARTICLE)
    question = client.calls[0][1]["tag_0"]
    assert question.instructions == "Q 'python'"
    assert question.criteria["true"] == "T 'python'"
    assert question.criteria["false"] == "F 'python'"


def test_suggest_keeps_only_at_or_above_threshold_sorted(fake_client):
    client = fake_client({"python": 0.9, "django": 0.6, "cooking": 0.1})
    tag_field = JevTagField(candidates=lambda: ["cooking", "django", "python"]).bind(ArticlePage, "tags")

    result = tag_field.suggest(ARTICLE)

    assert [(s.name, s.probability) for s in result] == [("python", 0.9), ("django", 0.6)]
    state, questions = client.calls[0]
    assert state["article"]["title"] == "Django ORM tips"
    assert len(questions) == 3


def test_suggest_applies_max_tags_and_field_threshold(fake_client):
    fake_client({"a": 0.95, "b": 0.85, "c": 0.5})
    tag_field = JevTagField(candidates=lambda: ["a", "b", "c"], threshold=0.4, max_tags=2).bind(
        ArticlePage, "tags"
    )
    assert [s.name for s in tag_field.suggest(ARTICLE)] == ["a", "b"]


def test_suggest_never_asks_about_existing_tags(fake_client):
    client = fake_client({"python": 0.9, "django": 0.9})
    tag_field = JevTagField(candidates=lambda: ["python", "django"]).bind(ArticlePage, "tags")
    article = Article(title="t", body="b", existing_tags=("django",))

    result = tag_field.suggest(article)

    assert [s.name for s in result] == ["python"]
    state, questions = client.calls[0]
    assert len(questions) == 1
    assert state["existing_tags"] == ["django"]


def fixed_candidates():
    return ["alpha", "beta"]
