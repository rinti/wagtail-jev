# Clef

[Clef](https://huggingface.co/Cloudflare/clef) is the decision model of Cloudflare.
Clef operates on Workers AI, the AI platform of Cloudflare.
Cloudflare sends you the invoices for the requests.
Clef accepts the same questions as Jev and returns its results in the same format.

Tag suggestions and Ratings operate as with Jev.
The buttons show "Clef", not "Jev".

## Connect to Clef

You must have a Cloudflare account ID and an API token with Workers AI permission.
Add them to your Django settings:

```python
WAGTAIL_JEV_BACKEND = "clef"
WAGTAIL_JEV_CLEF_ACCOUNT_ID = "your-account-id"   # or the CLOUDFLARE_ACCOUNT_ID environment variable
WAGTAIL_JEV_CLEF_API_TOKEN = "your-api-token"     # or the CLOUDFLARE_API_TOKEN environment variable
```

Workers AI accepts a maximum of 64 questions in one request.
Thus, keep `WAGTAIL_JEV_BATCH_SIZE` at 64 or less.
The default value is 40.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `WAGTAIL_JEV_CLEF_ACCOUNT_ID` | `None` | Your Cloudflare account ID. If you do not set it, wagtail-jev uses the `CLOUDFLARE_ACCOUNT_ID` environment variable |
| `WAGTAIL_JEV_CLEF_API_TOKEN` | `None` | A Cloudflare API token with Workers AI permission. If you do not set it, wagtail-jev uses the `CLOUDFLARE_API_TOKEN` environment variable |
| `WAGTAIL_JEV_CLEF_MODEL` | `"clef"` | `"clef"`, or `"clef-flash"` for the smaller and faster model |

`WAGTAIL_JEV_TIMEOUT` is also applicable to Clef.
For the general settings, refer to [Settings](../settings.md).

## Default values for Clef

Clef uses the same default values as Jev:

- The same [prompt templates](../tags.md#prompt-templates).
- The same JSON data. Refer to [The data that Jev receives](jev.md#the-data-that-jev-receives).
- The same `WAGTAIL_JEV_MAX_CHARS` of 12000.

We did not tune these values for Clef.
Before you use Clef, examine its Suggestions and Ratings on your pages.
Refer to [Tune the threshold](../tags.md#tune-the-threshold).
