# Development

## Run the tests

Install the package in a virtualenv and run the tests:

```sh
uv venv
uv pip install -e ".[test]"
pytest
```

## Use the buttons in a browser

The `tests/manual_e2e.py` script starts a local site.
The site uses a simulated Jev.
Thus, an API key is not necessary.

1. Start the site:

   ```sh
   python tests/manual_e2e.py
   ```

2. Log in at http://127.0.0.1:8765/admin/. The username is `admin` and the password is `pw`.
3. Open the "Django tips" page.

The script also shows the Ratings of that page in the terminal.

## Options of the script

| Option | Backend | Data that the script reads from `.env` |
| --- | --- | --- |
| `--live` | The real Jev | `WAGTAIL_API_KEY` or `TYPESAFE_API_KEY` |
| `--laya` | Laya in the same process. Install it first with `pip install -e ".[laya,test]"` | None |
| `--laya-url http://127.0.0.1:8000` | A Laya server from `python -m laya.serve` | None |
| `--clef` | Clef on Workers AI | `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` |
| `--openai` | The Decisions API of OpenAI | `OPENAI_API_KEY` |

To use a different port, add `--port 8766`.
