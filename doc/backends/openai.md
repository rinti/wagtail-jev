# OpenAI

The [Decisions API](https://developers.openai.com/api/docs/guides/decisions) of OpenAI accepts the same type of questions as Jev.
It uses the `gpt-6-luna` model.
OpenAI sends you the invoices for the requests.
The Decisions API is in public beta.

Tag suggestions and Ratings operate as with Jev.
The buttons show "OpenAI", not "Jev".

## Connect to OpenAI

Add your OpenAI API key to your Django settings:

```python
WAGTAIL_JEV_BACKEND = "openai"
WAGTAIL_JEV_OPENAI_API_KEY = "sk-..."   # or the OPENAI_API_KEY environment variable
```

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `WAGTAIL_JEV_OPENAI_API_KEY` | `None` | Your OpenAI API key. If you do not set it, wagtail-jev uses the `OPENAI_API_KEY` environment variable |
| `WAGTAIL_JEV_OPENAI_MODEL` | `"gpt-6-luna"` | The Decisions model. At this time, `gpt-6-luna` is the only Decisions model |
| `WAGTAIL_JEV_OPENAI_BASE_URL` | `"https://api.openai.com/v1"` | The address of the OpenAI API. For a project with European data residency, use `"https://eu.api.openai.com/v1"` |

`WAGTAIL_JEV_TIMEOUT` is also applicable to OpenAI.
For the general settings, refer to [Settings](../settings.md).

## Differences from Jev

The requests to OpenAI are different from the requests to Jev:

- wagtail-jev sends the page as plain text: the title, an empty line, and the body.
  It does not send the existing tags.
- The default question is "Would an editor file this article under the tag {tag}? …".
  This question does not refer to `article`, because OpenAI does not receive `article`.
- The conditions for "yes" and "no" are the same as for Jev.
  The Decisions API does not have a field for these conditions.
  Thus, wagtail-jev adds them to the question as a "True: …" line and a "False: …" line.
- The levels of a Rating have the labels 0, 1, 2, and more.
  OpenAI examines the descriptions of your levels.
  OpenAI does not see the labels of your levels.

The default value of `WAGTAIL_JEV_MAX_CHARS` is 12000, the same as for Jev.

## Errors

If OpenAI does not give a result for one question, wagtail-jev gives an error for the full request.
The error message gives the name of that question.

We did not tune the default values for OpenAI.
Before you use OpenAI, examine its Suggestions and Ratings on your pages.
Refer to [Tune the threshold](../tags.md#tune-the-threshold).
