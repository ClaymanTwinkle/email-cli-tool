# email-cli-tool

> 一个简洁的命令行邮件发送工具，支持纯文本、HTML 和文件附件。
>
> [English](README.md)

## 功能特性

- 发送纯文本 / HTML / 混合格式邮件
- 携带多个文件和图片附件
- 支持多收件人
- SMTP 直连（支持 SSL / STARTTLS）
- 交互式配置向导
- 从 stdin 读取正文内容

## 安装

```bash
# 从 PyPI 安装
pip install email-cli-tool

# 或使用 uv
uv tool install email-cli-tool
```

## 快速开始

### 1. 初始化配置

```bash
emailcli init
```

按提示输入 SMTP 信息。以网易 163 邮箱为例：

| 配置项 | 值 |
|--------|-----|
| From address | `yourname@163.com` |
| SMTP host | `smtp.163.com` |
| SMTP port | `465` |
| SMTP username | `yourname@163.com` |
| SMTP password | 授权码（非登录密码） |
| Encryption | `ssl` |

### 2. 发送邮件

```bash
# 纯文本
emailcli send --to user@example.com --subject "你好" --body "Hello World"

# HTML 格式
emailcli send --to user@example.com --subject "通知" \
  --html "<h1>标题</h1><p>正文内容</p>"

# 携带附件
emailcli send --to user@example.com --subject "报告" \
  --body "请查收附件" \
  --attach report.pdf \
  --attach photo.png

# 多个收件人
emailcli send \
  --to a@example.com \
  --to b@example.com \
  --subject "群发" --body "大家好"

# 从文件读取 HTML 正文
emailcli send --to user@example.com --subject "Newsletter" \
  --html-file template.html

# 从 stdin 读取正文
echo "邮件内容" | emailcli send \
  --to user@example.com --subject "Piped" --body -
```

## 命令参考

### `emailcli send`

| 参数 | 必填 | 可重复 | 说明 |
|------|:----:|:------:|------|
| `--to` | ✅ | ✅ | 收件人邮箱 |
| `--subject` | ✅ | | 邮件主题 |
| `--body` | | | 纯文本正文，`-` 从 stdin 读取 |
| `--html` | | | HTML 正文（与 `--html-file` 互斥） |
| `--html-file` | | | 从文件读取 HTML（与 `--html` 互斥） |
| `--attach` | | ✅ | 附件文件路径 |
| `--from` | | | 覆盖配置中的发件人地址 |

> `--body` 和 `--html` / `--html-file` 至少提供一个。

### `emailcli init`

交互式创建配置文件 `~/.emailcli/config.yaml`。

### `emailcli config show`

查看当前配置（密码已脱敏）。

## 配置文件

路径：`~/.emailcli/config.yaml`

```yaml
from: yourname@163.com
smtp:
  host: smtp.163.com
  port: 465
  username: yourname@163.com
  password: your-auth-code
  encryption: ssl  # ssl | starttls | none
```

## 开发

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest -v

# 本地运行
uv run emailcli --help
```

## License

MIT
