from wagtail_jev.classifier import PromptTemplates, score_tags

TEMPLATES = PromptTemplates("Q {tag}", "T {tag}", "F {tag}")


def test_score_tags_returns_every_candidate_sorted_high_to_low(fake_client):
    client = fake_client({"python": 0.9, "django": 0.7, "cooking": 0.1})
    result = score_tags(
        title="Django ORM tips",
        body="...",
        candidates=["cooking", "django", "python"],
        existing_tags=["orm"],
        templates=TEMPLATES,
    )
    assert [(s.name, s.probability) for s in result] == [
        ("python", 0.9),
        ("django", 0.7),
        ("cooking", 0.1),
    ]
    state, questions = client.calls[0]
    assert state == {"article": {"title": "Django ORM tips", "body": "..."}, "existing_tags": ["orm"]}
    assert len(questions) == 3


def test_score_tags_batches_candidates(fake_client, settings):
    settings.WAGTAIL_JEV_BATCH_SIZE = 2
    client = fake_client({"a": 0.1, "b": 0.2, "c": 0.3})
    result = score_tags(title="t", body="b", candidates=["a", "b", "c"], templates=TEMPLATES)
    assert len(client.calls) == 2
    assert [s.name for s in result] == ["c", "b", "a"]


def test_score_tags_dedupes_and_drops_blank_candidates(fake_client):
    client = fake_client({"a": 0.5})
    result = score_tags(title="t", body="b", candidates=["a", "", " ", "a"], templates=TEMPLATES)
    assert [s.name for s in result] == ["a"]
    assert len(client.calls[0][1]) == 1


def test_empty_candidates_makes_no_request(fake_client):
    client = fake_client({})
    assert score_tags(title="t", body="b", candidates=[], templates=TEMPLATES) == []
    assert client.calls == []


def test_body_is_truncated_to_max_chars(fake_client, settings):
    settings.WAGTAIL_JEV_MAX_CHARS = 5
    client = fake_client({"a": 0.9})
    score_tags(title="t", body="0123456789", candidates=["a"], templates=TEMPLATES)
    assert client.calls[0][0]["article"]["body"] == "01234"


def test_questions_are_built_from_the_given_templates(fake_client):
    client = fake_client({"python": 0.9})
    score_tags(title="t", body="b", candidates=["python"], templates=TEMPLATES)
    question = client.calls[0][1]["tag_0"]
    assert question.instructions == "Q 'python'"
    assert question.criteria["true"] == "T 'python'"
    assert question.criteria["false"] == "F 'python'"
