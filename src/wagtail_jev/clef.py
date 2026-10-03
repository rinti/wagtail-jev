"""Clef as an alternative to Jev: Cloudflare's decision model, hosted on Workers AI.

Clef takes Jev's request body and answers with Jev's response body, so a ``TypeSafeClient``
does the work: questions, retries, timeouts, errors and answers are the SDK's, and nothing
above ``get_client()`` knows which model answered. Only the wire differs. Workers AI serves
Clef at ``/client/v4/accounts/{account}/ai/run/@cf/cloudflare/{model}`` instead of
``/v1/systemone``, and wraps every answer in Cloudflare's envelope
(``{"result": ..., "success": ..., "errors": [...]}``). :class:`WorkersAITransport` sends the
SDK's request to that URL and unwraps the envelope before the SDK reads it.
"""

from __future__ import annotations

import json

import httpx2
from typesafe_sdk import TypeSafeClient, TypeSafeError

API_ROOT = "https://api.cloudflare.com/client/v4/accounts"
SYSTEM_ONE_PATH = "/v1/systemone"
# Set again by httpx2.Response for the unwrapped body, or wrong once the body is decoded.
STALE_HEADERS = ("content-encoding", "content-length", "transfer-encoding")


def make_client(
    *,
    account_id: str | None,
    api_token: str | None,
    model: str,
    timeout: float,
    transport: httpx2.BaseTransport | None = None,
) -> TypeSafeClient:
    """A ``TypeSafeClient`` that asks ``model`` ("clef" or "clef-flash") on Workers AI.

    ``transport`` carries the requests; tests pass an ``httpx2.MockTransport``. Raises
    :class:`TypeSafeError` when the account or token is missing, as the SDK does for a missing
    Jev key, rather than letting the SDK fall back to ``TYPESAFE_API_KEY`` and send that to
    Cloudflare.
    """
    if not account_id:
        raise TypeSafeError(
            "No Cloudflare account ID for Clef. Set WAGTAIL_JEV_CLEF_ACCOUNT_ID "
            "or the CLOUDFLARE_ACCOUNT_ID environment variable."
        )
    if not api_token:
        raise TypeSafeError(
            "No Cloudflare API token for Clef. Set WAGTAIL_JEV_CLEF_API_TOKEN "
            "or the CLOUDFLARE_API_TOKEN environment variable."
        )
    return TypeSafeClient(
        api_key=api_token,
        model=model,
        timeout=timeout,
        base_url=f"{API_ROOT}/{account_id}/ai/run/@cf/cloudflare/{model}",
        transport=WorkersAITransport(transport or httpx2.HTTPTransport()),
    )


class WorkersAITransport(httpx2.BaseTransport):
    """Sends the SDK's ``/v1/systemone`` request to the Workers AI URL it is based on, and
    answers with the ``result`` of Cloudflare's envelope, or its error messages."""

    def __init__(self, transport: httpx2.BaseTransport):
        self._transport = transport

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        request.url = request.url.copy_with(path=request.url.path.removesuffix(SYSTEM_ONE_PATH))
        response = self._transport.handle_request(request)
        try:
            envelope = json.loads(response.read())
        except ValueError:  # not Cloudflare's JSON (a proxy's HTML page): the SDK reports it as is
            return response
        if not isinstance(envelope, dict) or "success" not in envelope:
            return response
        body = envelope.get("result") if envelope["success"] else {"message": _messages(envelope)}
        headers = [(name, value) for name, value in response.headers.items() if name.lower() not in STALE_HEADERS]
        return httpx2.Response(response.status_code, headers=headers, json=body, request=request)

    def close(self) -> None:
        self._transport.close()


def _messages(envelope: dict) -> str:
    """Cloudflare's error messages as one line, for the SDK's error to show."""
    errors = envelope.get("errors") or []
    messages = [str(error.get("message", error)) if isinstance(error, dict) else str(error) for error in errors]
    return "; ".join(messages) or "Workers AI did not answer"
