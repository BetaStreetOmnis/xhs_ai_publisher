# Use Codex to operate Xiaohongshu from your phone

[中文](codex-mobile.zh.md)

Run Codex and Xiaohongshu AI Publisher on the same Mac. Office Town sends instructions from your phone to the original Codex session. Codex calls the local tool and reports back in that session. The phone does not need direct access to the Xiaohongshu service.

This guide describes a setup using existing sessions and HTTP endpoints. The complete phone-to-publication workflow has not been verified on a physical device. Employee chat has no dedicated Xiaohongshu draft or image preview screen.

## Prepare your Mac

Follow this project's README to install the tool and sign in. Open a dedicated Codex session for Xiaohongshu work. Note the absolute project path, Python environment and service URL.

For a native Web service, run this from the project root in an environment with the Web dependencies installed:

```bash
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
```

Use a loopback address for local calls. The service's login status refers to the Xiaohongshu account; it does not authenticate remote API callers.

Check from the environment where Codex runs:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/healthz
curl --fail --silent --show-error http://127.0.0.1:8000/api/auth/status
```

A healthy service does not mean the account is signed in. Complete login or any verification challenge on the Mac. Keep both the Mac and the service running.

## Instructions for Codex

Send this to the dedicated session, replacing the path and URL:

```text
Use the local Xiaohongshu AI Publisher.
Project path: <absolute project path>
Service URL: http://127.0.0.1:8000

Check service reachability and Xiaohongshu login status first. Report failures.
Write content from my instructions. Save drafts with POST /api/content.
Read a draft with GET /api/content/{content_id}; list drafts with GET /api/content.
Return the draft ID, title, full text, tags and image paths for review on my phone.
After editing, save a new draft and identify which draft it replaces. Wait for my review.

Generation, editing and follow-up requests only create drafts by default.
Call POST /api/publish with auto_publish=true only after I explicitly identify a draft ID and ask you to publish it.
If publication times out or the result is uncertain, check status and the browser before retrying.
An accepted publication request is not a completed post. Query the content and report its actual status.
Never include passwords, cookies, verification codes or model keys in the conversation.
```

The existing `POST /api/content` accepts text that has already been written. It does not generate an article through a model. There is no HTTP content-editing endpoint, so these instructions save revisions as new drafts.

Draft request body:

```json
{
  "title": "Example title",
  "content": "The completed body text",
  "tags": ["Office Town"],
  "images": []
}
```

Send it to `POST /api/content` and read the draft ID from `data.id`. Image paths must be accessible in the tool's execution environment. A Docker service needs container paths, rather than Mac paths. Prepare valid images before requesting publication.

## Continue from your phone

Connect Office Town to the Mac and import that Codex session. Start with:

> Check whether the Xiaohongshu service is reachable. Report the result without creating content or publishing.

Refresh employee output and confirm the reply came from that session. Then try:

> Write an introduction to Office Town in a natural voice. Save a draft and return its ID and full text. Do not publish yet.

To revise:

> Shorten the opening and keep the point about continuing tasks away from my computer. Save a new draft and return its ID and text.

The existing conversation can return text and paths. A local Mac image path is not a phone-accessible image link. Review the images separately for now, and confirm the title, text, cover and target account before requesting publication.

## Check the result

`POST /api/publish` with `auto_publish=false` fills the browser form and leaves confirmation to the computer browser. It does not provide phone-side publication approval. Explicitly authorized automatic publication uses `auto_publish=true`.

After the request is accepted, query the content status. The implementation records `publishing`, `published` or `failed`. Verify the tool output and the actual post as well. Investigate uncertain results before retrying to avoid duplicate posts.

Ordinary butler chat currently has task-query tools only. Codex performs the operations in this workflow. Phone supervision follows up by messaging the original session. Start with manual instructions and publication confirmation, keeping publishing outside broad automatic follow-up goals.
