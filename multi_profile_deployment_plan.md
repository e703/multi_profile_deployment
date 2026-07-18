# Hermes 多 Profile 部署规划

## 1. 概述

在单台 Linux 服务器上部署 8 个 Hermes profile，实现单用户多角色协作环境。
每个 profile 拥有独立的模型、人格设定（SOUL.md）、记忆、API 凭据和工作空间，
通过 Kanban 看板进行跨 profile 任务协作，通过 Cron 定时任务实现自动化，
portal profile 接入飞书平台作为对外交互入口。

## 2. 环境现状

| 项目 | 值 |
|------|-----|
| 主机 | Linux hermes-hk01, x86_64, 7.0.0-1007-gcp |
| 内存 | 3.8 GB（可用 3.1 GB） |
| 磁盘 | 19 GB（可用 12 GB） |
| Swap | 无（建议创建 2GB swap） |
| Hermes 版本 | v0.18.2 (2026.7.7.2) |
| 安装方式 | git，位于 /home/alan/.hermes/hermes-agent |
| 当前 profile | 仅 default |
| 主模型提供商 | api.bjlab.tk（OpenAI 兼容，用于 portal/coding/research/personal/writing） |
| 媒体模型提供商 | apihub.agnes-ai.com（用于 pic/mov，独立 API key） |
| 当前模型 | glm-5.2 |
| Gateway 状态 | 未运行 |

## 3. Profile 清单与配置

### 3.1 总表

| # | Profile | 用途 | LLM 模型 | 媒体工具 | 网关 | 工作目录 |
|---|---------|------|----------|---------|------|---------|
| 1 | portal | 日常对话、信息检索、任务编排 | deepseek-v4-flash | 无 | 飞书 | ~/workspace |
| 2 | coding | 编程、代码生成 | glm-5.2 | 无 | 无 | ~/workspace |
| 3 | research | 研究、深度推理 | deepseek-v4-pro | 无 | 无 | ~/workspace |
| 4 | personal | 计划任务、portal 交付的额外任务 | deepseek-v4-flash | 无 | 无 | ~/workspace |
| 5 | writing | 文档编写 | deepseek-v4-flash | 无 | 无 | ~/workspace |
| 6 | pic | 图像生成（文生图/图生图/多图合成） | deepseek-v4-flash | generate_image_via_pic01 | 无 | ~/workspace |
| 7 | mov | 视频生成（文生视频/图生视频/关键帧动画） | deepseek-v4-flash | generate_video_via_mov01 | 无 | ~/workspace |
| 8 | tts | 文字转语音（TTS） | 豆包语音克隆音色 | 自定义插件（待开发） | 无 | ~/workspace |

### 3.2 API 提供商与密钥分配

| 提供商 | 用途 | 生效 profile | 环境变量 |
|--------|------|-------------|----------|
| api.bjlab.tk | 主 LLM 提供商 | portal, coding, research, personal, writing | config.yaml 中 custom_providers 配置 |
| apihub.agnes-ai.com | Agnes 媒体生成 API | pic, mov | AGNES_API_KEY（pic 和 mov 各自独立） |
| apihub.agnes-ai.com | Agnes 聊天 API（fallback） | 全 profile | AGNES_CHAT_API_KEY 或 AGNES_API_KEY |
| 飞书 | 消息平台 | portal | FEISHU_APP_ID, FEISHU_APP_SECRET |

**关键说明：**
- 每个 profile 的 .env 中只放该 profile 需要的 API key
- pic 和 mov 使用不同的 AGNES_API_KEY（各自在各自的 .env 中配置）
- api.bjlab.tk 的密钥通过 config.yaml 的 custom_providers 配置，在需要该提供商模型的 profile 的 config.yaml 中写入
- agnes-2.0-flash 作为后备模型（fallback model），在 api.bjlab.tk 不可用时自动切换
- agnes-2.0-flash 的聊天 API 端点（https://apihub.agnes-ai.com/v1/chat/completions）与图像/视频 API 使用同一域名但不同路径，可能需要独立的 API key

### 3.3 各 Profile 模型与提供商配置

#### portal / research / personal / writing

```yaml
# 这些 profile 共用 api.bjlab.tk 作为主提供商
model:
  default: deepseek-v4-flash       # portal/personal/writing 用
  # default: deepseek-v4-pro        # research 用
provider: custom:api.bjlab.tk
custom_providers:
  - name: api.bjlab.tk
    base_url: https://api.bjlab.tk/v1
    api_key: sk-...                 # 共用密钥
    api_mode: chat_completions

# 后备模型：当主提供商不可用时自动切换
fallback_model:
  provider: custom
  model: agnes-2.0-flash
  base_url: https://apihub.agnes-ai.com/v1
  key_env: AGNES_CHAT_API_KEY
```

#### coding

```yaml
model:
  default: glm-5.2
provider: custom:api.bjlab.tk
custom_providers:
  - name: api.bjlab.tk
    base_url: https://api.bjlab.tk/v1
    api_key: sk-...
    api_mode: chat_completions

fallback_model:
  provider: custom
  model: agnes-2.0-flash
  base_url: https://apihub.agnes-ai.com/v1
  key_env: AGNES_CHAT_API_KEY
```

#### pic

```yaml
# pic profile 的 LLM 通过 api.bjlab.tk 调用 deepseek-v4-flash
# 同时通过 agnes_router_pic 插件调用 Agnes 图像生成 API
model:
  default: deepseek-v4-flash
provider: custom:api.bjlab.tk
custom_providers:
  - name: api.bjlab.tk
    base_url: https://api.bjlab.tk/v1
    api_key: sk-...                 # 与 portal 共用 bjlab 密钥
    api_mode: chat_completions

fallback_model:
  provider: custom
  model: agnes-2.0-flash
  base_url: https://apihub.agnes-ai.com/v1
  key_env: AGNES_CHAT_API_KEY

plugins:
  enabled:
    - agnes_router_pic              # 仅图像生成工具
  entries:
    agnes_router_pic:
      workspace_root: ~/workspace
      image_endpoint: https://apihub.agnes-ai.com/v1/images/generations
      image_model: agnes-image-2.0-flash
      image_timeout: 180
      download_timeout: 300
      max_retries: 10
      retry_delay: 30.0
```

#### mov

```yaml
model:
  default: deepseek-v4-flash
provider: custom:api.bjlab.tk
custom_providers:
  - name: api.bjlab.tk
    base_url: https://api.bjlab.tk/v1
    api_key: sk-...
    api_mode: chat_completions

fallback_model:
  provider: custom
  model: agnes-2.0-flash
  base_url: https://apihub.agnes-ai.com/v1
  key_env: AGNES_CHAT_API_KEY

plugins:
  enabled:
    - agnes_router_mov              # 仅视频生成工具
  entries:
    agnes_router_mov:
      workspace_root: ~/workspace
      video_endpoint: https://apihub.agnes-ai.com/v1/videos
      video_model: agnes-video-v2.0
      video_timeout: 300
      download_timeout: 300
      max_retries: 2
      retry_delay: 3.0
```

### 3.4 各 Profile SOUL.md 人格设定

#### portal（聊天助手 / 总调度）

```
你是 Agnes，一个智能助手。你负责所有的日常对话交互、信息检索、项目空间管理
和下级各项任务调度。当用户提出涉及编程、研究、写作、图像、视频、语音合成等专项
任务时，你应当通过 Kanban 看板创建任务并分配给对应的下级 profile 执行。

你的下级 profile 包括：
- coding：编程和代码生成
- research：研究和推理
- personal：计划任务及你交付的额外任务
- writing：文档编写
- pic：图像生成（文生图/图生图/多图合成）
- mov：视频生成（文生视频/图生视频/关键帧动画）
- tts：文字转语音（TTS）

除非用户询问架构细节，否则不需要主动暴露内部代号。用中文回复。
```

#### coding（编程）

```
你是 Agnes，一个专职编程助手。你负责编程和代码生成任务。
当通过 Kanban 接收到编程任务时，在工作空间 ~/workspace/<project_name>/code/ 中
完成代码编写、测试和调试。用中文回复。
```

#### research（研究）

```
你是 Agnes，一个专职研究助手。你负责研究和深度推理任务。
当通过 Kanban 接收到研究任务时，进行信息收集、分析、推理并输出研究报告，
报告保存到 ~/workspace/<project_name>/research/。用中文回复。
```

#### personal（日常助手）

```
你是 Agnes，一个专职日常助手。你负责所有的计划任务及 portal 交付的额外任务。
当通过 Kanban 或 Cron 接收到任务时，按计划执行并汇报结果。用中文回复。
```

#### writing（写作）

```
你是 Agnes，一个专职写作助手。你负责文档编写任务。
当通过 Kanban 接收到写作任务时，撰写高质量文档并交付到
~/workspace/<project_name>/documents/。用中文回复。
```

#### pic（图像生成）

```
你是 Agnes，一个专职图像生成助手。你负责文生图、图生图、多图合成任务。
你通过 generate_image_via_pic01 工具调用 Agnes 图像生成 API。

行为规范：
1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，
   从 body 中解析 project_name 和 prompt。
2. 如果缺少 project_name，调用 kanban_block(reason="缺少 project_name")
3. 调用 generate_image_via_pic01 时传入 project_name、prompt、file_name
4. 图像文件自动保存到 ~/workspace/<project_name>/target/images/<file_name>
5. 生成成功时调用 kanban_complete，metadata 中包含 output_files 路径
6. 生成失败时调用 kanban_block 说明原因
7. 不主动创建子任务或分配任务给其他 profile
用中文回复。
```

#### mov（视频生成）

```
你是 Agnes，一个专职视频生成助手。你负责文生视频、图生视频(ti2vid)、
关键帧动画任务。你通过 generate_video_via_mov01 工具调用 Agnes 视频生成 API。

行为规范：
1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，
   从 body 中解析 project_name、prompt、mode 等参数。
2. 如果缺少 project_name，调用 kanban_block(reason="缺少 project_name")
3. 调用 generate_video_via_mov01 时传入 project_name、prompt、file_name
   以及可选的 mode、image、width、height、num_frames、frame_rate、seed 等参数
4. 视频生成是异步的，工具可能返回 async 状态。此时需要启动后台监控进程。
5. 使用 monitor_video.py 脚本进行后台轮询（30s 间隔），
   通过 terminal(background=true, notify_on_complete=true) 启动
6. 视频文件自动保存到 ~/workspace/<project_name>/target/videos/<file_name>
7. 生成成功时调用 kanban_complete，metadata 中包含 output_files 路径
8. 生成失败时调用 kanban_block 说明原因
9. 不主动创建子任务或分配任务给其他 profile
用中文回复。
```

#### tts（文字转语音）

```
你是 Agnes，一个专职语音合成助手。你负责文字转语音（TTS）任务。
你通过 volcengine-tts 技能调用豆包语音克隆音色 API，将文字转为自然语音播报。

你的操作步骤：
1. 从 Kanban 任务 body 中读取 project_name、text（要朗读的文字）。
2. 通过 terminal 工具执行 TTS API 调用，生成 MP3 语音文件。
3. API 返回的 JSON 中包含 base64 编码的音频数据，需要用 python3 解码保存。
4. 语音文件保存到 ~/workspace/<project_name>/target/audio/<file_name>.mp3。

你用 terminal 工具执行以下命令调用 TTS API（注意路径使用 $HERMES_REAL_HOME 而非 ~，因为 home_mode: profile 下 ~ 指向的是 profile 内目录）：

```bash
set -a; source $HERMES_REAL_HOME/.hermes/profiles/tts/.env; set +a
TEXT="要朗读的文字"
OUTPUT=$HERMES_REAL_HOME/workspace/<project_name>/target/audio/<file_name>.mp3
REQID="$(date +%s)$(shuf -i 1000-9999 -n 1)"
curl -s -X POST 'https://openspeech.bytedance.com/api/v1/tts' \
  -H "x-api-key: $VOLC_TTS_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "app": { "cluster": "volcano_icl" },
    "user": { "uid": "豆包语音" },
    "audio": {
      "voice_type": "'"$VOLC_TTS_VOICE_ID"'",
      "encoding": "mp3",
      "speed_ratio": 1.0
    },
    "request": {
      "reqid": "'"$REQID"'",
      "text": "'"$TEXT"'",
      "operation": "query"
    }
  }' | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
if data['code'] == 3000:
    audio = base64.b64decode(data['data'])
    with open('$OUTPUT', 'wb') as f: f.write(audio)
    print(f'OK: {len(audio)/1024:.1f}KB, {int(data[\"addition\"][\"duration\"])/1000:.1f}s')
else:
    print(f'FAIL: {data[\"message\"]} (code: {data[\"code\"]})')
"
```

关键注意事项：
- ❌ 不要用 curl -o 直接保存——API 返回 JSON，不是二进制
- ❌ 不要硬编码 API Key 和 Voice ID——必须从 .env 加载
- ❌ 不要忽略 set -a——source .env 前必须 set -a
- reqid 每次请求必须唯一，用 date +%s + 随机数生成
- 长文本（超过 1024 字节）需要分段处理
- 用中文回复。
```

### 4.1 目录结构

```
/home/alan/
├── .hermes/                          # Hermes 主目录（default profile）
│   ├── config.yaml                   # default profile 配置（含 kanban 全局配置）
│   ├── .env                          # default profile 凭据
│   ├── SOUL.md                       # default profile 人格
│   ├── memories/                     # default profile 记忆
│   ├── kanban.db                     # Kanban 共享看板数据库
│   └── profiles/                     # 命名 profile 目录
│       ├── portal/
│       │   ├── config.yaml
│       │   ├── .env                  # 飞书凭据 + bjlab API key
│       │   ├── SOUL.md
│       │   ├── memories/
│       │   ├── skills/
│       │   ├── cron/
│       │   └── home/
│       │       └── .gitconfig
│       ├── coding/...（同上结构）
│       ├── research/...
│       ├── personal/...
│       ├── writing/...
│       ├── pic/
│       │   ├── config.yaml           # 含 agnes_router_pic 插件配置
│       │   ├── .env                  # AGNES_API_KEY（pic 专用）
│       │   ├── SOUL.md
│       │   ├── memories/
│       │   ├── plugins/
│       │   │   └── agnes_router_pic/ # 仅图像生成的插件变体
│       │   ├── skills/
│       │   │   └── creative/agnes-media/  # 图像技能文档
│       │   └── home/
│       │       └── .gitconfig
│       ├── mov/
│       │   ├── config.yaml           # 含 agnes_router_mov 插件配置
│       │   ├── .env                  # AGNES_API_KEY（mov 专用）
│       │   ├── SOUL.md
│       │   ├── memories/
│       │   ├── plugins/
│       │   │   └── agnes_router_mov/ # 仅视频生成的插件变体
│       │   ├── skills/
│       │   │   ├── creative/agnes-media/  # 视频技能文档
│       │   │   └── media/agnes-video-async-monitor/  # 异步监控技能
│       │   └── home/
│       │       └── .gitconfig
│       └── tts/
│           ├── config.yaml
│           ├── .env                  # VOLC_TTS_API_KEY, VOLC_TTS_VOICE_ID
│           ├── SOUL.md
│           ├── memories/
│           ├── skills/
│           │   └── voice/volcengine-tts/  # 火山引擎 TTS 技能
│           └── home/
│               └── .gitconfig
├── workspace/                        # 统一工作空间根目录
│   └── <project_name>/
│       ├── sources/
│       │   ├── images/               # 输入素材：参考图片
│       │   ├── videos/               # 输入素材：源视频
│       │   ├── scripts/              # 生成脚本
│       │   └── others/               # 其他输入文件
│       ├── target/                   # 输出结果
│       │   ├── images/               # 图像产出（pic 生成）
│       │   ├── videos/               # 视频产出（mov 生成）
│       │   ├── audio/                # 语音产出（TTS 生成）
│       │   ├── documents/            # 文档产出（writing 生成）
│       │   ├── code/                 # 代码产出（coding 生成）
│       │   └── research/             # 研究报告（research 生成）
│       └── <其他项目文件>
└── ...
```

### 4.2 项目隔离准则

1. 所有文件写入、读取和媒体生成任务，必须在一个具体项目目录下进行。统一工作空间根目录是 /home/alan/workspace。
2. 每个项目以 /home/alan/workspace/<project_name>/ 为根。输入素材放入 sources/ 子目录，输出结果放入 target/ 子目录。
3. 如果用户没有显式指定当前项目，portal 必须先询问或引导用户定义一个合规项目名。
4. project_name 必须是 ASCII 字符（小写字母、数字、下划线、连字符），不得包含 ../、斜杠、反斜杠、绝对路径或任何试图跳出 workspace 的内容。
   - 如果用户给出中文项目名（如"西域春宣发项目"），portal 必须将其转写为 ASCII slug（如 xiyuchun_xuanfa），然后在 kanban_create 的 body 中同时携带中文名和 slug：
     body="project_name: xiyuchun_xuanfa\nproject_display: 西域春宣发项目\n..."
5. portal 调用 kanban_create 创建下级任务时，必须在 body 中传入当前项目名 project_name，并拟定合理文件名，包含正确后缀名。
6. 绝对不要尝试构造 /etc、../、~/.ssh 等越界路径。所有文件操作严格限制在 /home/alan/workspace/<project_name>/ 下。
7. Kanban 任务 workspace 默认使用 dir:/home/alan/workspace/<project_name>，确保 worker 在正确项目目录下工作。
8. 不同项目的文件互不干扰，不跨项目读取或写入文件，除非用户明确指示。

### 4.3 Hermes 状态隔离（HERMES_HOME 边界）

每个 profile 有独立的 HERMES_HOME 目录（~/.hermes/profiles/<name>/），以下内容完全隔离：

| 隔离项 | 说明 |
|--------|------|
| config.yaml | 独立模型、提供商、插件、工具集配置 |
| .env | 独立 API 密钥（不同 profile 用不同的 key） |
| SOUL.md | 独立人格设定 |
| memories/ | 独立长期记忆（MEMORY.md, USER.md） |
| sessions/ | 独立会话历史 |
| skills/ | 独立技能 |
| cron/ | 独立定时任务 |
| plugins/ | 独立插件（pic 和 mov 各自安装自己的插件变体） |
| state.db | 独立状态数据库 |
| logs/ | 独立日志 |

Kanban 看板数据库（~/.hermes/kanban.db）是唯一的共享状态，所有 profile 通过它协作。

### 4.4 CLI 凭据隔离（HOME 边界，home_mode: profile）

每个 profile 的子进程 HOME 被设为 {HERMES_HOME}/home，实现独立的 CLI 身份：

| 隔离项 | 说明 |
|--------|------|
| git 提交身份 | 每个 profile 有独立的 .gitconfig（user.name, user.email） |
| SSH 密钥 | 每个 profile 有独立的 .ssh/ 目录 |
| npm/gh 等凭据 | 每个 profile 有独立的 CLI 工具登录态 |

部署时需要为每个 profile 初始化：
- ~/.hermes/profiles/<name>/home/.gitconfig（配置独立的 user.name 和 user.email）
- ~/.hermes/profiles/<name>/home/.ssh/（生成或链接专属密钥）

HERMES_REAL_HOME 环境变量保留真实 OS 用户目录（/home/alan），供需要回退到真实 HOME 的脚本使用。

### 4.5 Kanban 看板

Kanban 数据库位于 ~/.hermes/kanban.db，所有 profile 共享同一个看板。这是跨 profile 协作的核心机制：
- portal profile 作为 orchestrator（编排者），启用 kanban 工具集
- 其他 profile 作为 worker（执行者），由 dispatcher 自动分发任务
- 看板配置在 default profile 的 config.yaml 中

## 5. 互操作行为规范

### 5.1 角色职责边界

#### portal（编排者 / Orchestrator）

- 职责：接收用户指令、理解意图、确定项目名、导入物料、分解任务、分配给下级 profile、汇总结果
- 工具集：file, terminal, memory, skills, cronjob, kanban, delegation, todo
- 行为规范：
  1. 收到用户请求后，先确定当前 project_name。如果用户未指定，引导用户给出合规项目名。如果用户给出中文名，转写为 ASCII slug（见 4.2 节第 4 条）。
  2. 文本对话、信息检索、简单问答等普通任务由自己处理，不调用下级 profile。
  3. 如果用户通过聊天发送了附件文件（图片、文档、压缩包等），必须先保存到工作空间：
     - 创建项目目录骨架：`mkdir -p ~/workspace/<project_name>/sources/{images,videos,documents,others}`
     - 飞书/gateway 收到的附件文件会以临时路径或 URL 形式出现在消息上下文中。portal 通过 terminal 工具执行 `cp` 或 `mv` 将文件从 gateway 缓存路径复制到 sources/ 对应子目录：
       ```bash
       cp <消息上下文中的文件路径> ~/workspace/<project_name>/sources/<类型>/
       ```
       如果文件是 URL 形式，用 `curl -Lo` 下载：
       ```bash
       curl -Lo ~/workspace/<project_name>/sources/<类型>/<文件名> <文件URL>
       ```
     - 如果是压缩包（zip/rar），先下载到 sources/others/，然后解压到对应子目录
     - 记录已导入的文件清单，后续创建任务时将文件路径写入 body
  4. 只有当用户明确提出编程、研究、写作、图像、视频、语音合成（TTS）等专项任务时，才通过 kanban_create 分解任务并分配给对应 profile。
  5. kanban_create 的 body 中必须包含以下字段：
     - project_name：ASCII slug（必填）
     - project_display：中文项目名（可选，有中文名时填写）
     - 任务描述和具体需求
     - 涉及的文件路径清单（如 sources/images/logo.png）
     - 下游任务依赖的文本内容（如 TTS 需要的朗读文案、视频需要的 prompt 描述）
  6. 通过 kanban_link 建立任务依赖关系（如 research 完成后 writing 才开始）。
  7. 收到所有子任务完成事件后，汇总结果并通过飞书回复用户。
  8. 对用户屏蔽内部调度细节，除非用户明确询问架构。回复中直接给出最终结果和文件路径。
  9. 收到 worker blocked 事件时，判断是否需要用户输入。如果是，通过飞书询问用户；如果不需要，重新编排任务。
  10. tts 任务的 text 来源和 voice_type 来源：
      - text：portal 必须从素材中提取或自行撰写需要朗读的文案，直接在 kanban_create 的 body 中传入 text 参数
      - voice_type：如果用户在请求中指定了音色 ID，直接传入；如果用户只说"用指定音色/我的音色"但未提供 ID，portal 必须追问用户具体的音色 ID，不得自行猜测或伪造
  11. 视频任务的 prompt 来源采用**两阶段编排**：
      - 阶段一：portal 先创建 research 任务（不依赖任何前置任务），research 负责分析素材并产出报告
      - 阶段二：research 完成后 portal 被重新唤醒（orchestrator_profile 机制），此时 portal 阅读 research 报告，然后创建 writing、tts、mov 等下游任务，在 body 中写入基于真实素材内容的具体 prompt
      - 禁止在 research 未完成前预先创建需要素材知识的任务
  12. 飞书文件传输限制与处理规则：
      - 输入来源：用户可以通过飞书直接发送文件，也可以通过飞书发送下载链接。portal 对两者都需支持——直接附件按第 3 条流程处理，下载链接用 `curl -Lo` 下载到 sources/
      - 输出限制：飞书单次文件传输上限约为 20MB。生成的产出文件（图像、视频、音频、文档、PPT 等）如果超过 20MB，不得直接通过飞书发送
      - 大文件处理：超过 20MB 的文件，不通过飞书传输，另行处理。源文件保留在 workspace 中
      - 汇总回复时对于大文件告知用户文件已保存到工作空间及本地路径，对于小文件直接附上本地路径

#### coding / research / writing / personal（执行者 / Worker）

- 职责：接收 Kanban 任务、在指定项目目录下执行、完成或阻塞
- 工具集：file, terminal, memory, skills（不含 kanban 编排工具）
- 依赖的 Python 库（需预先安装）：
  - research profile：`python-docx`（读取 .docx）、`python-pptx`（读取 .pptx）、`PyMuPDF`（读取 .pdf）、`openpyxl`（读取 .xlsx）、`python-magic`（文件类型检测）
  - writing profile：`python-pptx`（生成 .pptx）
- 行为规范：
  1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，从 body 中解析 project_name。
  2. 如果 task body 中缺少 project_name，调用 kanban_block(reason="缺少 project_name，无法确定工作目录") 阻塞任务。
  3. 所有文件操作严格在 /home/alan/workspace/<project_name>/ 下进行，不越界。
  4. 各 profile 的专项行为：
     - coding：代码产出写入 <project_name>/target/code/，使用 git 管理版本
     - research：读取 sources/ 下的文档素材（docx/pdf/pptx/txt），使用 Python 库提取文本内容，分析后产出研究报告写入 <project_name>/target/research/。
       读取 docx：`python3 -c "import docx; print(docx.Document('path').text)"`
       读取 pdf：`python3 -c "import pymupdf; print(''.join([p.get_text() for p in pymupdf.open('path')]))"`
       读取 pptx：`python3 -c "from pptx import Presentation; [print(s.text) for slide in Presentation('path').slides for s in slide.shapes if hasattr(s, 'text')]"`
     - writing：根据 research 报告或 portal 提供的素材，编写文档。如需生成 PPT：
       `python3 -c "from pptx import Presentation; from pptx.util import Inches; prs = Presentation(); ...; prs.save('path')"`
       文档产出写入 <project_name>/target/documents/。
  5. 长时间任务（预计超过 5 分钟）每隔几分钟调用 kanban_heartbeat(note="...") 报告存活。
  6. 完成后调用 kanban_complete(summary="...", metadata={"output_files": ["绝对路径1", ...], "project_name": "..."}) 交付。
  7. 遇到阻碍调用 kanban_block(reason="...") 阻塞并等待人工输入。
  8. 不主动创建子任务或分配任务给其他 profile。如果任务需要其他 profile 的能力，block 并说明原因，由 portal 重新编排。
  9. 媒体生成类需求（图像/视频/语音合成）不是这些 profile 的职责，block 并说明 "需要 pic/mov/tts profile 处理"。

#### pic（图像生成执行者）

- 职责：接收 Kanban 图像任务、调用 Agnes 图像 API 生成、交付
- 工具集：file, terminal, memory, skills, agnes_router_pic（仅 generate_image_via_pic01 工具）, todo
- 行为规范：
  1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，从 body 中解析 project_name、prompt、size、参考图 URL 等参数。
  2. 如果缺少 project_name，调用 kanban_block(reason="缺少 project_name，无法确定输出目录")。
  3. 调用 generate_image_via_pic01 时传入：
     - project_name（必填）
     - prompt（必填，详细的视觉描述）
     - file_name（必填，带正确后缀名如 .png/.jpg）
     - size（可选，默认 1024x1024）
     - image（可选，图生图/多图合成的参考图 URL 数组）
  4. 图像自动保存到 ~/workspace/<project_name>/target/images/<file_name>。
  5. 生成成功时调用 kanban_complete，在 summary 中告知本地路径和 remote_url，metadata 包含 output_files。
  6. 生成失败时调用 kanban_block(reason="生成失败：...")。若是安全拦截，直接说明该路径请求被拦截。
  7. 不主动创建子任务或分配任务给其他 profile。
  8. 遇到视频/语音合成需求时 block 并说明 "需要 mov/tts profile 处理"。

#### mov（视频生成执行者）

- 职责：接收 Kanban 视频任务、调用 Agnes 视频 API 生成、监控异步任务、交付
- 工具集：file, terminal, memory, skills, agnes_router_mov（仅 generate_video_via_mov01 工具）, todo
- 行为规范：
  1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，从 body 中解析 project_name、prompt、mode、width、height 等参数。
  2. 如果缺少 project_name，调用 kanban_block(reason="缺少 project_name，无法确定输出目录")。
  3. 调用 generate_video_via_mov01 时传入：
     - project_name（必填）
     - prompt（必填，详细的视频/分镜描述）
     - file_name（必填，带正确后缀名 .mp4）
     - mode（可选：ti2vid 图生视频 / keyframes 关键帧动画）
     - image（可选，图生视频的单张图片 URL）
     - width/height/num_frames/frame_rate/seed/negative_prompt（可选）
  4. 视频生成是异步的。如果工具返回异步状态，从 raw.video_id 中提取 video_id。
  5. 启动后台监控进程（注意：monitor_video.py 需先改造为支持 CLI 参数，路径使用 $HERMES_REAL_HOME）：
     ```
     terminal(
       command='python3 $HERMES_REAL_HOME/.hermes/profiles/mov/skills/media/agnes-video-async-monitor/scripts/monitor_video.py --video-id <解析出的VIDEO_ID> --project-dir ~/workspace/<project_name> --output <file_name>.mp4',
       background=True,
       notify_on_complete=True,
       timeout=600
     )
     ```
  6. 视频完成后自动保存到 ~/workspace/<project_name>/target/videos/<file_name>。
  7. 生成成功时调用 kanban_complete，在 summary 中告知本地路径，metadata 包含 output_files。
  8. 生成失败时调用 kanban_block(reason="生成失败：...")。若是安全拦截，直接说明该路径请求被拦截。
  9. 不主动创建子任务或分配任务给其他 profile。
  10. 遇到图像/语音合成需求时 block 并说明 "需要 pic/tts profile 处理"。

#### tts（文字转语音）

- 职责：接收 Kanban 语音合成任务、将文字转为语音、交付
- 工具集：file, terminal, memory, skills, todo
- 行为规范（基于 volcengine TTS API 实现）：
  1. 被 dispatcher 唤醒后，首先调用 kanban_show() 读取任务详情，从 body 中解析 project_name、text（要朗读的文字）、voice_type（音色 ID，可选，默认使用 .env 中 VOLC_TTS_VOICE_ID）。
  2. 如果缺少 project_name，调用 kanban_block(reason="缺少 project_name，无法确定输出目录")。
  3. 语音文件保存到 ~/workspace/<project_name>/target/audio/<file_name>.mp3。
  4. 火山引擎 TTS API 的调用方式（通过 terminal 工具执行）：
     ```bash
     set -a; source $HERMES_REAL_HOME/.hermes/profiles/tts/.env; set +a
     TEXT="要朗读的文字"
     OUTPUT="$HERMES_REAL_HOME/workspace/<project_name>/target/audio/<file_name>.mp3"
     REQID="$(date +%s)$(shuf -i 1000-9999 -n 1)"
     curl -s -X POST 'https://openspeech.bytedance.com/api/v1/tts' \
       -H "x-api-key: $VOLC_TTS_API_KEY" \
       -H 'Content-Type: application/json' \
       -d '{
         "app": { "cluster": "volcano_icl" },
         "user": { "uid": "豆包语音" },
         "audio": {
           "voice_type": "'"$VOLC_TTS_VOICE_ID"'",
           "encoding": "mp3",
           "speed_ratio": 1.0,
           "pitch_ratio": 1.0,
           "volume_ratio": 1.0
         },
         "request": {
           "reqid": "'"$REQID"'",
           "text": "'"$TEXT"'",
           "operation": "query"
         }
       }' | python3 -c "
     import sys, json, base64
     data = json.load(sys.stdin)
     if data['code'] == 3000:
         audio = base64.b64decode(data['data'])
         with open('$OUTPUT', 'wb') as f: f.write(audio)
         print(f'OK: {len(audio)/1024:.1f}KB, {int(data[\"addition\"][\"duration\"])/1000:.1f}s')
     else:
         print(f'FAIL: {data[\"message\"]} (code: {data[\"code\"]})')
     "
     ```
  5. 关键注意事项：
     - ❌ 不要用 curl -o 直接保存：API 返回的是 JSON，不是 MP3 二进制，必须通过 python3 解码 data 字段
     - ❌ 不要硬编码 API Key 和 Voice ID：必须从 .env 加载
     - ❌ 不要忽略 set -a：source .env 前必须 set -a，否则变量不会 export 到子进程
     - reqid 每次请求必须唯一，用 date +%s + 随机数生成
     - 文字 UTF-8 编码长度建议控制在 1024 字节以内，长文本分段处理
     - 国内网络环境正常，海外可能因 SSL 问题无法连接
  6. 可调节参数：speed_ratio（语速 0.1~2.0）、pitch_ratio（音调 0.1~3.0）、volume_ratio（音量 0.1~3.0）、encoding（mp3/wav/pcm/ogg_opus）
  7. 生成成功时调用 kanban_complete，在 summary 中告知本地路径和语音时长，metadata 包含 output_files
  8. 生成失败时调用 kanban_block(reason="tts 生成失败：...") 说明原因
  9. 不主动创建子任务或分配任务给其他 profile
  10. 遇到图像/视频需求时 block 并说明 "需要 pic/mov profile 处理"

### 5.2 任务流转协议

#### 5.2.1 标准任务流

```
用户 → 飞书 → portal gateway
  → portal 理解意图，确定 project_name，保存附件到 sources/
  → portal 判断是否需要下级 profile 参与
    → 普通任务 portal 自行处理
    → 专项任务 → **两阶段编排**

**阶段一：先分析素材**
  → kanban_create 创建 research 任务（无依赖）
    assignee=research, title="分析西域春宣发素材",
    body="project_name: xiyuchun_xuanfa
project_display: 西域春宣发项目
task: 分析 sources/ 下的全部素材文件
files:
  - sources/documents/brand_intro.docx
  - sources/images/logo.png
  - sources/others/market_data.pdf
output: 输出研究报告到 target/research/"
  → portal 调用 kanban_complete 完成本阶段编排
  → dispatcher 分发 research 任务
  → research worker 执行：读取素材 → 提取文本 → 分析 → 产出报告
  → research 完成后，portal 被重新唤醒（orchestrator_profile）

**阶段二：根据研究结果创建下游任务**
  → portal 阅读 research 报告（read_file target/research/xxx.md）
  → 根据报告内容创建具体任务：
    → assignee=writing, title="生成宣讲PPT",
      body="project_name: xiyuchun_xuanfa
task: 根据 research 报告生成宣讲 PPT"
    → 询问用户 voice_type（如尚未提供），然后创建 tts 任务：
    → assignee=tts, title="合成宣发配音",
      body="project_name: xiyuchun_xuanfa
task: 将以下文案转为语音
text: （从 research 报告提取的完整文案）
voice_type: （用户提供的音色 ID）"
    → assignee=mov, title="生成宣发视频",
      body="project_name: xiyuchun_xuanfa
prompt: （根据 research 报告内容撰写的详细视频描述）
mode: ti2vid"
  → portal 调用 kanban_complete 完成本阶段编排
  → dispatcher 分发下游任务
  → 所有任务完成后，portal 再次被唤醒
  → portal 汇总结果，通过飞书回复用户（包含所有产出文件路径）
```

#### 5.2.2 阻塞处理

```
worker 遇到阻碍 → kanban_block(reason="需要用户提供XXX")
  → dispatcher 将任务状态设为 blocked
  → 事件推送到 portal 的飞书会话（auto_subscribe_on_create=true）
  → portal 判断是否需要用户输入
    → 需要 → 通过飞书询问用户
    → 不需要 → portal 调用 kanban_comment 补充上下文 → kanban_unblock
  → 用户通过飞书回复
  → portal 调用 kanban_comment 补充上下文
  → portal 调用 kanban_unblock 恢复任务
  → dispatcher 重新分发
```

#### 5.2.3 失败重试

- dispatcher 默认 failure_limit=2：连续 2 次失败后自动 block
- worker 进程崩溃：dispatcher 检测 PID 消失，回收任务重新分发
- worker 超时无心跳：dispatch_stale_timeout_seconds（默认 2 小时）后回收
- 回收是良性的：任务回到 ready 状态重新排队，不增加失败计数

### 5.3 Kanban 编排配置

在 default profile 的 config.yaml 中配置：

```yaml
kanban:
  dispatch_in_gateway: true           # dispatcher 运行在 gateway 内
  dispatch_interval_seconds: 60       # 每 60 秒扫描一次
  auto_decompose: false               # 关闭自动分解，由 portal 手动编排
  orchestrator_profile: portal          # 编排任务归属 portal
  default_assignee: personal          # 兜底分配给 personal
  max_in_progress: 3                  # 全局并发上限（考虑 3.8GB 内存）
  max_in_progress_per_profile: 1      # 每 profile 同时只跑 1 个任务
  failure_limit: 2                    # 连续 2 次失败后 block
  dispatch_stale_timeout_seconds: 7200  # worker 无心跳 2 小时后回收（默认 4h，3.8GB 环境缩短）
```

### 5.4 各 Profile 工具集配置

```yaml
# portal profile - 编排者
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - cronjob
  - kanban
  - delegation
  - todo

# coding profile - 编程执行者
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - code_execution
  - todo

# research profile - 研究执行者
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - web
  - todo

# writing profile - 写作执行者
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - todo

# personal profile - 日常任务执行者
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - cronjob
  - todo
# 建议启用 disk-cleanup 插件定期清理媒体产出缓存

# pic profile - 图像生成执行者
# 不需要 image_gen 工具集，而是通过 agnes_router_pic 插件提供 generate_image_via_pic01
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - todo

# mov profile - 视频生成执行者
# 不需要 video_gen 工具集，而是通过 agnes_router_mov 插件提供 generate_video_via_mov01
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - todo

# tts profile - 文字转语音（TTS）
enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - todo
```

## 6. Agnes Media 插件部署

### 6.1 插件拆分方案

从 agnes-media-skill 项目中复制并修改，拆分为两个独立插件：

**agnes_router_pic（pic profile 专用）**
- 只注册 generate_image_via_pic01 工具
- 只调用图像 API（/v1/images/generations）
- 只依赖 AGNES_API_KEY 环境变量
- 只包含图像相关的 workspace_manager 逻辑

**agnes_router_mov（mov profile 专用）**
- 只注册 generate_video_via_mov01 工具
- 只调用视频 API（/v1/videos）
- 只依赖 AGNES_API_KEY 环境变量
- 包含视频异步轮询逻辑

### 6.2 插件安装

```bash
# 源文件路径
SOURCE_DIR=/tmp/agnes-media-skill

# pic profile 安装
mkdir -p ~/.hermes/profiles/pic/plugins/
cp -r $SOURCE_DIR/plugins/agnes_router ~/.hermes/profiles/pic/plugins/agnes_router_pic
# 编辑 agnes_router_pic/__init__.py，只保留 image 工具的注册，删除 video 工具注册
# 编辑 plugin.yaml 修改名称和描述，删除 video 相关配置

# mov profile 安装
mkdir -p ~/.hermes/profiles/mov/plugins/
cp -r $SOURCE_DIR/plugins/agnes_router ~/.hermes/profiles/mov/plugins/agnes_router_mov
# 编辑 agnes_router_mov/__init__.py，只保留 video 工具的注册，删除 image 工具注册
# 编辑 plugin.yaml 修改名称和描述，删除 image 相关配置
```

### 6.3 技能安装

```bash
# pic profile 安装主技能（图像相关文档）
mkdir -p ~/.hermes/profiles/pic/skills/creative/
cp -r $SOURCE_DIR/skills/creative/agnes-media/. \
      ~/.hermes/profiles/pic/skills/creative/agnes-media/
# 可以删除其中视频相关的参考文档

# mov profile 安装主技能 + 异步监控技能
mkdir -p ~/.hermes/profiles/mov/skills/creative/
mkdir -p ~/.hermes/profiles/mov/skills/media/
cp -r $SOURCE_DIR/skills/creative/agnes-media/. \
      ~/.hermes/profiles/mov/skills/creative/agnes-media/
cp -r $SOURCE_DIR/skills/media/agnes-video-async-monitor/. \
      ~/.hermes/profiles/mov/skills/media/agnes-video-async-monitor/
```

### 6.4 视频异步监控脚本配置

mov profile 的监控脚本需要预先配置 VIDEO_ID 等变量。由于每次任务的 video_id 不同，
推荐在 mov profile 的 SOUL.md 中指导模型如下：

```
视频生成完成后，在工具返回的 raw 中提取 video_id 字段。
然后运行以下命令进行后台监控（注意使用 $HERMES_REAL_HOME 而非 ~）：
  python3 $HERMES_REAL_HOME/.hermes/profiles/mov/skills/media/agnes-video-async-monitor/scripts/monitor_video.py --video-id <VIDEO_ID> --project-dir $HERMES_REAL_HOME/workspace/<project_name> --output <file_name>.mp4
```

更优方案：修改 monitor_video.py 脚本，改为从命令行参数接收 VIDEO_ID 和 OUTPUT_DIR：
```bash
python3 $HERMES_REAL_HOME/.hermes/profiles/mov/skills/media/agnes-video-async-monitor/scripts/monitor_video.py --video-id <VIDEO_ID> --project-dir $HERMES_REAL_HOME/workspace/<project_name> --output <file_name>.mp4
```

### 6.5 图像 API 注意事项

- 图像 API 经常返回 HTTP 503（队列满），这是瞬态错误，非失败
- 插件配置了 30 秒间隔、最多 10 次重试
- 图生图时：image 参数放在 extra_body.image[] 中
- response_format 必须放在 extra_body 内，不能放顶层
- 支持 URL 和 Data URI 两种图片输入方式

### 6.6 视频 API 注意事项

- 视频生成是异步的，POST 后立即返回 task_id/video_id
- 必须用 GET /agnesapi?video_id=<real_video_id> 查询状态
- 绝对不要用 GET /v1/videos/{task_id}——该 endpoint 不返回正确结果
- video_id 是 base64 编码的，需要用 check_task.py 解码
- 典型处理时间：简单 1-3 分钟，复杂 3-10 分钟，高分辨率 5-15 分钟
- 长时间轮询需要用后台进程（不能使用 cron，因为 cron 最小间隔 30 分钟）

## 7. 飞书网关配置

### 7.1 portal profile 飞书接入

仅在 portal profile 上启用飞书网关，其他 profile 不启动网关。

portal profile 的 .env 需要配置：
```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=secret_xxx
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_ALLOWED_USERS=ou_xxx           # 限定用户
FEISHU_HOME_CHANNEL=oc_xxx            # cron 结果投递频道
```

### 7.2 网关运行模式

由于仅 portal 需要网关，采用**单进程模式**（不使用 multiplexing）：
- portal profile 独立运行一个 gateway 进程
- 该 gateway 同时承载 kanban dispatcher
- 其他 profile 不启动网关，仅通过 kanban dispatcher 以 worker 方式被唤醒

### 7.3 systemd 开机自启

为 portal profile 创建 systemd 用户服务：

```bash
hermes -p portal gateway install   # 创建 hermes-gateway-portal.service
```

同时配置：
```bash
sudo loginctl enable-linger alan   # 允许用户服务在 SSH 断开后继续运行
```

## 8. Cron 定时任务

### 8.1 Cron 架构

- Cron 调度器运行在 portal profile 的 gateway 内
- 定时任务的 cron agent 使用 portal profile 的模型和配置
- 交付目标默认为飞书（deliver=feishu 或指定频道）

### 8.2 计划的定时任务

部署完成后按需创建，示例：
```bash
# 每日早报
portal cron create "every 1d at 09:00" \
  "检查昨日 Kanban 看板状态，汇总未完成任务和阻塞项，生成日报" \
  --deliver feishu

# 定期清理
portal cron create "every 1d at 03:00" \
  "清理 workspace 中的临时文件" \
  --deliver local
```

## 9. 部署步骤

### 9.1 前置准备

1. 确认 api.bjlab.tk 支持所需模型（deepseek-v4-flash, deepseek-v4-pro, glm-5.2）
2. 获取 Agnes AI API Key（apihub.agnes-ai.com），用于媒体工具（pic/mov）和可选的后备 LLM 模型（agnes-2.0-flash）
3. 获取火山引擎 TTS API Key 和 Voice ID（用于 tts profile）
4. 确认飞书应用凭据（APP_ID, APP_SECRET）
5. 创建工作目录：mkdir -p ~/workspace
6. 克隆 agnes-media-skill 源码：git clone https://github.com/aiedwardai/agnes-media-skill.git /tmp/agnes-media-skill
7. 安装文档处理 Python 库（用于 research 和 writing profile）：
   ```bash
   pip install python-docx python-pptx PyMuPDF openpyxl python-magic
   ```

### 9.2 创建 Profile

```bash
# 逐个创建，从 default clone 配置，然后定制
hermes profile create portal --clone
hermes profile create coding --clone
hermes profile create research --clone
hermes profile create personal --clone
hermes profile create writing --clone
hermes profile create pic --clone
hermes profile create mov --clone
hermes profile create tts --clone
```

### 9.3 配置每个 Profile

对每个 profile 修改以下文件：

**1. config.yaml（以 pic 为例）：**
```yaml
model:
  default: deepseek-v4-flash       # pic profile 的 LLM 模型
provider: custom:api.bjlab.tk
custom_providers:
  - name: api.bjlab.tk
    base_url: https://api.bjlab.tk/v1
    api_key: sk-...     # bjlab 的密钥
    api_mode: chat_completions

terminal:
  backend: local
  cwd: /home/alan/workspace
  home_mode: profile

memory:
  memory_enabled: true
  user_profile_enabled: true

plugins:
  enabled:
    - agnes_router_pic    # pic 用；mov 用 agnes_router_mov
  entries:
    agnes_router_pic:
      workspace_root: ~/workspace
      image_endpoint: https://apihub.agnes-ai.com/v1/images/generations
      image_model: agnes-image-2.0-flash
      image_timeout: 180
      download_timeout: 300
      max_retries: 10
      retry_delay: 30.0

enabled_toolsets:
  - file
  - terminal
  - memory
  - skills
  - todo
```

**2. SOUL.md：** 写入对应人格设定（见 3.4 节）

**3. .env：**
- portal, coding, research, personal, writing：不需要额外 env（API key 在 config.yaml 中），但如需 fallback 模型则加 `AGNES_CHAT_API_KEY=sk-xxx`
- pic：`AGNES_API_KEY=sk-xxx`（pic 专用的 Agnes 媒体 key）；如需 fallback 加 `AGNES_CHAT_API_KEY=sk-xxx`
- mov：`AGNES_API_KEY=sk-xxx`（mov 专用的 Agnes 媒体 key，与 pic 不同）；如需 fallback 加 `AGNES_CHAT_API_KEY=sk-xxx`
- tts：`VOLC_TTS_API_KEY=xxx`, `VOLC_TTS_VOICE_ID=xxx`
- portal 额外：`FEISHU_APP_ID=...`, `FEISHU_APP_SECRET=...`
- 全 profile（启用 fallback 时）：`AGNES_CHAT_API_KEY=sk-xxx`（agnes-2.0-flash 聊天 API 的密钥，各 profile 各自在 .env 中配置）
  注意：pic 和 mov 一旦启用 fallback，其 .env 中必须同时包含 `AGNES_API_KEY=xxx`（媒体专用）和 `AGNES_CHAT_API_KEY=xxx`（后备 LLM 专用），即使两者使用同一密钥也必须分别声明，缺一不可。

**4. home/.gitconfig：** 为每个 profile 配置独立的 git 身份

### 9.4 安装 Agnes Media 插件和技能

```bash
SOURCE_DIR=/tmp/agnes-media-skill
PROFILES_DIR=~/.hermes/profiles

# ===== pic profile =====
# 复制插件并重命名为 agnes_router_pic
cp -r $SOURCE_DIR/plugins/agnes_router $PROFILES_DIR/pic/plugins/agnes_router_pic
# 编辑 __init__.py 删除 video 工具注册
# 编辑 plugin.yaml 改名为 agnes_router_pic，只保留 image 配置

# 复制主技能
mkdir -p $PROFILES_DIR/pic/skills/creative/
cp -r $SOURCE_DIR/skills/creative/agnes-media $PROFILES_DIR/pic/skills/creative/agnes-media

# ===== mov profile =====
# 复制插件并重命名为 agnes_router_mov
cp -r $SOURCE_DIR/plugins/agnes_router $PROFILES_DIR/mov/plugins/agnes_router_mov
# 编辑 __init__.py 删除 image 工具注册
# 编辑 plugin.yaml 改名为 agnes_router_mov，只保留 video 配置

# 复制主技能 + 异步监控技能
mkdir -p $PROFILES_DIR/mov/skills/creative/
mkdir -p $PROFILES_DIR/mov/skills/media/
cp -r $SOURCE_DIR/skills/creative/agnes-media $PROFILES_DIR/mov/skills/creative/agnes-media
cp -r $SOURCE_DIR/skills/media/agnes-video-async-monitor $PROFILES_DIR/mov/skills/media/agnes-video-async-monitor
```

### 9.5 配置 Kanban 看板

1. 在 default profile 的 config.yaml 中添加 kanban 配置（见 5.3 节）
2. 为每个 profile 设置 description：
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
3. 初始化看板：
   ```bash
   hermes kanban init
   ```

### 9.6 配置飞书网关

1. 在 portal profile 的 .env 中填入飞书凭据
2. 在飞书开放平台配置应用权限和事件（见飞书文档）
3. 安装 systemd 服务：
   ```bash
   hermes -p portal gateway install
   ```

### 9.7 启动服务

```bash
# 允许用户服务在 SSH 断开后继续运行
sudo loginctl enable-linger alan

# 创建 swap（可选，推荐）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 启动 portal 网关（含 kanban dispatcher + cron 调度）
hermes -p portal gateway start

# 验证
hermes -p portal gateway status
hermes profile list
hermes kanban stats
```

### 9.8 验证清单

- [ ] hermes profile list 显示全部 8 个 profile + default
- [ ] 每个 profile 的 config.yaml 模型和提供商配置正确
- [ ] 每个 profile 的 SOUL.md 内容正确
- [ ] 每个 profile 的 memory_enabled 为 true
- [ ] 每个 profile 的 home_mode 为 profile
- [ ] 每个 profile 的 terminal.cwd 为 ~/workspace
- [ ] 每个 profile 的 home/.gitconfig 已配置独立 git 身份
- [ ] tts profile 的 .env 包含 VOLC_TTS_API_KEY 和 VOLC_TTS_VOICE_ID
- [ ] pic profile 的 .env 包含 AGNES_API_KEY
- [ ] mov profile 的 .env 包含 AGNES_API_KEY（与 pic 不同）
- [ ] portal profile 的 .env 包含飞书凭据
- [ ] pic profile 的 plugins/agnes_router_pic 已安装且只注册了 generate_image_via_pic01
- [ ] mov profile 的 plugins/agnes_router_mov 已安装且只注册了 generate_video_via_mov01
- [ ] mov profile 的 skills/media/agnes-video-async-monitor 已安装
- [ ] portal gateway 启动并连接飞书成功
- [ ] kanban.db 已初始化
- [ ] kanban dispatcher 在 gateway 内运行
- [ ] 通过飞书发送消息，portal 能响应
- [ ] 创建图像生成 Kanban 任务，dispatcher 能分发到 pic profile 并成功执行
- [ ] 创建视频生成 Kanban 任务，dispatcher 能分发到 mov profile 并成功执行
- [ ] systemd 服务开机自启生效

## 10. 资源评估

### 10.1 内存考量

- 当前可用内存约 3.1 GB
- gateway 进程（portal）约 200-400 MB
- kanban dispatcher 约 50 MB
- 每个 kanban worker 是一个独立的 hermes 进程，约 150-300 MB
- 配置 max_in_progress: 3, max_in_progress_per_profile: 1
- 预计峰值内存：gateway(300MB) + 3 worker(900MB) = 1.2 GB
- 建议创建 2GB swap 防止内存溢出

### 10.2 磁盘考量

- 当前可用 12 GB
- Hermes 代码 + venv 约 1 GB
- 每个 profile 目录约 50-100 MB（含 home/）
- 8 个 profile 约 800 MB
- kanban.db + 会话 + 日志预计 < 2 GB
- 媒体生成产出可能较大（尤其是视频，单个可达 10-50MB），需要定期清理
- 建议启用 disk-cleanup 插件

## 11. 维护与运维

### 11.1 日常操作

```bash
# 查看所有 profile 状态
hermes profile list

# 查看 Kanban 看板
hermes kanban list
hermes kanban stats

# 查看 gateway 日志
tail -f ~/.hermes/profiles/portal/logs/gateway.log

# 更新 Hermes
hermes update   # 更新代码 + 同步技能到所有 profile

# 重启 portal 网关
hermes -p portal gateway restart
```

### 11.2 添加新定时任务

通过飞书聊天直接创建，或通过 CLI：
```bash
portal cron create "every 6h" "检查看板阻塞任务并提醒" --deliver feishu
```

### 11.3 添加新 profile

```bash
hermes profile create <name> --clone
# 编辑 config.yaml, SOUL.md, .env, home/.gitconfig
hermes profile describe <name> --text "描述"
```

### 11.4 更新 Agnes Media 插件

```bash
# 拉取最新源码
cd /tmp/agnes-media-skill && git pull

# 同步到 pic profile（仅同步核心逻辑，不覆盖 __init__.py 和 plugin.yaml）
cp -r plugins/agnes_router/* ~/.hermes/profiles/pic/plugins/agnes_router_pic/

# 同步到 mov profile（同上）
cp -r plugins/agnes_router/* ~/.hermes/profiles/mov/plugins/agnes_router_mov/

# ⚠️ 注意：pic 和 mov 的插件是拆分后的变体（pic 版删除了 video 工具注册，
# mov 版删除了 image 工具注册）。全量覆盖后必须重新执行 9.4 节的拆分修改步骤
# （编辑 __init__.py 和 plugin.yaml），否则插件会恢复为完整版，破坏角色隔离。

# 重启 Hermes 使插件生效
```

## 12. 待办事项

- [ ] 获取 Agnes AI API Key（apihub.agnes-ai.com），用于 pic/mov 媒体工具 + 可选 fallback 模型
- [ ] 确认 Agnes 聊天 API（agnes-2.0-flash）是否与媒体 API 使用同一密钥或不同密钥 → 决定 AGNES_CHAT_API_KEY
- [ ] 获取火山引擎 TTS API Key 和 Voice ID
- [ ] 获取飞书 APP_ID 和 APP_SECRET
- [ ] 改造 monitor_video.py 脚本使其支持 --video-id / --project-dir / --output 命令行参数
- [ ] 开发 volcengine-tts 技能文案（用于 tts profile 的技能文档，参考 https://github.com/e703/notes/blob/master/00_005_About_AI/skills/volcengine-tts-skill/SKILL.md）
- [ ] 为每个 profile 分配独立的 git 提交身份（user.name, user.email）
- [ ] 修改 agnes_router 插件代码，拆分为 pic 版（仅 image 工具）和 mov 版（仅 video 工具）
- [ ] 在 personal profile 的 plugins.enabled 中添加 disk-cleanup，并配置清理策略，防止媒体文件堆积撑满磁盘