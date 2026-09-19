"""Manual check of the editor button.

    python tests/manual_e2e.py          # stubbed Jev, no network
    python tests/manual_e2e.py --live   # real Jev; reads WAGTAIL_API_KEY / TYPESAFE_API_KEY from .env

Then log in at http://127.0.0.1:8765/admin/ as admin / pw and edit "Django tips".
"""

import os
import sys
from pathlib import Path

sys.path[:0] = ["src", "."]
LIVE = "--live" in sys.argv


def load_dotenv(path=Path(".env")):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


if LIVE:
    load_dotenv()
    key = os.environ.get("WAGTAIL_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("No WAGTAIL_API_KEY or TYPESAFE_API_KEY found in .env or environment")
    os.environ["WAGTAIL_JEV_API_KEY"] = key

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.e2e_settings"
import django  # noqa: E402

django.setup()

from django.core.management import call_command, execute_from_command_line  # noqa: E402

if not LIVE:
    import wagtail_jev.classifier as classifier
    from tests.conftest import FakeClient

    classifier.get_client = lambda: FakeClient(
        {"python": 0.93, "django": 0.71, "cooking": 0.05, "travel": 0.02,
         "finance": 0.1, "sport": 0.03, "calm": 0.9, "tense": 0.3, "joyful": 0.82,
         "nostalgic": 0.1}
    )

db = Path("tests/test.db")
if db.exists():
    db.unlink()
call_command("migrate", verbosity=0)

from django.contrib.auth import get_user_model  # noqa: E402
from taggit.models import Tag  # noqa: E402
from wagtail.models import Page  # noqa: E402

from tests.testapp.models import ArticlePage, FeelingTag  # noqa: E402

get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
for name in ["python", "django", "cooking", "travel", "finance", "sport"]:
    Tag.objects.create(name=name)
for name in ["calm", "tense", "joyful", "nostalgic"]:
    FeelingTag.objects.create(name=name)
root = Page.objects.get(depth=1)
page = root.add_child(
    instance=ArticlePage(
        title="Django tips",
        slug="django-tips",
        intro="<p>Five ORM tricks that make Django queries faster: select_related, "
        "prefetch_related, only(), annotate() and database indexes.</p>",
    )
)
print(f"Edit page: http://127.0.0.1:8765/admin/pages/{page.id}/edit/  (admin / pw)")
print("Mode:", "LIVE Jev" if LIVE else "stubbed Jev")
execute_from_command_line(["manage", "runserver", "8765", "--noreload"])
