# Jev

[Jev](https://docs.typesafe.ai) is the AI decision model of TypeSafe.
Jev is the default backend.
Jev operates on the servers of TypeSafe.
TypeSafe sends you the invoices for the requests.

## Connect to Jev

Add your TypeSafe API key to your Django settings:

```python
WAGTAIL_JEV_API_KEY = "..."  # or the TYPESAFE_API_KEY environment variable
```

It is not necessary to set `WAGTAIL_JEV_BACKEND`, because the default value is `"jev"`.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `WAGTAIL_JEV_API_KEY` | `None` | Your TypeSafe API key. If you do not set it, wagtail-jev uses the `TYPESAFE_API_KEY` environment variable |
| `WAGTAIL_JEV_MODEL` | `"jev-latest"` | The version of Jev. After you tune the threshold, set one version, not `"jev-latest"`. Then a new version of Jev cannot change your results |

These settings are only for Jev.
For the general settings, refer to [Settings](../settings.md).

## The data that Jev receives

For tag suggestions, Jev receives the page as JSON data:

- `article` contains the `title` and the `body` of the page.
- `existing_tags` contains the existing tags of the tag field.

wagtail-jev puts quotes around each tag name in the question.

For a Rating of a full page, Jev receives `article` with the `title` and the `body`.
For a Rating of an Excerpt, Jev receives only `text`.

The default prompt templates refer to `article`.
Refer to [Prompt templates](../tags.md#prompt-templates).
The default value of `WAGTAIL_JEV_MAX_CHARS` is 12000.
