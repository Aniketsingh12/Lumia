"""
Webhook Authenticity Verification
==================================

Channel webhooks (`/api/channels/{whatsapp,instagram,slack}/...`) cannot use the
JWT dependency every other endpoint uses — they are called by Meta and Slack, not
by a logged-in user, so they have to accept anonymous POSTs from the internet.

That makes them the cheapest way to spend someone else's inference budget: each
one runs the full `AIEngine.process_message()` pipeline (an intent-classification
call plus an answer-generation call) against the deployment's own provider key.
Before this module existed, a forged payload sent to the public webhook URL was
processed exactly like a genuine one.

Providers sign their requests precisely so this can be detected:

  Meta (WhatsApp / Instagram)
      X-Hub-Signature-256: sha256=<hex>
      hex = HMAC-SHA256(app_secret, raw_request_body)

  Slack
      X-Slack-Request-Timestamp: <unix seconds>
      X-Slack-Signature: v0=<hex>
      hex = HMAC-SHA256(signing_secret, "v0:{timestamp}:{raw_body}")

Two details that matter:

  * The HMAC is over the RAW bytes, not a re-serialised dict — `json.dumps` of a
    parsed payload will not reproduce the provider's byte sequence (key order and
    whitespace differ), so callers must pass `await request.body()`.

  * The payload has to be parsed to work out WHICH bot a message is for, and
    therefore which secret to check it against, before the signature can be
    verified. That ordering is safe as long as the parsed content is used only to
    look up the secret — nothing may act on it until `verify_*` returns True.

Enforcement is deliberately conditional: a bot with no secret configured cannot
be verified, and hard-failing would break every already-connected channel. Those
requests fall through to the rate limiter and the per-bot daily quota instead,
which bound the damage regardless of authenticity.
"""

import hashlib
import hmac
import time

# Slack rejects anything older than five minutes; matching that stops a captured
# request from being replayed indefinitely.
_SLACK_MAX_SKEW_SECONDS = 300


def verify_meta_signature(raw_body: bytes, header: str | None, app_secret: str | None) -> bool:
    """
    Validate Meta's `X-Hub-Signature-256` header against the raw request body.

    Returns False when the header is missing or malformed. Returns True when no
    `app_secret` is configured — the caller cannot verify what it has no key for,
    and treats that case as "unverified" rather than "rejected" (see module docstring).
    """
    if not app_secret:
        return True  # nothing to verify against; caller falls back to rate limits
    if not header or not header.startswith("sha256="):
        return False

    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # compare_digest keeps the comparison constant-time, so a forged signature
    # can't be recovered byte-by-byte by timing repeated requests.
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def verify_slack_signature(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    signing_secret: str | None,
) -> bool:
    """
    Validate Slack's `X-Slack-Signature`, including the replay window.

    As above, returns True when no signing secret is configured.
    """
    if not signing_secret:
        return True
    if not signature or not timestamp:
        return False

    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False

    if abs(time.time() - sent_at) > _SLACK_MAX_SKEW_SECONDS:
        return False  # too old (or too far in the future) to be a live request

    basestring = b"v0:" + timestamp.encode() + b":" + raw_body
    expected = "v0=" + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
