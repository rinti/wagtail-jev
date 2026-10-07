# Laya

[Laya](https://huggingface.co/convaiinnovations/laya) is an open-source decision model.
It accepts the same type of questions as Jev.
Laya operates in your Django process or on a server that you operate.
Thus, you do not get invoices for requests.
The text of your pages stays on your infrastructure.

Tag suggestions and Ratings operate as with Jev.
The buttons show "Laya", not "Jev".

You can use Laya in two configurations:

- [In the Django process](#laya-in-the-django-process). Each web worker loads a copy of the model.
- [On a Laya server](#laya-on-a-laya-server). The Laya server keeps one copy of the model in memory. Use a GPU machine for this server if you can.

## Laya in the Django process

1. Install wagtail-jev with the `laya` extra:

   ```sh
   pip install "wagtail-jev[laya]"
   ```

2. Set the backend in your Django settings:

   ```python
   WAGTAIL_JEV_BACKEND = "laya"
   ```

Laya downloads the model from Hugging Face when you use it for the first time.
After each restart, Laya loads the model on the first click.
Thus, the first request can continue for up to one minute.
After three seconds, the button shows "Loading Laya…".
Subsequent requests are faster: less than one second on a GPU, and some seconds on a CPU.

Your web server can stop slow requests.
For example, the default timeout of gunicorn is 30 seconds.
If your web server stops the first request, increase its timeout or use a Laya server.

## Laya on a Laya server

1. On the Laya machine, install Laya:

   ```sh
   pip install "laya[serve]"
   ```

2. Start the server:

   ```sh
   LAYA_API_KEY=choose-a-secret python -m laya.serve     # listens on :8000
   ```

3. In your Django settings, set the backend and the URL of the server:

   ```python
   WAGTAIL_JEV_BACKEND = "laya"
   WAGTAIL_JEV_LAYA_URL = "http://laya.internal:8000"
   WAGTAIL_JEV_LAYA_API_KEY = "choose-a-secret"   # or the LAYA_API_KEY environment variable
   ```

`laya.serve` accepts a maximum of 64 questions in one request.
Thus, keep `WAGTAIL_JEV_BATCH_SIZE` at 64 or less.
The default value is 40.

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `WAGTAIL_JEV_LAYA_URL` | `None` | The base URL of a Laya server. If you do not set it, Laya operates in the Django process |
| `WAGTAIL_JEV_LAYA_API_KEY` | `None` | The `LAYA_API_KEY` of the server. If you do not set it, wagtail-jev uses the `LAYA_API_KEY` environment variable |
| `WAGTAIL_JEV_LAYA_MODEL` | `None` | `"english"` or `"multilingual"`. If you do not set it, Laya selects a model for each request from the language of the text |

`WAGTAIL_JEV_TIMEOUT` is also applicable to the requests to a Laya server.
For the general settings, refer to [Settings](../settings.md).

## Default values for Laya

The default values for Laya are different from the default values for Jev.
We measured these values with English and Swedish pages.
With the prompt templates of Jev, Laya did not find a clear difference between correct and incorrect tags.
These changes gave much better results:

- wagtail-jev sends the page as plain text: the title, an empty line, and the body.
  It does not send `article` or `existing_tags`.
- wagtail-jev does not put quotes around the tag names.
- The default prompt templates are short:

  ```python
  WAGTAIL_JEV_INSTRUCTIONS = "Is `state` about {tag}?"
  WAGTAIL_JEV_CRITERIA_TRUE = "about {tag}"
  WAGTAIL_JEV_CRITERIA_FALSE = "not about {tag}"
  ```

- wagtail-jev sends only the first 2000 characters of the text.
  Laya does not read much more text than this.

Your prompt templates and your `WAGTAIL_JEV_MAX_CHARS` setting override these default values.
If you write prompt templates for Laya, keep them as short as these.

## Ratings on Laya

We did a test with 10 pages: 7 English pages and 3 Swedish pages.
The test gave 20 Ratings.
10 of the 20 Ratings had the same level as the level from an editor.
The mood Ratings were usually correct in English.
But the readability Rating was "Medium" for 9 of the 10 pages.

Before you use Ratings from Laya, compare them with the Ratings of a person.

For Ratings, Laya also reads plain text.
For a full page, Laya reads the title and the body.
For an Excerpt, Laya reads only the text of the field.

## Errors

These problems cause an error:

- Laya is the backend, but Laya is not installed.
- Laya cannot start.
- wagtail-jev cannot connect to the Laya server.

The editor sees an error message with the name of the problem.
The `jev_tag_pages` command stops immediately.
