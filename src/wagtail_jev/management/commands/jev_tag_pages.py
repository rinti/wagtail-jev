"""Bulk tag pages with Jev.

    manage.py jev_tag_pages blog.BlogPage --threshold 0.7 --apply
    manage.py jev_tag_pages blog.BlogPage --field feeling_tags

Without --apply it only prints suggestions. With --apply it adds tags to a
new draft revision, and with --publish it publishes that revision too.
Without --field every field in the model's ``jev_tag_fields`` is processed.
"""

from dataclasses import replace

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from typesafe_sdk import TypeSafeError

from wagtail_jev import client as jev_client
from wagtail_jev.article import Article
from wagtail_jev.models import JevTaggableMixin


class Command(BaseCommand):
    help = "Suggest or apply Jev tags for all live pages of a page model."

    def add_arguments(self, parser):
        parser.add_argument("model", help="app_label.ModelName of a JevTaggableMixin page")
        parser.add_argument("--field", action="append", dest="fields", help="Tag field(s) to process")
        parser.add_argument("--threshold", type=float, default=None)
        parser.add_argument("--max-tags", type=int, default=None)
        parser.add_argument("--apply", action="store_true", help="Save suggestions as a draft")
        parser.add_argument("--publish", action="store_true", help="Publish after applying")
        parser.add_argument("--ids", nargs="*", type=int, help="Restrict to these page IDs")

    def handle(self, *args, **options):
        model = apps.get_model(options["model"])
        if not issubclass(model, JevTaggableMixin):
            raise CommandError(f"{options['model']} does not use JevTaggableMixin")

        overrides = {}
        if options["threshold"] is not None:
            overrides["threshold"] = options["threshold"]
        if options["max_tags"] is not None:
            overrides["max_tags"] = options["max_tags"]

        names = options["fields"] or list(model.jev_tag_fields)
        try:
            tag_fields = [replace(model.jev_tag_field(name), **overrides) for name in names]
        except LookupError as exc:
            raise CommandError(str(exc)) from None

        queryset = model.objects.live()
        if options["ids"]:
            queryset = queryset.filter(id__in=options["ids"])

        with jev_client.get_client() as client:
            for page in queryset.iterator():
                changed = False
                for tag_field in tag_fields:
                    label = f"[{page.id}] {page.title} / {tag_field.name}"
                    article = Article.from_page(page, tag_field.name)
                    try:
                        suggestions = tag_field.suggest(article, client=client)
                    except TypeSafeError as exc:
                        self.stderr.write(f"{label}: {exc}")
                        continue

                    summary = ", ".join(f"{s.name} ({s.percent}%)" for s in suggestions) or "-"
                    self.stdout.write(f"{label}: {summary}")

                    if options["apply"] and suggestions:
                        getattr(page, tag_field.name).add(*(s.name for s in suggestions))
                        changed = True

                if changed:
                    revision = page.save_revision(log_action=True)
                    if options["publish"]:
                        revision.publish()
