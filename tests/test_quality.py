import pytest
from typesafe_sdk import Score
from wagtail.rich_text import RichText

from tests.testapp.models import ArticlePage
from wagtail_jev.article import Article, Excerpt
from wagtail_jev.quality import Level, Quality, rate

ARTICLE = Article(title="Django ORM tips", body="select_related and friends")


def _page(**kwargs):
    defaults = dict(title="T", intro="<p>Lead in</p>", body=[("paragraph", RichText("<p>Body</p>"))])
    return ArticlePage(**{**defaults, **kwargs})


def test_lookup_returns_the_bound_quality_for_a_key():
    quality = ArticlePage.jev_quality("readability")
    assert quality.key == "readability"
    assert quality.model is ArticlePage
    assert [level.label for level in quality.levels] == ["Easy", "Medium", "Hard"]


def test_unknown_key_raises_lookup_error_naming_configured_keys():
    with pytest.raises(LookupError, match="nope") as exc:
        ArticlePage.jev_quality("nope")
    assert "readability" in str(exc.value) and "mood" in str(exc.value)


@pytest.mark.parametrize("count", [0, 1, 11])
def test_binding_rejects_fewer_than_two_or_more_than_ten_levels(count):
    levels = tuple(Level(f"L{i}", f"Level {i}.") for i in range(count))
    with pytest.raises(ValueError, match="between 2 and 10"):
        Quality(instructions="?", levels=levels).bind(ArticlePage, "bad")


@pytest.mark.parametrize("count", [2, 10])
def test_binding_accepts_two_and_ten_levels(count):
    levels = tuple(Level(f"L{i}", f"Level {i}.") for i in range(count))
    bound = Quality(instructions="?", levels=levels).bind(ArticlePage, "ok")
    assert bound.key == "ok"
    assert bound.model is ArticlePage


def test_jev_rate_with_no_keys_rates_every_quality_in_one_request(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1], "mood": [0.1, 0.1, 0.8]})

    ratings = _page().jev_rate()

    assert [(r.key, r.top_label) for r in ratings] == [("readability", "Easy"), ("mood", "Happy")]
    assert len(client.calls) == 1
    state, questions = client.calls[0]
    assert list(questions) == ["readability", "mood"]
    assert all(isinstance(q, Score) for q in questions.values())
    assert questions["readability"].instructions == "How easy is the text to understand?"
    assert questions["readability"].criteria == [
        "A first-time reader follows every sentence.",
        "A reader needs to reread some sentences.",
        "The text assumes expert knowledge or is densely written.",
    ]


def test_jev_rate_with_keys_rates_only_those_in_declaration_order(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1], "mood": [0.1, 0.1, 0.8]})
    assert [r.key for r in _page().jev_rate("mood")] == ["mood"]
    assert list(client.calls[0][1]) == ["mood"]

    ratings = _page().jev_rate("mood", "readability")
    assert [r.key for r in ratings] == ["readability", "mood"]


def test_jev_rate_with_an_unknown_key_raises_before_any_request(fake_client):
    client = fake_client()
    with pytest.raises(LookupError, match="nope"):
        _page().jev_rate("nope")
    assert client.calls == []


def test_state_carries_title_and_body_and_no_existing_tags(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1], "mood": [0.1, 0.1, 0.8]})
    _page().jev_rate()
    state, _ = client.calls[0]
    assert state == {"article": {"title": "T", "body": "Lead in\n\nBody"}}


def test_top_level_is_the_argmax_not_the_rounded_expected_level(fake_client):
    # Expected level is 0.9, which rounds to "Medium"; the most likely level is "Easy".
    fake_client(distributions={"readability": [0.55, 0.0, 0.45]})

    rating = ArticlePage.jev_quality("readability").rate(ARTICLE)

    assert rating.top_index == 0
    assert rating.top_label == "Easy"
    assert rating.top_probability == 0.55
    assert rating.percent == 55
    assert rating.probabilities == (0.55, 0.0, 0.45)
    assert [level.label for level in rating.levels] == ["Easy", "Medium", "Hard"]


def test_body_is_truncated_to_max_chars(fake_client, settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1]})
    ArticlePage.jev_quality("readability").rate(Article(title="t", body="0123456789"))
    assert client.calls[0][0]["article"]["body"] == "01234"


def test_blank_article_makes_no_request_and_yields_no_ratings(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1]})
    blank = Article(title=" ", body="")

    assert rate([ArticlePage.jev_quality("readability")], blank) == []
    assert ArticlePage.jev_quality("readability").rate(blank) is None
    assert _page(title="", intro="", body=[]).jev_rate() == []
    assert client.calls == []


def test_quality_label_falls_back_to_the_key():
    assert ArticlePage.jev_quality("readability").label == "Readability"
    assert ArticlePage.jev_quality("mood").label == "mood"


def test_rating_carries_the_quality_label(fake_client):
    fake_client(distributions={"readability": [0.7, 0.2, 0.1], "mood": [0.1, 0.1, 0.8]})
    assert [(r.key, r.label) for r in _page().jev_rate()] == [("readability", "Readability"), ("mood", "mood")]


def test_excerpt_state_is_the_excerpt_alone(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1]})

    rating = ArticlePage.jev_quality("readability").rate(Excerpt(text="Just the intro"))

    assert rating.top_label == "Easy"
    assert client.calls[0][0] == {"text": "Just the intro"}


def test_excerpt_text_is_truncated_to_max_chars(fake_client, settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1]})
    ArticlePage.jev_quality("readability").rate(Excerpt(text="0123456789"))
    assert client.calls[0][0] == {"text": "01234"}


def test_blank_excerpt_makes_no_request_and_yields_no_ratings(fake_client):
    client = fake_client(distributions={"readability": [0.7, 0.2, 0.1]})
    blank = Excerpt(text=" \n")

    assert rate([ArticlePage.jev_quality("readability")], blank) == []
    assert ArticlePage.jev_quality("readability").rate(blank) is None
    assert client.calls == []
