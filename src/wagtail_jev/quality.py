"""Qualities and Ratings: Jev judging an Article or an Excerpt on a developer-declared spectrum.

A ``Quality`` is an ordered rubric of levels, each with a short label for the editor
and a concrete description for Jev. ``Quality.bind`` checks the declaration against a
model and key once, producing a ``BoundQuality``, the one place that turns a subject
(an Article or an Excerpt) into a ``Rating``. Several bound Qualities are rated against
one subject in a single Jev request by :func:`rate`; one Score question per Quality,
keyed by the Quality key.

Per ADR 0001 a Rating trusts the per-level probabilities, not the rounded expected
level: the top level is the argmax of the distribution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence, Union

from typesafe_sdk import Score, TypeSafeClient

from wagtail_jev import classifier
from wagtail_jev.article import Article, Excerpt
from wagtail_jev.settings import get_setting

logger = logging.getLogger(__name__)

MIN_LEVELS = 2
MAX_LEVELS = 10

Subject = Union[Article, Excerpt]


@dataclass(frozen=True)
class Level:
    """One step of a Quality's rubric.

    :param label: what the editor sees, e.g. ``"Easy"``.
    :param description: what Jev judges: a concrete situation, phrased about "the text".
    """

    label: str
    description: str


@dataclass(frozen=True)
class Quality:
    """A spectrum a text can be judged on, declared once under a key in ``jev_qualities``.

    :param instructions: the question Jev answers, e.g. "How easy is the text to understand?".
    :param levels: ordered rubric from the lowest level to the highest; 2 to 10 levels.
    :param label: what the editor sees the Quality called, e.g. ``"Readability"``; the key when unset.
    """

    instructions: str
    levels: tuple[Level, ...]
    label: str | None = None

    def bind(self, model, key: str) -> "BoundQuality":
        """Check the declaration and attach it to ``key`` on ``model``.

        Raises :class:`ValueError` when the rubric has fewer than 2 or more than 10 levels.
        """
        if not MIN_LEVELS <= len(self.levels) <= MAX_LEVELS:
            raise ValueError(
                f"{model.__name__}.jev_qualities[{key!r}] must have between {MIN_LEVELS} and "
                f"{MAX_LEVELS} levels, got {len(self.levels)}"
            )
        return BoundQuality(
            model=model,
            key=key,
            label=self.label or key,
            instructions=self.instructions,
            levels=tuple(self.levels),
        )


@dataclass(frozen=True)
class Rating:
    """Jev's judgment of one Quality: a probability per level, never saved.

    ``label`` is the Quality's display name; ``top_label`` is the most likely level's.
    """

    key: str
    label: str
    levels: tuple[Level, ...]
    probabilities: tuple[float, ...]

    @property
    def top_index(self) -> int:
        """Index of the most likely level: the argmax, not the rounded expected level."""
        return max(range(len(self.probabilities)), key=self.probabilities.__getitem__)

    @property
    def top_level(self) -> Level:
        return self.levels[self.top_index]

    @property
    def top_label(self) -> str:
        return self.top_level.label

    @property
    def top_probability(self) -> float:
        return self.probabilities[self.top_index]

    @property
    def percent(self) -> int:
        return round(self.top_probability * 100)


@dataclass(frozen=True)
class BoundQuality:
    """A :class:`Quality` checked and attached to a model and key."""

    model: type
    key: str
    label: str
    instructions: str
    levels: tuple[Level, ...]

    def question(self) -> Score:
        """The Score question for this Quality: criteria are the level descriptions, in order."""
        return Score(instructions=self.instructions, criteria=[level.description for level in self.levels])

    def rate(self, subject: Subject, *, client: TypeSafeClient | None = None) -> Rating | None:
        """Rate an Article or an Excerpt on this Quality alone. ``None`` when there is nothing to rate."""
        ratings = rate([self], subject, client=client)
        return ratings[0] if ratings else None


def rate(
    qualities: Sequence[BoundQuality],
    subject: Subject,
    *,
    client: TypeSafeClient | None = None,
) -> list[Rating]:
    """Rate an Article or an Excerpt on every Quality in one Jev request; Ratings come back
    in the same order.

    A blank subject makes no request and returns no Ratings.
    """
    if not qualities or _is_blank(subject):
        return []

    questions = {quality.key: quality.question() for quality in qualities}
    owns_client = client is None
    client = client or classifier.get_client()
    try:
        response = client.system_one(_state(subject), questions)
    finally:
        if owns_client:
            client.close()
    logger.info("jev rated %d qualities with %s", len(questions), response.model)

    ratings = []
    for quality in qualities:
        answer = response.scores[quality.key]
        probabilities = tuple(answer.probabilities.get(i, 0.0) for i in range(len(quality.levels)))
        ratings.append(
            Rating(key=quality.key, label=quality.label, levels=quality.levels, probabilities=probabilities)
        )
    return ratings


def _is_blank(subject: Subject) -> bool:
    if isinstance(subject, Excerpt):
        return not subject.text.strip()
    return not subject.title.strip() and not subject.body.strip()


def _state(subject: Subject) -> dict:
    """What Jev reads for a Rating, so unrelated material stays out: an Article's title and
    body with no existing tags, or an Excerpt's text alone."""
    max_chars = get_setting("WAGTAIL_JEV_MAX_CHARS")
    if isinstance(subject, Excerpt):
        return {"text": subject.text[:max_chars]}
    return {"article": {"title": subject.title, "body": subject.body[:max_chars]}}
