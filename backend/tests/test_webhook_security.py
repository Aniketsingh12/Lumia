"""
Tests for webhook signature verification.

These matter more than most: the channel webhooks are the only endpoints that
reach the LLM without authentication, so a regression here is a regression that
lets a stranger spend the deployment's inference budget.
"""

import hashlib
import hmac
import time

from app.middleware.webhook_security import verify_meta_signature, verify_slack_signature

SECRET = "test-app-secret"
BODY = b'{"entry":[{"changes":[{"value":{"metadata":{"phone_number_id":"123"}}}]}]}'


def _meta_sig(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _slack_sig(body: bytes, secret: str, ts: str) -> str:
    base = b"v0:" + ts.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


class TestMetaSignature:
    def test_accepts_genuine_signature(self):
        assert verify_meta_signature(BODY, _meta_sig(BODY, SECRET), SECRET)

    def test_rejects_forged_signature(self):
        assert not verify_meta_signature(BODY, "sha256=deadbeef", SECRET)

    def test_rejects_missing_header(self):
        assert not verify_meta_signature(BODY, None, SECRET)

    def test_rejects_unprefixed_header(self):
        raw = hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
        assert not verify_meta_signature(BODY, raw, SECRET)

    def test_rejects_tampered_body(self):
        # Signature computed over the original body must not validate a modified
        # one — this is the case that stops payload rewriting in transit.
        sig = _meta_sig(BODY, SECRET)
        assert not verify_meta_signature(BODY + b"tampered", sig, SECRET)

    def test_rejects_wrong_secret(self):
        assert not verify_meta_signature(BODY, _meta_sig(BODY, "other-secret"), SECRET)

    def test_passes_through_when_no_secret_configured(self):
        # Deliberate: a bot with no app secret stored cannot be verified, and
        # hard-failing would break every already-connected channel. Such requests
        # are bounded by the rate limiter and per-bot daily quota instead.
        assert verify_meta_signature(BODY, None, "")
        assert verify_meta_signature(BODY, None, None)


class TestSlackSignature:
    def test_accepts_genuine_signature(self):
        ts = str(int(time.time()))
        assert verify_slack_signature(BODY, _slack_sig(BODY, SECRET, ts), ts, SECRET)

    def test_rejects_forged_signature(self):
        ts = str(int(time.time()))
        assert not verify_slack_signature(BODY, "v0=deadbeef", ts, SECRET)

    def test_rejects_replayed_request(self):
        # A signature stays valid forever unless the timestamp is checked too, so
        # a captured request could otherwise be resent indefinitely.
        old = str(int(time.time()) - 600)
        assert not verify_slack_signature(BODY, _slack_sig(BODY, SECRET, old), old, SECRET)

    def test_accepts_within_replay_window(self):
        recent = str(int(time.time()) - 60)
        assert verify_slack_signature(BODY, _slack_sig(BODY, SECRET, recent), recent, SECRET)

    def test_rejects_missing_timestamp(self):
        ts = str(int(time.time()))
        assert not verify_slack_signature(BODY, _slack_sig(BODY, SECRET, ts), None, SECRET)

    def test_rejects_non_numeric_timestamp(self):
        assert not verify_slack_signature(BODY, "v0=abc", "not-a-number", SECRET)

    def test_rejects_tampered_body(self):
        ts = str(int(time.time()))
        sig = _slack_sig(BODY, SECRET, ts)
        assert not verify_slack_signature(BODY + b"x", sig, ts, SECRET)

    def test_passes_through_when_no_secret_configured(self):
        assert verify_slack_signature(BODY, None, None, "")
