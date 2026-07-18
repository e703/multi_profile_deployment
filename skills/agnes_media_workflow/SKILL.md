---
name: agnes-media-workflow
description: "Orchestrator-side workflow for dispatching media generation tasks (image, video, audio) via Kanban to pic/mov/tts profiles using the Agnes API. Covers task structure, workspace config, reference image handling, and common pitfalls."
version: 1.0.0
author: Agnes
tags: [image-generation, video-generation, audio-generation, kanban, orchestration, agnes-api, workflow]
---

# Agnes Media Generation Workflow (Orchestrator)

## When to Use

This skill governs how the orchestrator (portal profile) dispatches media generation tasks. It does NOT replace the pic/mov/ttz profile's own skills — those handle the actual API calls. This skill is for the **task creation and dispatch** phase.

## Architecture

```
User request
  → orchestrator (portal) creates Kanban task
  → dispatcher spawns pic/mov/tts profile worker
  → worker reads task body, calls generate_image_via_pic01 / generate_video_via_mov01
  → tool calls Agnes API (agnes-image-2.0-flash / agnes-video-v2.0)
  → worker saves output, writes info file, completes Kanban task
```

## Task Body Structure

### Text-to-Image (文生图)

```
project_name: <slug>
prompt: <detailed prompt, English preferred for API>
file_name: <name>.png
```

### Image-to-Image (图生图)

```
project_name: <slug>
prompt: <description including "keep facial features, fur pattern 100% identical to reference">
file_name: <name>.png
mode: img2img
image: <public URL or data URI>
```

### Multi-Image Composition (多图合成)

Same as img2img with `image` parameter.

### Text-to-Video (文生视频)

```
project_name: <slug>
prompt: <detailed prompt>
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
```

### Image-to-Video / ti2vid (图生视频)

```
project_name: <slug>
prompt: <description including "keep facial features 100% identical to reference">
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
mode: ti2vid
image: <public URL of reference image>
```

### Keyframe Animation (关键帧动画)

```
project_name: <slug>
prompt: <description of transitions between keyframes>
file_name: <name>.mp4
width: 1152
height: 768
num_frames: 121
frame_rate: 24
mode: keyframes
image: ["<url1>", "<url2>", "<url3>"]
```

### TTS / Text-to-Speech (文字转语音)

```
project_name: <slug>
text: <text to synthesize, Chinese supported natively>
file_name: <name>.mp3
```

**Long text handling:** Volcengine API has a per-request payload limit. Text over ~1024 bytes should be passed as-is — the tts agent handles segmentation internally.

**Kanban toolset required:** The tts profile MUST have the `kanban` toolset enabled in its config.yaml, otherwise the agent cannot call `kanban_complete` / `kanban_block` and falls back to direct DB writes:
```yaml
enabled_toolsets:
  - kanban    # required for kanban_show/complete/block
  # ... other toolsets
```

## Workspace Path Configuration

**CRITICAL:** The `workspace_root` in pic/mov profile config must be an **absolute path**, not `~/workspace`. The `~` expansion in Kanban worker environments resolves to the profile's virtual home, not the real user home.

Fix in `config.yaml`:
```yaml
plugins:
  entries:
    agnes_router_pic:
      workspace_root: /home/alan/workspace   # absolute path, not ~/workspace
```

Also set in `.env`:
```
AGNES_WORKSPACE_ROOT=/home/alan/workspace
```

## Reference Image Handling

### DO: Use public URLs
Upload reference images to a temporary hosting service and pass the URL directly.

```bash
# Upload to tmpfiles.org
curl -s -F "file=@/path/to/image.png" https://tmpfiles.org/api/v1/upload
```

### AVOID: Data URIs for large images
Data URIs > ~1MB (e.g. 1.4MB PNG → 1.9MB base64) are too large for tool parameters and cause the agent to hang. Use public URLs instead.

### Best Practice
1. Copy reference image to `<project>/sources/images/`
2. Upload to tmpfiles.org for a public URL
3. Include the URL in the Kanban task body as `image: <url>`
4. If the agent still tries to generate a data URI (causing a hang), add `DO_NOT_GENERATE_DATA_URI: The image URL is already publicly accessible. Do NOT convert it to a data URI.` to the task body — this overrides the agent's default behaviour.

## Post-Generation: Info File

After each generation, the worker automatically saves `generation_info.md` / `<file>_info.json` to `target/others/`. This is enforced by the `generation-info-report` skill and the mov profile's SOUL.

## Common Pitfalls

1. **503 Queue Full (Image Gen)** — The Agnes image API returns 503 under load. The tool retries up to 10 times with 30s delays. This is normal. Do NOT submit concurrent image requests.

2. **Video Gen is Async** — The ti2vid and keyframe APIs return immediately. The mov agent starts a background polling script (30s interval). The Kanban task stays "running" until the video is ready.

3. **Project Name Rules** — Must be ASCII only, no slashes, no path traversal, no Chinese characters. Examples: `001_my_cat_project`, `006_dog_pounce_project`.

4. **File Name Rules** — ASCII only, no directory components. The tool auto-appends `.png` / `.mp4` if missing.

5. **Resolution Auto-Mapping** — Requested resolution (e.g. 1152×768) is auto-mapped to the nearest standard preset (720p 4:3 → 1088×832). This is expected behavior.

6. **Stale Kanban Claims** — After session interruption, the old claim lock persists. Run `hermes kanban reclaim <task_id>` then `hermes kanban dispatch --max 1` to resume.

7. **tts Profile Needs kanban Toolset** — The tts profile's config.yaml must include `kanban` in `enabled_toolsets`, otherwise the agent cannot call `kanban_show`, `kanban_complete`, or `kanban_block` and falls back to fragile direct DB writes. Fix: add `- kanban` to the profile's `enabled_toolsets` list.

8. **Data URI Overflow for mov Profile** — When passing reference images for ti2vid or keyframe modes, data URIs > ~1MB cause the `generate_video_via_mov01` tool parameter to overflow, hanging the agent during `preparing generate_video_via_mov01…`. Always use a publicly accessible URL instead. If stuck, block the task and recreate with a URL + `DO_NOT_GENERATE_DATA_URI` instruction.

## Reference Files

- `references/session-examples.md` — Complete task creation commands, project directory structure, API response formats, file size benchmarks, and TTS example from the 2026-07-18 session.