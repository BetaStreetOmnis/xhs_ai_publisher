"""Shared publication states and duplicate-request identity."""
import hashlib
import json


class PublicationNeedsReview(RuntimeError):
    """Publication must stop until a person verifies the browser/platform."""


AUTO_PUBLICATION_DISABLED = "自动提交已停用。请核对草稿、图片、目标账号及 AI 声明后，在小红书页面手动发布。"
PUBLICATION_REVIEW_NOTICE = (
    "核实事实和亲身经历，确认图片、文字已获授权；使用 AI 生成或润色的内容，"
    "请按平台现行要求主动声明。人工确认和 AI 声明都不能保证内容通过审核。"
)


def require_manual_publication(auto_publish=False):
    """Reject legacy callers before they can create a browser or submit a post."""
    if auto_publish:
        raise PublicationNeedsReview(AUTO_PUBLICATION_DISABLED)


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
