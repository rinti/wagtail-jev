# Settings

Put these settings in your Django settings file.
All the settings are optional.
But Jev, Clef and OpenAI must have an API key.
Refer to the page of your backend.

## General settings

| Setting | Default | Description |
| --- | --- | --- |
| `WAGTAIL_JEV_BACKEND` | `"jev"` | The backend: `"jev"`, `"laya"`, `"clef"` or `"openai"`. Refer to [Backend settings](#backend-settings) |
| `WAGTAIL_JEV_THRESHOLD` | `0.6` | The minimum probability of a tag. wagtail-jev adds a tag only if its probability is at this value or higher |
| `WAGTAIL_JEV_MAX_TAGS` | `None` | The maximum number of new tags for one tag field. `None` sets no maximum |
| `WAGTAIL_JEV_MAX_CHARS` | Jev, Clef and OpenAI: `12000`. Laya: `2000` | wagtail-jev sends only this number of characters of the text. `None` sends all the text |
| `WAGTAIL_JEV_BATCH_SIZE` | `40` | The maximum number of candidate tags in one request |
| `WAGTAIL_JEV_TAG_MODEL` | `"taggit.Tag"` | The tag model for candidate tags, if wagtail-jev cannot find the tag model of the tag field |
| `WAGTAIL_JEV_CANDIDATES` | `None` | A function that returns tag names, or the dotted path to that function. If you set it, wagtail-jev uses it for the candidate tags, not the tag model |
| `WAGTAIL_JEV_TIMEOUT` | `30.0` | The maximum time for one request, in seconds |
| `WAGTAIL_JEV_INSTRUCTIONS` | Different for each backend | The question for each candidate tag. Refer to [Prompt templates](tags.md#prompt-templates) |
| `WAGTAIL_JEV_CRITERIA_TRUE` | Different for each backend | The condition for "yes" |
| `WAGTAIL_JEV_CRITERIA_FALSE` | Different for each backend | The condition for "no" |

If you do not set `WAGTAIL_JEV_MAX_CHARS`, wagtail-jev uses the default value of the backend.
This is also true for the prompt templates.

## Settings for one tag field

You can also set some of these settings for one tag field only.
Give the applicable argument to the `JevTagField` of that field.
Refer to [More than one tag field](tags.md#more-than-one-tag-field).

## Backend settings

Each backend has more settings.
Refer to the page of the backend:

- [Jev](backends/jev.md): `WAGTAIL_JEV_API_KEY` and `WAGTAIL_JEV_MODEL`
- [Laya](backends/laya.md): `WAGTAIL_JEV_LAYA_URL`, `WAGTAIL_JEV_LAYA_API_KEY` and `WAGTAIL_JEV_LAYA_MODEL`
- [Clef](backends/clef.md): `WAGTAIL_JEV_CLEF_ACCOUNT_ID`, `WAGTAIL_JEV_CLEF_API_TOKEN` and `WAGTAIL_JEV_CLEF_MODEL`
- [OpenAI](backends/openai.md): `WAGTAIL_JEV_OPENAI_API_KEY`, `WAGTAIL_JEV_OPENAI_MODEL` and `WAGTAIL_JEV_OPENAI_BASE_URL`

`WAGTAIL_JEV_TIMEOUT` is applicable to all the backends.
