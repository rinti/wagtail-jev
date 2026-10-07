"""Manual check of the editor button and the Python rating API.

    python tests/manual_e2e.py          # stubbed Jev, no network
    python tests/manual_e2e.py --live   # real Jev; reads WAGTAIL_API_KEY / TYPESAFE_API_KEY from .env
    python tests/manual_e2e.py --laya                             # real Laya in this process
    python tests/manual_e2e.py --laya-url http://127.0.0.1:8000   # a running `python -m laya.serve`
    python tests/manual_e2e.py --clef   # Clef on Workers AI; reads CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN from .env
    python tests/manual_e2e.py --openai # OpenAI's Decisions API; reads OPENAI_API_KEY from .env
    python tests/manual_e2e.py --port 8766                        # serve the admin on another port

Prints the Ratings of the seeded page on every declared Quality, then serves the admin.
Log in at http://127.0.0.1:<port>/admin/ as admin / pw and edit "Django tips".
"""

import os
import sys
from pathlib import Path

sys.path[:0] = ["src", "."]
LIVE = "--live" in sys.argv
LAYA_URL = sys.argv[sys.argv.index("--laya-url") + 1] if "--laya-url" in sys.argv else None
LAYA = "--laya" in sys.argv or LAYA_URL is not None
CLEF = "--clef" in sys.argv
OPENAI = "--openai" in sys.argv
PORT = sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "8765"
if LAYA:
    os.environ["WAGTAIL_JEV_BACKEND"] = "laya"
    if LAYA_URL:
        os.environ["WAGTAIL_JEV_LAYA_URL"] = LAYA_URL
if CLEF:
    os.environ["WAGTAIL_JEV_BACKEND"] = "clef"
if OPENAI:
    os.environ["WAGTAIL_JEV_BACKEND"] = "openai"


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

if CLEF:
    load_dotenv()
    missing = [name for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN") if not os.environ.get(name)]
    if missing:
        sys.exit(f"No {' or '.join(missing)} found in .env or environment")

if OPENAI:
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("No OPENAI_API_KEY found in .env or environment")

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.e2e_settings"
import django  # noqa: E402

django.setup()

from django.core.management import call_command, execute_from_command_line  # noqa: E402

if not LIVE and not LAYA and not CLEF and not OPENAI:
    import wagtail_jev.client as jev_client
    from tests.conftest import FakeClient

    jev_client.get_client = lambda: FakeClient(
        {"python": 0.93, "django": 0.71, "cooking": 0.05, "travel": 0.02,
         "finance": 0.1, "sport": 0.03, "calm": 0.9, "tense": 0.3, "joyful": 0.82,
         "nostalgic": 0.1},
        distributions={"readability": [0.6, 0.3, 0.1], "mood": [0.05, 0.75, 0.2]},
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
print(
    "Mode:",
    f"Laya server at {LAYA_URL}" if LAYA_URL else "Laya in this process" if LAYA
    else "Clef on Workers AI" if CLEF else "OpenAI's Decisions API" if OPENAI
    else "LIVE Jev" if LIVE else "stubbed Jev",
)
print("Ratings for", repr(page.title))
for rating in page.jev_rate():
    distribution = ", ".join(
        f"{level.label} {round(p * 100)}%" for level, p in zip(rating.levels, rating.probabilities)
    )
    print(f"  {rating.key}: {rating.top_label} ({rating.percent}%)  [{distribution}]")
print(f"Edit page: http://127.0.0.1:{PORT}/admin/pages/{page.id}/edit/  (admin / pw)")
execute_from_command_line(["manage", "runserver", PORT, "--noreload"])
