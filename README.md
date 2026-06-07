# prompt-asset-inventory

`prompt-asset-inventory` 是一个离线 CLI，用来盘点仓库里散落的 prompt 资产。它面向使用 Codex、Claude Code、ChatGPT、Cursor 或自研 agent 的团队，帮助你找到 system prompts、few-shot examples、eval prompts、agent instructions、tool descriptions，并检查这些资产是否缺少 owner、purpose、version、privacy、source、citations 等治理信息。

项目分类：AI / Developer tooling

## 真实场景

很多团队的 prompt 资产不会只存在一个地方。它们可能写在 Markdown 说明里、Python/JS 常量里、JSON/YAML eval fixtures 里、工具 schema 描述里，或者藏在给 agent 的 rules 文件中。上线前、审计前、迁移模型前、清理隐私风险前，团队需要一个资产台账：

- 这段 prompt 谁负责？
- 它用于什么产品或流程？
- 当前版本是什么？
- 是否说明了隐私边界？
- 来源和引用是否可追溯？
- 是否包含疑似 PII、API key、token、password、private key？

本工具不会调用外部网络，也不会上传内容。它只读取你指定目录下的文本文件，并在本地输出 Markdown、JSON 或 CSV。

## 功能

- 扫描 Markdown、TXT、JSON、YAML、Python、JavaScript、TypeScript 文件。
- 识别 prompt-like blocks：
  - system/user/assistant/developer role messages
  - few-shot examples
  - agent instructions
  - tool schema / function descriptions
  - eval cases / rubrics / golden expected outputs
- 读取可选 `inventory-rules.json`。
- 输出 Markdown、JSON、CSV 资产台账。
- 检查缺失字段：`owner`、`purpose`、`version`、`privacy`、`source`、`citations`。
- 检测疑似 PII 和 secret。
- 支持 `--check`，适合 CI 失败退出。
- Python 标准库运行，无运行时第三方依赖。

## 安装

开发安装：

```bash
python -m pip install -e .
```

直接从源码运行（未安装时）：

```bash
PYTHONPATH=src python -m prompt_asset_inventory --help
```

PowerShell：

```bash
$env:PYTHONPATH="src"; python -m prompt_asset_inventory --help
```

安装后运行：

```bash
prompt-asset-inventory --help
```

## 快速开始

扫描当前仓库并输出 Markdown：

```bash
python -m prompt_asset_inventory . --format markdown
```

输出 JSON：

```bash
python -m prompt_asset_inventory . --format json --output prompt-assets.json
```

输出 CSV：

```bash
python -m prompt_asset_inventory . --format csv --output prompt-assets.csv
```

CI 检查模式：

```bash
python -m prompt_asset_inventory . --rules examples/inventory-rules.json --check
```

当存在 warning/error findings 时，`--check` 返回退出码 `1`。运行错误返回 `2`。无阻断 finding 返回 `0`。

## 输入格式

工具通过启发式扫描文件内容。你可以用轻量 metadata 行标注资产：

```markdown
## Support System Prompt
owner: support-platform
purpose: classify customer support tickets
version: 2026-06-01
privacy: no customer identifiers in prompt body
source: internal prompt registry
citations: runbook/support-triage.md

System prompt:
You are a support triage assistant...
```

也支持代码和结构化数据：

```python
SYSTEM_PROMPT = """
owner: search-team
purpose: answer repository search questions
version: 1.4.0
privacy: repository text only
source: prompts/search.py
citations: evals/search.yaml

System prompt: You are a precise code search assistant.
"""
```

```json
{
  "eval_case": "tool schema should reject malformed parameters",
  "owner": "platform-quality",
  "purpose": "validate tool schema prompt behavior",
  "version": "2026.06",
  "privacy": "synthetic only",
  "source": "evals/tool-schema.json",
  "citations": "qa-plan.md",
  "messages": [
    {"role": "system", "content": "Follow the tool schema exactly."}
  ]
}
```

## Rules JSON

`inventory-rules.json` 可选。示例：

```json
{
  "required_fields": ["owner", "purpose", "version", "privacy", "source", "citations"],
  "ignore_paths": ["dist/**", "node_modules/**", ".git/**"],
  "max_snippet_chars": 240,
  "severity": {
    "missing_required": "warning",
    "pii": "warning",
    "secret": "error"
  },
  "path_defaults": [
    {
      "path": "examples/prompts/**",
      "metadata": {
        "owner": "ai-platform",
        "source": "examples/prompts"
      }
    }
  ]
}
```

`path_defaults` 会为匹配路径补默认 metadata，文件里的 metadata 会覆盖默认值。

## 输出格式

### Markdown

Markdown 输出包含概览表和每个资产的详情，适合人工审阅或作为审计附件。

### JSON

JSON 输出适合导入内部系统：

```json
{
  "root": "/repo",
  "files_scanned": 12,
  "files_skipped": 0,
  "asset_count": 3,
  "finding_count": 4,
  "assets": []
}
```

### CSV

CSV 输出适合电子表格或 BI 工具，包含 `id`、`path`、`line_start`、`type`、metadata、finding codes 和 snippet。

## 隐私与安全边界

- 本工具离线运行，不发送网络请求。
- 不读取你未指定目录以外的文件。
- 不需要 GitHub token，也不会推送 GitHub。
- 疑似 PII/secret 检测是启发式，不等同于完整 DLP 或 secret scanning。
- 输出报告会包含资产 snippet。处理敏感仓库时，请把输出文件当作敏感材料管理。
- 默认不会修改被扫描仓库，只生成 stdout 或你指定的输出文件。

## GitHub Actions CI

仓库内提供 `.github/workflows/ci.yml`。你也可以在自己的项目里加入：

```yaml
name: Prompt Asset Inventory
on: [push, pull_request]
jobs:
  prompt-assets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e .
      - run: python -m prompt_asset_inventory . --rules examples/inventory-rules.json --check
```

## 开发与测试

```bash
python -m unittest discover -s tests -v
```

## English

`prompt-asset-inventory` is an offline command-line inventory scanner for prompt assets in AI and developer tooling repositories. It is designed for teams using Codex, Claude Code, ChatGPT, Cursor, or internal agents whose repositories contain scattered system prompts, few-shot examples, eval prompts, agent instructions, and tool descriptions.

### What It Solves

Prompt assets often live in Markdown docs, Python or JavaScript constants, JSON/YAML eval cases, tool schema files, and agent instruction files. Before audits, model migrations, CI gates, or privacy reviews, teams need to know:

- who owns each prompt asset,
- why it exists,
- which version is current,
- whether privacy expectations are documented,
- where the prompt came from,
- which citations or source materials support it,
- whether it appears to include PII or credentials.

The tool runs locally and does not use the network.

### Install And Run

```bash
python -m pip install -e .
python -m prompt_asset_inventory . --format markdown
python -m prompt_asset_inventory . --format json --output prompt-assets.json
python -m prompt_asset_inventory . --format csv --output prompt-assets.csv
python -m prompt_asset_inventory . --rules examples/inventory-rules.json --check
```

### Supported Inputs

The scanner supports Markdown, TXT, JSON, YAML, Python, JavaScript, TypeScript, JSX, and TSX files. It detects prompt-like blocks using local heuristics for role messages, few-shot examples, agent instructions, tool schemas, eval cases, and prompt variables.

Add lightweight metadata near the prompt:

```text
owner: ai-platform
purpose: classify support tickets
version: 1.0.0
privacy: no customer identifiers
source: internal registry
citations: support-runbook.md
```

### Rules

An optional rules JSON file can configure required fields, ignored paths, snippet length, severity levels, and path-based metadata defaults. See `examples/inventory-rules.json`.

### Outputs

The tool emits Markdown, JSON, or CSV. Markdown is useful for review, JSON for automation, and CSV for spreadsheets or asset governance workflows.

### Safety Boundary

The scanner is offline, uses no runtime third-party dependencies, does not require tokens, does not push to GitHub, and does not modify the scanned repository. PII and secret detection is heuristic and should complement, not replace, dedicated security tooling.

## License

MIT. See `LICENSE`.
