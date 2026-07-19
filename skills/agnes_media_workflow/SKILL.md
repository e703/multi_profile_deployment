---
name: agnes-media-workflow
description: "Orchestrator-side workflow for dispatching media generation tasks (image, video, audio) via Kanban to pic/mov/tts profiles. Covers task structure, workspace config, reference image handling, and common pitfalls."
version: 1.4.0
author: Agnes
tags: [image-generation, video-generation, audio-generation, kanban, orchestration, agnes-api, workflow]
---

# Agnes Media Generation Workflow (Orchestrator)

## Dispatch: Two Modes

The orchestrator has **two dispatch paths**. **Kanban is the primary and only reliable path** for media generation tasks. `delegate_task` is a fallback.

### Mode A: Kanban (Primary — CLI via `hermes kanban create`)

There is no `kanban_create` tool. Use the **`hermes kanban create` CLI command**:

```bash
hermes kanban --board default create "文生图: 银灰色英短虎斑猫" \
  --body "project_name: 001_my_cat_project
prompt: A silver-gray British Shorthair Tabby cat, ...
file_name: cat_01.png" \
  --assignee pic \
  --workspace "dir:/home/alan/workspace/001_my_cat_project"
```

**Syntax gotchas:**
- `--board` is a **global** option of `hermes kanban`, put it BEFORE the subcommand
- `--title` does NOT exist — title is the positional arg after `create`
- `--workspace "dir:/path"` binds the worker to the project directory
- `--body` must contain: `project_name`, `prompt`, `file_name`

**Prerequisites:**
1. Orchestrator must have `kanban` toolset
2. Gateway must be running: `hermes gateway start`
3. Worker profiles must have `kanban` toolset
4. Kanban DB initialized: `hermes kanban init`

**Checking progress:**
```bash
hermes kanban show <task_id>
hermes kanban log <task_id>
hermes kanban runs <task_id>
```

**Kanban lifecycle:**
created (ready) → dispatcher picks up → claimed (running) → worker spawns → kanban_complete/block

### Mode B: delegate_task (AVOID for Media Tasks)

**Do NOT use `delegate_task` for pic/mov/tts media generation tasks.** The subagent spawned by `delegate_task` inherits the **orchestrator's toolset**, not the target profile's. It lacks the pic/mov/tts specialized plugins.

Consequences of using `delegate_task` for media generation:
- Falls back to free/low-quality APIs (Pollinations.ai, etc.)
- Image quality is poor — local features (M-mark, eye color, paw color) are unreliable
- Subagent frequently hits the 50-tool-call limit before completing the info file
- No kanban_show/complete/block capability

**Always use Kanban** (`hermes kanban create --assignee pic/mov/tts`) for media generation tasks. Only use `delegate_task` for:
- Research document analysis (where `research` profile isn't set up as Kanban worker)
- Quick code generation snippets (non-project work)
- Non-media tasks that don't need specialized plugins

**Key points (if forced to use delegate_task):**
- Subagent runs in background, notifies when done — do not poll
- Pass all context in `goal`; subagents have no conversation history
- **Always verify** file existence — subagent summaries are self-reported
- If user asks to switch to Kanban, do so immediately

## Architecture

### Kanban Path (Primary)
User → orchestrator creates project dir → `hermes kanban create` → gateway dispatcher → worker spawns → kanban_show() → generate_image/... → kanban_complete → orchestrator reports

## Task Body Structure

### Text-to-Image
```
project_name: <slug>
prompt: <detailed prompt, English preferred>
file_name: <name>.png
```

### Image-to-Image
```
project_name: <slug>
prompt: <description with "keep facial features 100% identical to reference">
file_name: <name>.png
mode: img2img
image: <public URL>
```

### Text-to-Video
```
project_name: <slug>
prompt: <detailed prompt>
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
```

### Image-to-Video / ti2vid
```
project_name: <slug>
prompt: <description with "keep facial features 100% identical">
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
mode: ti2vid
image: <public URL>
```

### Keyframe Animation
```
project_name: <slug>
prompt: <description of transitions>
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
mode: keyframes
image: ["<url1>", "<url2>", "<url3>"]
```

### TTS
```
project_name: <slug>
text: <text to synthesize>
file_name: <name>.mp3
speed_ratio: 0.85    # optional: 0.1~2.0, default 1.0. Lower = slower
```

## Workspace Path Configuration

**CRITICAL:** `workspace_root` must be absolute path, not `~/workspace`. The `~` in Kanban workers resolves to profile's virtual home, not the real user home.

```yaml
plugins:
  entries:
    agnes_router_pic:
      workspace_root: /home/alan/workspace
```

### Reference Image Handling

### Mode A: Local path (preferred — same machine)
When orchestrator and worker are on the **same machine** (both portal and worker profile share the same filesystem), **use the local absolute path directly**. No upload needed.

```bash
# 1. Copy reference to project sources
cp /path/to/reference.png /home/alan/workspace/<project>/sources/images/
# 2. Use absolute path in task body
image: /home/alan/workspace/<project>/sources/images/reference.png
```

This works because Kanban workers are spawned on the same machine and can access the same paths.

### Mode B: Public URL (for cross-machine / remote workers)
```bash
curl -s -F "file=@/path/to/image.png" https://tmpfiles.org/api/v1/upload
```

### AVOID: Data URIs > ~1MB
They cause the agent to hang. Use public URLs or local paths.

### Best Practice
1. Copy to `<project>/sources/images/`
2. Same machine → use absolute path
3. Remote worker → upload to tmpfiles.org
4. Include path/URL in task body as `image: <path or url>`
5. Add `DO_NOT_GENERATE_DATA_URI` instruction if needed

## Post-Generation: Info File

Worker saves `generation_info.md` / `<file>_info.json` to `target/others/`.

## Post-Completion: Verification

After Kanban task done, verify:
1. `ls <project>/target/images/<file_name>` — file exists
2. Check `target/others/` for info file
3. Display image to user via MEDIA: path
4. Kanban task should show status: done with artifacts list

## Common Pitfalls

1. **No kanban_create tool** — Use CLI: `hermes kanban --board default create ...`
2. **Gateway must be running** — Tasks sit in `ready` forever without it
3. **503 Queue Full** — Image API retries 10x with 30s delays. Normal.
4. **Video Gen Async** — Task stays "running" until video ready
5. **Project Name Rules** — ASCII only, no Chinese, no slashes
6. **File Name Rules** — ASCII only, no directory components
7. **Resolution Auto-Mapping** — 1152×768 → nearest preset
8. **Stale Kanban Claims** — `hermes kanban reclaim <id>` then `dispatch --max 1`
9. **Data URI Overflow** — >1MB hangs the agent. Use public URLs.
10. **delegate_task for media** — NEVER use. Always Kanban.
12. **Kanban CLI Syntax** — `--board` before subcommand, title is positional after `create`
13. **TTS Config Format** — tts profile's config.yaml MUST use the same structure as other profiles: `provider` at top level with `custom_providers` list. Do NOT nest `provider`/`base_url`/`api_key` under `model:`. Wrong format causes "Unknown provider 'custom:api.bjlab.tk'" error on worker spawn.
14. **Worker config changes** — Workers are spawned fresh per task, so config changes take effect immediately without gateway restart. Gateway config changes (max_in_progress) need gateway restart.

## Deployment Verification Checklist

Compare repo vs deployed:
1. Read README (source of truth — not plan docs)
2. Compare configs/*_config.yaml vs ~/.hermes/profiles/*/config.yaml
3. Check kanban toolset on pic, mov, tts
4. Check workspace_root is absolute path
5. Compare SOULs
6. Compare gitconfigs
7. Check plugins exist
8. Check Kanban config (max_in_progress, orchestrator_profile)
9. Check .env files exist for all 8 profiles
10. Git commit: `git add -A && git commit -m "fix: ..."`
11. Verify profile descriptions match README

## Reference Files

- `references/session-examples.md` — Task creation commands, project structure, API responses
- `references/deployment-verification.md` — Scripted comparison procedure with common discrepancies and fix commands