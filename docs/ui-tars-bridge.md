# UI-TARS Sidecar Bridge (historical design)

The sidecar is not shipped in the current repository. The supported desktop and Web/API paths only fill forms and reject automatic submission. Do not use this historical design to automate final publication.

This sidecar service runs a local UI-TARS agent and exposes a simple HTTP API for GUI automation. It is intended to be called by the Python app (or any client) to perform browser-based publishing with safety confirmations.

## What it does

- Launches a local browser via UI-TARS `@ui-tars/operator-browser`.
- Runs tasks step-by-step using a plan.
- Default confirmation is step-level. Optional runtime confirmation can block actions before execution.

## Requirements

- Node.js >= 18
- A local Chromium-based browser (Chrome/Edge) installed

## Install

```bash
cd sidecar/ui-tars-bridge
npm install
```

Create `.env` based on `.env.example`:

```bash
cp .env.example .env
```

Set:

- `UI_TARS_BASE_URL`
- `UI_TARS_API_KEY`
- `UI_TARS_MODEL`

By default, the bridge loads the repo root `.env` first, then the sidecar `.env`.
Root values take priority (sidecar file only fills missing values).

## Run

```bash
npm run start
```

Default port: `8799` (override via `UI_TARS_BRIDGE_PORT` or `PORT`).

## API

### POST /v1/run

Starts a run (async). Returns a `run_id` immediately. Poll `/v1/run/:id` for status.

Request body (example):

```json
{
  "operator": "browser",
  "task": "Open the creator page and draft a post",
  "plan": ["Open creator page", "Fill title", "Fill body"],
  "action_spaces": [
    "click(start_box='[x1, y1, x2, y2]')",
    "type(content='')",
    "scroll(start_box='[x1, y1, x2, y2]', direction='down')",
    "wait()",
    "finished()",
    "call_user()"
  ],
  "system_prompt": "Never click final Publish or Submit. Stop after preparing a draft for the user.",
  "max_loop": 20,
  "require_confirm": ["publish", "submit", "login"],
  "runtime_intercept": false,
  "operator_config": {
    "browser_type": "chrome",
    "headless": false,
    "user_data_dir": "/path/to/profile",
    "viewport": { "width": 1280, "height": 800 },
    "initial_url": "https://creator.example.com"
  },
  "login": {
    "phone": "+86xxxxxxxxxxx",
    "login_url": "https://creator.xiaohongshu.com/login",
    "pause_after_send": true
  }
}
```

Notes:

- `runtime_intercept: true` enables runtime confirmation in addition to step-level confirmation.
- `confirm_mode` can override `runtime_intercept` with values: `step`, `runtime`, `both`, `none`.
- `action_spaces` is optional; if provided and `system_prompt` is not, the service injects them into a default system prompt.
- `login` is optional. When `login.phone` is provided, the bridge tries to auto-fill the phone and click "send code", then pauses for you to enter the SMS code.

### GET /v1/run/:id

Returns status and the latest agent outputs.

### POST /v1/run/:id/confirm

Approve or reject a pending confirmation.

```json
{ "decision": "approve" }
```

```json
{ "decision": "reject" }
```

### POST /v1/run/:id/abort

Abort a running task.

## Confirmation behavior

- **Step-level (default)**: if a step contains any `require_confirm` keyword, the run pauses before that step.
- **Runtime (optional)**: checks the model output and action payloads for `require_confirm` keywords and pauses before executing actions. This is best-effort and may not catch UI label changes.

## Limitations

- Operator support is currently `browser` only.
- Runtime confirmation is best-effort because UI-TARS actions are coordinate-based.
