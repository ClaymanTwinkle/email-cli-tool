# emailcli 设计文档

## 概述

一个 Python CLI 工具，用于通过命令行发送邮件，支持纯文本/HTML 格式，可携带图片和文件附件。

## 技术选型

- **语言**: Python >= 3.10
- **包管理**: uv + pyproject.toml
- **CLI 框架**: click
- **配置解析**: pyyaml
- **邮件构建/发送**: Python 标准库 (email, smtplib, mimetypes)
- **测试**: pytest

## 项目结构

```
emailcli/
├── pyproject.toml
├── README.md
├── src/
│   └── emailcli/
│       ├── __init__.py
│       ├── cli.py          # click CLI 入口，参数解析
│       ├── config.py        # 配置文件加载
│       ├── message.py       # 邮件构建（MIME 组装、附件处理）
│       ├── sender.py        # Sender 抽象接口 + SmtpSender 实现
│       └── exceptions.py    # 自定义异常
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_message.py
    └── test_sender.py
```

### 模块职责

- `cli.py` — 参数解析、调用核心逻辑、统一异常处理
- `config.py` — 加载和校验 `~/.emailcli/config.yaml`
- `message.py` — 构建 MIME 邮件对象（text/html/附件）
- `sender.py` — Sender 抽象基类 + SmtpSender 实现
- `exceptions.py` — 自定义异常类型

## CLI 接口

```bash
# 纯文本邮件
emailcli send \
  --to user@example.com \
  --subject "Hello" \
  --body "Hello World"

# 多个收件人
emailcli send \
  --to user1@example.com \
  --to user2@example.com \
  --subject "Hello" \
  --body "Hello World"

# HTML 邮件
emailcli send \
  --to user@example.com \
  --subject "Report" \
  --html "<h1>Report</h1><p>Content</p>"

# text + HTML（multipart/alternative）
emailcli send \
  --to user@example.com \
  --subject "Report" \
  --body "Plain text fallback" \
  --html "<h1>Report</h1>"

# 携带附件
emailcli send \
  --to user@example.com \
  --subject "Files" \
  --body "See attachments" \
  --attach report.pdf \
  --attach photo.png

# 从文件读取 HTML 正文
emailcli send \
  --to user@example.com \
  --subject "Newsletter" \
  --html-file template.html \
  --attach data.csv

# 从 stdin 读取正文
echo "Hello" | emailcli send \
  --to user@example.com \
  --subject "Hi" \
  --body -

# 初始化配置
emailcli init

# 查看当前配置
emailcli config show
```

### 参数说明

| 参数 | 必填 | 可重复 | 说明 |
|------|------|--------|------|
| `--to` | 是 | 是 | 收件人邮箱 |
| `--subject` | 是 | 否 | 邮件主题 |
| `--body` | 否* | 否 | 纯文本正文，`-` 表示从 stdin 读取 |
| `--html` | 否* | 否 | HTML 正文字符串 |
| `--html-file` | 否* | 否 | 从文件读取 HTML 正文 |
| `--attach` | 否 | 是 | 附件文件路径 |
| `--from` | 否 | 否 | 发件人（覆盖配置文件默认值） |

*`--body` 和 `--html`/`--html-file` 至少提供一个。

## 配置文件

路径：`~/.emailcli/config.yaml`

```yaml
from: me@example.com

smtp:
  host: smtp.gmail.com
  port: 587
  username: me@example.com
  password: app-password-here
  encryption: starttls  # starttls | ssl | none
```

- `emailcli init` 交互式引导创建配置
- 文件权限设为 600（仅用户可读写）
- `encryption` 支持：`starttls`（587）、`ssl`（465）、`none`

## 数据流

```
CLI 参数解析 (cli.py)
       │
       ▼
加载配置 (config.py)
       │
       ▼
构建邮件 (message.py)
  ├── 解析 --body / --html / --html-file / stdin
  ├── 构建 MIME 结构
  │   ├── 纯文本 → text/plain
  │   ├── HTML → text/html
  │   └── 两者都有 → multipart/alternative
  ├── 附加文件 → multipart/mixed
  │   └── 自动检测 MIME 类型（mimetypes）
  └── 返回 EmailMessage 对象
       │
       ▼
发送邮件 (sender.py)
  ├── Sender 抽象基类
  └── SmtpSender
      ├── starttls → SMTP + starttls()
      ├── ssl → SMTP_SSL
      └── none → SMTP
       │
       ▼
输出结果
```

## Sender 抽象接口

```python
class Sender(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None: ...

class SmtpSender(Sender): ...

# 未来扩展：
# class SendGridSender(Sender): ...
# class SesSender(Sender): ...
```

## 错误处理

- 配置文件不存在 → 提示运行 `emailcli init`
- SMTP 连接/认证失败 → 清晰错误信息，exit code 1
- 附件文件不存在 → 发送前校验，提前报错
- 所有异常在 `cli.py` 层统一捕获，输出友好提示

## 测试策略

| 模块 | 测试内容 |
|------|---------|
| `test_message.py` | 纯文本构建、HTML 构建、text+HTML 混合、附件添加（MIME 类型检测）、从文件读取 HTML |
| `test_config.py` | 配置加载、缺失字段校验、文件不存在处理 |
| `test_sender.py` | Mock smtplib 验证连接逻辑（starttls/ssl/none） |
| `test_cli.py` | CliRunner 测试参数解析和端到端流程 |

## 依赖

### 运行时
- click
- pyyaml

### 开发时
- pytest
