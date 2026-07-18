# Hermes 多 Profile 部署包

## 概述

本目录包含 Hermes Agent 多 Profile 部署的全部配置文件和部署文档，
用于在单台 Linux 服务器上部署 8 个 Hermes profile，实现单用户多角色协作环境。

## 目录结构

```
multi_profile_deployment/
├── README.md                              # 本文件
├── multi_profile_deployment_plan.md       # 完整部署规划文档
│
├── plugins/
│   ├── agnes_router_pic/                  # pic profile 专用插件（仅图像生成）
│   │   ├── __init__.py                    # 注册 generate_image_via_pic01
│   │   ├── plugin.yaml                    # 插件清单
│   │   ├── schemas.py                     # 工具参数 Schema
│   │   ├── tools.py                       # 核心逻辑（API 调用、重试）
│   │   └── workspace_manager.py           # 路径验证 + 安全隔离
│   │
│   └── agnes_router_mov/                  # mov profile 专用插件（仅视频生成）
│       ├── __init__.py                    # 注册 generate_video_via_mov01
│       ├── plugin.yaml                    # 插件清单
│       ├── schemas.py                     # 工具参数 Schema
│       ├── tools.py                       # 核心逻辑（API 调用、重试）
│       └── workspace_manager.py           # 路径验证 + 安全隔离
│
├── skills/
│   ├── agnes_media_pic/                   # pic 主技能（图像生成文档）
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── check_task.py              # 视频任务状态查询
│   │   │   └── to_data_uri.py             # 文件 → Data URI 转换
│   │   ├── references/                    # API 参考文档
│   │   └── templates/                     # 重试脚本模板
│   │
│   ├── agnes_media_mov/                   # mov 主技能（视频生成文档）
│   │   └── ...（同上结构）
│   │
│   ├── agnes_video_async_monitor/         # 异步视频轮询技能
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── monitor_video.py           # 通用视频监控（30s轮询）
│   │   │   └── monitor_keyframe.py        # 关键帧专用监控
│   │   └── references/
│   │
│   ├── agnes_media_workflow/              # 自动生成：编排工作流技能
│   │   └── SKILL.md
│   │
│   ├── generation_info_report/            # 自动生成：生成结果信息报告规范
│   │   └── SKILL.md
│   │
│   └── volcengine_tts/                    # TTS 技能（占位，需自行创建 SKILL.md）
│
├── configs/                              # 各 profile 的 config.yaml 模板
├── souls/                                # 各 profile 的人格设定
├── gitconfigs/                           # 各 profile 的 git 提交身份
```

## 8 个 Profile 一览

| Profile | 用途 | LLM 模型 | 媒体工具 | 网关 |
|---------|------|----------|---------|------|
| portal | 日常对话、信息检索、任务编排 | deepseek-v4-flash | 无 | 飞书 |
| coding | 编程、代码生成 | glm-5.2 | 无 | 无 |
| research | 研究、深度推理 | deepseek-v4-pro | 无 | 无 |
| personal | 计划任务、portal 交付的额外任务 | deepseek-v4-flash | 无 | 无 |
| writing | 文档编写 | deepseek-v4-flash | 无 | 无 |
| pic | 图像生成（文生图/图生图/多图合成） | deepseek-v4-flash | generate_image_via_pic01 | 无 |
| mov | 视频生成（文生视频/图生视频/关键帧动画） | deepseek-v4-flash | generate_video_via_mov01 | 无 |
| tts | 文字转语音（TTS） | deepseek-v4-flash | volcengine TTS | 无 |

## 环境变量与密钥配置

### 变量表

| 变量名 | 用途 | 配置位置 | 说明 |
|--------|------|---------|------|
| `bjlab_API_KEY` | 主 LLM 提供商 API Key | 各 profile 的 config.yaml 中 custom_providers | api.bjlab.tk 的密钥 |
| `chat_API_KEY` | Agnes 聊天 API Key（fallback 后备模型） | 各 profile 的 .env 中 `AGNES_CHAT_API_KEY` | 用于后备模型 agnes-2.0-flash |
| `pic_API_KEY` | Agnes 图像生成 API Key | pic profile 的 .env 中 `AGNES_API_KEY` | 用于 pic 的媒体工具 |
| `mov_API_KEY` | Agnes 视频生成 API Key | mov profile 的 .env 中 `AGNES_API_KEY` | 用于 mov 的媒体工具 |
| `Feishu_APP_ID` | 飞书应用 ID | portal profile 的 .env 中 `FEISHU_APP_ID` | 飞书开放平台获取 |
| `Feishu_APP_SECRET` | 飞书应用密钥 | portal profile 的 .env 中 `FEISHU_APP_SECRET` | 飞书开放平台获取 |
| `VOLC_TTS_API_KEY` | 火山引擎 TTS API Key | tts profile 的 .env 中 `VOLC_TTS_API_KEY` | 火山引擎控制台获取 |
| `VOLC_TTS_VOICE_ID` | 克隆音色 ID | tts profile 的 .env 中 `VOLC_TTS_VOICE_ID` | 已克隆的音色 ID |

### 变量映射关系

部署时，上述变量名需映射到对应 profile 的 .env 中的实际环境变量名：

| 本包中的变量名 | .env 中的实际变量名 | 生效 profile |
|----------------|-------------------|-------------|
| `bjlab_API_KEY` | 写入 config.yaml 的 custom_providers.api_key | portal, coding, research, personal, writing, pic, mov, tts |
| `chat_API_KEY` | `AGNES_CHAT_API_KEY` | 全 profile（启用 fallback 时） |
| `pic_API_KEY` | `AGNES_API_KEY` | pic |
| `mov_API_KEY` | `AGNES_API_KEY` | mov |
| `Feishu_APP_ID` | `FEISHU_APP_ID` | portal |
| `Feishu_APP_SECRET` | `FEISHU_APP_SECRET` | portal |
| `VOLC_TTS_API_KEY` | `VOLC_TTS_API_KEY` | tts |
| `VOLC_TTS_VOICE_ID` | `VOLC_TTS_VOICE_ID` | tts |

### 注意

- **pic 和 mov 一旦启用 fallback，其 .env 中必须同时包含 `AGNES_API_KEY` 和 `AGNES_CHAT_API_KEY`**，即使两者使用同一密钥也必须分别声明，缺一不可
- `bjlab_API_KEY` 不写入 .env，而是写入各 profile 的 config.yaml 中 custom_providers 段
- 环境变量名严格区分大小写，请保持原样

## 前置条件

### 系统依赖

```bash
# Python 文档处理库（用于 research/writing profile）
pip install python-docx python-pptx PyMuPDF openpyxl python-magic

# 创建 2GB swap（可选，推荐）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 创建工作目录
mkdir -p ~/workspace
```

## 快速部署步骤

### 1. 创建 Profile

```bash
hermes profile create portal --clone
hermes profile create coding --clone
hermes profile create research --clone
hermes profile create personal --clone
hermes profile create writing --clone
hermes profile create pic --clone
hermes profile create mov --clone
hermes profile create tts --clone
```

### 2. 复制配置文件

将本目录下的 `*_config.yaml` 覆盖到对应 profile 的 config.yaml，
将 `*_SOUL.md` 覆盖到对应 profile 的 SOUL.md，
将 `*_gitconfig` 覆盖到对应 profile 的 home/.gitconfig。

### 3. 配置 .env

每个 profile 的 .env 中写入对应的环境变量（见上方变量映射表）。

### 4. 安装插件和技能

```bash
# pic 插件
cp -r plugins/agnes_router_pic ~/.hermes/profiles/pic/plugins/

# mov 插件
cp -r plugins/agnes_router_mov ~/.hermes/profiles/mov/plugins/

# pic 技能
mkdir -p ~/.hermes/profiles/pic/skills/creative/
cp -r skills/agnes_media_pic/. ~/.hermes/profiles/pic/skills/creative/agnes_media_pic/

# mov 技能
mkdir -p ~/.hermes/profiles/mov/skills/creative/
mkdir -p ~/.hermes/profiles/mov/skills/media/
cp -r skills/agnes_media_mov/. ~/.hermes/profiles/mov/skills/creative/agnes_media_mov/
cp -r skills/agnes_video_async_monitor/. ~/.hermes/profiles/mov/skills/media/agnes_video_async_monitor/
```

### 5. 配置 Kanban 看板

```bash
hermes kanban init
# 在 default profile 的 config.yaml 中添加以下配置：
kanban:
  dispatch_in_gateway: true
  dispatch_interval_seconds: 60
  auto_decompose: false
  orchestrator_profile: portal
  default_assignee: personal
  max_in_progress: 3
  max_in_progress_per_profile: 1
  failure_limit: 2
  dispatch_stale_timeout_seconds: 7200
```

### 6. 设置 profile 描述

```bash
hermes profile describe portal --text "日常对话交互、信息检索、任务调度编排"
hermes profile describe coding --text "编程和代码生成任务"
hermes profile describe research --text "研究和深度推理任务"
hermes profile describe personal --text "计划任务及日常杂项任务"
hermes profile describe writing --text "文档编写任务"
hermes profile describe pic --text "图像生成、文生图、图生图、多图合成"
hermes profile describe mov --text "视频生成、动画、多媒体生成"
hermes profile describe tts --text "使用豆包语音克隆音色API实现文字转语音（TTS）功能"
```

### 7. 启动网关

```bash
# 仅为 portal profile 启用飞书网关
hermes -p portal gateway install
hermes -p portal gateway start
sudo loginctl enable-linger alan
```

## 注意事项

- **home_mode: profile**：子进程 HOME 指向 profile 内目录，所有路径中的 `~` 需要用 `$HERMES_REAL_HOME` 替代
- **插件拆分**：pic 和 mov 的插件已从原始 agnes_router 拆分，更新时注意不要全量覆盖 __init__.py 和 plugin.yaml
- **两阶段编排**：涉及素材分析的任务，portal 先创建 research 任务，research 完成后 portal 再创建下游任务
- **大文件**：超过 20MB 的文件不通过飞书传输，源文件保存在 workspace 中
- **视频异步**：视频生成是异步的，使用 monitor_video.py 后台轮询（30s 间隔），不能使用 cron（最小间隔 30m）

## 文件说明

| 文件 | 说明 |
|------|------|
| multi_profile_deployment_plan.md | 完整部署规划文档，含所有行为规范和交互逻辑 |
| plugins/agnes_router_pic/* | 已拆分的 pic 插件（仅图像生成），直接可用 |
| plugins/agnes_router_mov/* | 已拆分的 mov 插件（仅视频生成），直接可用 |
| skills/agnes_media_pic/* | 图像技能文档，安装到 pic 的 skills/creative/ |
| skills/agnes_media_mov/* | 视频技能文档，安装到 mov 的 skills/creative/ |
| skills/agnes_video_async_monitor/* | 视频异步轮询技能，安装到 mov 的 skills/media/ |
| skills/agnes_media_workflow/* | 自动生成：编排工作流技能（portal 用） |
| skills/generation_info_report/* | 自动生成：生成结果信息报告规范 |
| skills/volcengine_tts/ | TTS 技能占位，需自行创建 SKILL.md |
| *_config.yaml | 各 profile 的完整配置模板（含 fallback 和 home_mode 配置） |
| *_SOUL.md | 各 profile 的人格设定 |
| *_gitconfig | 各 profile 的 git 提交身份 |