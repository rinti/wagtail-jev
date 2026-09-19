from wagtail_jev.classifier import score_tags, suggest_tags


def test_suggest_tags_keeps_only_above_threshold_sorted(fake_client):
    client = fake_client({"python": 0.9, "django": 0.7, "cooking": 0.1})
    result = suggest_tags(
        title="Django ORM tips", body="...", candidates=["cooking", "django", "python"]
    )
    assert [(s.name, s.probability) for s in result] == [("python", 0.9), ("django", 0.7)]
    state, questions = client.calls[0]
    assert state["article"]["title"] == "Django ORM tips"
    assert len(questions) == 3


def test_suggest_tags_respects_max_tags_and_custom_threshold(fake_client):
    fake_client({"a": 0.95, "b": 0.85, "c": 0.5})
    result = suggest_tags(title="t", body="b", candidates=["a", "b", "c"], threshold=0.4, max_tags=2)
    assert [s.name for s in result] == ["a", "b"]


def test_score_tags_batches_candidates(fake_client, settings):
    settings.WAGTAIL_JEV_BATCH_SIZE = 2
    client = fake_client({"a": 0.1, "b": 0.2, "c": 0.3})
    result = score_tags(title="t", body="b", candidates=["a", "b", "c"])
    assert len(client.calls) == 2
    assert [s.name for s in result] == ["c", "b", "a"]


def test_empty_candidates_makes_no_request(fake_client):
    client = fake_client({})
    assert suggest_tags(title="t", body="b", candidates=[]) == []
    assert client.calls == []


def test_body_is_truncated_to_max_chars(fake_client, settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    client = fake_client({"a": 0.9})
    suggest_tags(title="t", body="0123456789", candidates=["a"])
    assert client.calls[0][0]["article"]["body"] == "01234"


def test_prompt_templates_come_from_settings(fake_client, settings):
    settings.WAGTAIL_JEV_INSTRUCTIONS = "Is this about {tag}?"
    settings.WAGTAIL_JEV_CRITERIA_TRUE = "yes {tag}"
    settings.WAGTAIL_JEV_CRITERIA_FALSE = "no {tag}"
    client = fake_client({"python": 0.9})
    suggest_tags(title="t", body="b", candidates=["python"])
    question = client.calls[0][1]["tag_0"]
    assert question.instructions == "Is this about 'python'?"
    assert question.criteria["true"] == "yes 'python'"
    assert question.criteria["false"] == "no 'python'"


def test_prompt_templates_can_be_passed_per_model(fake_client):
    from wagtail_jev.classifier import PromptTemplates

    client = fake_client({"python": 0.9})
    templates = PromptTemplates("Q {tag}", "T {tag}", "F {tag}")
    suggest_tags(title="t", body="b", candidates=["python"], templates=templates)
    assert client.calls[0][1]["tag_0"].instructions == "Q 'python'"
