"""Shared publication states and duplicate-request identity."""
import hashlib
import json


class PublicationNeedsReview(RuntimeError):
    """Publication must stop until a person verifies the browser/platform."""


BLOCKED_PUBLICATION_STATES = frozenset({
    "queued", "publishing", "submitted", "under_review", "published",
    "unknown", "needs_review",
})


def publication_fingerprint(title, content, images):
    payload = {
        "title": str(title or "").strip(),
        "content": str(content or "").strip().replace("\r\n", "\n"),
        "images": [str(path) for path in (images or [])],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
