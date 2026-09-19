from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase, TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from wagtail_jev.classifier import PromptTemplates
from wagtail_jev.models import JevTagField, JevTaggableMixin
from wagtail_jev.quality import Level, Quality
from wagtail_jev.panels import JevTagFieldPanel


class ArticleTag(TaggedItemBase):
    content_object = ParentalKey("testapp.ArticlePage", related_name="tagged_items")


class FeelingTag(TagBase):
    class Meta:
        verbose_name = "feeling"


class ArticleFeeling(ItemBase):
    tag = models.ForeignKey(FeelingTag, on_delete=models.CASCADE, related_name="articles")
    content_object = ParentalKey("testapp.ArticlePage", related_name="feeling_items")


class ArticlePage(JevTaggableMixin, Page):
    intro = RichTextField(blank=True)
    body = StreamField(
        [("paragraph", blocks.RichTextBlock()), ("heading", blocks.CharBlock())],
        blank=True,
    )
    tags = ClusterTaggableManager(through=ArticleTag, blank=True)
    feeling_tags = ClusterTaggableManager(
        through=ArticleFeeling, blank=True, related_name="feeling_tagged"
    )

    jev_text_fields = ("title", "intro", "body")
    jev_tag_fields = {
        "tags": JevTagField(),
        "feeling_tags": JevTagField(
            templates=PromptTemplates(
                instructions="Does the mood of `article` match {tag}?",
                criteria_true="A reader would come away feeling {tag}.",
                criteria_false="{tag} does not describe the article's tone.",
            ),
            threshold=0.8,
        ),
    }
    jev_qualities = {
        "readability": Quality(
            instructions="How easy is the text to understand?",
            levels=(
                Level("Easy", "A first-time reader follows every sentence."),
                Level("Medium", "A reader needs to reread some sentences."),
                Level("Hard", "The text assumes expert knowledge or is densely written."),
            ),
        ),
        "mood": Quality(
            instructions="What mood does the text leave the reader in?",
            levels=(
                Level("Sad", "The text dwells on loss or disappointment."),
                Level("Neutral", "The text reports without emotional colour."),
                Level("Happy", "The text celebrates or reassures."),
            ),
        ),
    }

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
        JevTagFieldPanel("tags"),
        JevTagFieldPanel("feeling_tags"),
    ]
