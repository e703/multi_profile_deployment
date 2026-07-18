---
name: generation-info-report
description: "每次生图、生视频、生音频任务完成后，必须在 target/others/ 下保存详细的生成说明文件（Markdown/JSON），包含中英文提示词、参数配置、结果说明和原始下载链接说明。"
version: 1.1.0
author: Agnes
tags: [image-generation, video-generation, audio-generation, tts, logging, report, SOP]
related_skills: [agnes-media-workflow]
---

# 生成结果信息报告规范

## 适用范围

每次通过下级 profile（pic / mov / tts）完成生图、生视频、生音频任务后，**必须**在项目目录的 `target/others/` 下保存一份详细的说明文件。

## 文件规范

- **文件名**: `generation_info.md`（pic 用）或 `<file_name>_info.json`（mov 用）
- **存放路径**: `<workspace_root>/<project_name>/target/others/`
- **格式**: Markdown 或 JSON
- **语言**: 中文（英文部分仅用于提示词对照）
- **不上传到飞书/任何聊天平台**，仅保留在服务器本地

## 文件内容结构

### 1. 项目名称
项目目录名，如 `001_my_cat_project`、`002_my_cat_project`。

### 2. 最终生成的提示词（中英文对照）
- **中文在上，英文在下**
- 如果是图生图/图生视频，需注明参考图来源
- 如有多个输出（如一次生成多张图），每个输出分别列出提示词

### 3. 完成的结果参数配置
| 参数 | 说明 |
|------|------|
| 图片/视频/音频 | 分辨率/时长/采样率等 |
| 宽高比/尺寸 | 如 1:1、16:9 |
| 模型 | 使用的模型名称（如 agnes-image-2.0-flash） |
| API 端点 | 调用的 API URL |
| 生成方式 | 文生图/图生图/文生视频/图生视频/TTS 等 |
| 调度方式 | Kanban 看板 → profile名 → 工具名 |

### 4. 生成后的结果说明
- 输出文件名
- 文件大小（MB）
- 文件格式（PNG/MP4/WAV 等）
- 保存路径（绝对路径）
- 生成耗时
- 状态（成功/失败）

### 5. 原始下载链接
> ⚠️ **说明**: 原始下载链接为临时签名 URL，生成后立即用于下载内容，链接已过期，无法保证长期有效。内容已保存至本地服务器路径，可直接从服务器获取。

| 文件名 | 原始远程地址 | 状态 |
|--------|-------------|------|
| 文件名 | 临时 URL（已过期） | 🔗 已失效 |

## 执行流程

1. 任务通过 Kanban 看板 → 下级 profile 执行
2. 下级 profile 调用对应工具生成内容
3. 工具返回结果（包含本地路径、remote_url 等信息）
4. **在标记 kanban_complete 之前**，收集所有信息，写入 `target/others/generation_info.md`（pic 用）或 `target/others/<file_name>_info.json`（mov/tts 用）
5. 文件不上传到飞书，仅保留在服务器本地

## 注意事项

### mov 和 tts profile：信息文件已内建
mov 和 tts 的 SOUL.md 已经**强制要求**在生成完成后保存信息文件到 `target/others/`。因此 orchestrator 不需要在 Kanban 任务体中额外要求——这些 profile 会自动执行。

### tts profile 需启用 kanban 工具集
如果 tts profile 的 `disabled_toolsets` 中包含了 `kanban`，agent 无法调用 `kanban_complete`/`kanban_block`，会退化为直接写数据库的脆弱方式。**必须先检查并移除该配置：**

```yaml
# tts config.yaml — 确保 kanban 不在 disabled_toolsets 中
disabled_toolsets:
  # ... 其他工具集
  # - kanban  ← 必须移除或不存在此行
```

## 各 profile 的特殊说明

### pic（图像生成）
- 记录：分辨率、宽高比、模型、参考图路径
- 文件后缀：`.png` / `.jpg` / `.webp`
- **图生图参考图**：优先使用公网 URL（如 tmpfiles.org 上传），避免 data URI。1.5MB+ 的 PNG 图片转 data URI 后约 2M 字符，会导致工具入参溢出，agent 卡住。如果必须用 data URI，确保图片 < 500KB。需在信息文件中注明参考图路径和 data URI 文件路径。

### mov（视频生成）
- 记录：分辨率、帧数、帧率、时长、宽高比、模型
- 文件后缀：`.mp4` / `.webm`

### tts（语音合成）
- 记录：采样率、声道数、语速、模型
- 文件后缀：`.mp3` / `.wav` / `.ogg`

## 示例

参见 `001_my_cat_project/target/others/generation_info.md` 和 `002_my_cat_project/target/others/generation_info.md`。