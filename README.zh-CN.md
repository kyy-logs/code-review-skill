# code-review-skill

[English](README.md) | 简体中文

**基于证据的代码审查：优先静态分析，使用探针分工，并根据结果执行门禁。**

技能源码位于 [`skills/code-review/`](skills/code-review/)，与宿主工具的安装目录分离。仓库在 [`adapters/`](adapters/) 中提供 Claude Code 和 Codex 的 reviewer 适配器。当前为 beta 候选版本，版本号见 [VERSION](VERSION)。

[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-6B4FBB?style=flat-square)](https://claude.com/claude-code)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-standard-1f6feb?style=flat-square)](https://agentskills.io)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![静态分析优先](https://img.shields.io/badge/review-static--first-2ea44f?style=flat-square)](#能力边界)

许多 AI 审查只给出“这里可能有风险”的判断。这个 skill 生成可核对的审查结果：每条问题都有位置、契约或代码路径依据，以及严重级别；门禁结论由机器可读的 JSON 派生。审查会读取 diff、相关源码、测试和项目规范，无须先构建项目、运行测试或生成覆盖率报告。

审查过程不会修改被审代码。

## 最新动态

### v0.1.0-beta.2（2026-10-31）

#### 新增

- 四探针并行执行：每个探针使用独立代理并写自己的 JSON；宿主没有四个并发槽位时分批执行，或记录串行回退。
- 自动 NEWS 未发布更新和单命令远程 skill 安装。

#### 调整

- 探针派发加入本地搜索范围和后台任务收口约束；`behavior-review` 先从 diff 定位，证据足够时停止。
- `test-coverage` 把有效覆盖率数据交回主执行器；跨探针重复问题暂时保留并计数，后续再评估去重。

#### 修复

- `behavior-review` 补充异步完成、异常和取消收尾路径检查，并区分取消通知与任务实际结束。

[完整更新记录（英文）](NEWS.md)

## 发布状态

`v0.1.0-beta.2` 为测试版本。在 1.0 之前，探针契约、报告结构和门禁行为可能调整。

- **三级评级**：`high`、`medium`、`low`。此前四级版本写入的记录，包括包含 `critical` 值的记录，**不兼容**当前版本；`collect-metrics` 会拒绝这些记录。使用前请重新审查，或显式迁移记录。
- **适用范围**：以静态分析为主，使用四个探针、可选的独立 reviewer，以及从 JSON 派生的报告和门禁。不能替代测试、CI 或人工审查。
- **验证情况**：50 项审查流程、NEWS 与安装离线测试；干净项目中包含 reviewer 和阻塞门禁的端到端验证；额外的探针与 reviewer 冒烟验证。这些属于回归检查，不能据此宣称具备通用召回能力。并发缺陷识别尚未验证。

## 目录

- [最新动态](#最新动态)
- [发布状态](#发布状态)
- [为什么使用这个技能](#为什么使用这个技能)
- [快速开始](#快速开始)
- [工作流程](#工作流程)
- [证据契约](#证据契约)
- [配置](#配置)
- [独立复核](#独立复核)
- [能力边界](#能力边界)
- [验证情况](#验证情况)
- [运行环境](#运行环境)
- [仓库结构](#仓库结构)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

## 为什么使用这个技能

| 特点 | 作用 |
|---|---|
| **优先静态分析** | 新克隆的仓库或不完整检出也能审查。覆盖率数据可选，不作为前置条件。 |
| **证据契约** | 每条问题必须有位置、摘要和可核对的证据。 |
| **四个探针分工** | 分别检查行为、测试、规范和影响，各自产出独立记录。 |
| **独立 reviewer** | 可选的第二个上下文只读取冻结输入和原始发现，不读取预设答案。 |
| **可由脚本检查的门禁** | 计数和阻塞项由 JSON 派生。 |
| **可核对的输出** | 人读报告和 JSON 使用同一份数据，并检查两者是否一致。 |

## 快速开始

### 安装

源码仓库把可移植技能放在 `skills/code-review/`；安装器会把技能和对应宿主的 reviewer 适配器复制到使用方项目。默认不覆盖已有文件。

**在你的项目目录中**执行下面一条命令，同时安装 skill 和 Codex reviewer：

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/kyy-logs/code-review-skill/main/scripts/install-remote.py', timeout=30).read())" --agent codex
```

需要 Python 3.9+ 和 PATH 中可用的 Git；如果你的 Python 命令是 `python3`，替换开头的 `python` 即可。把 `codex` 改成 `claude-code` 或 `both` 可选择其他宿主。入口会把所选 ref 下载到临时目录，调用安装器，结束后清理临时仓库，无须手动克隆或切换目录。

命令末尾可追加 `--dry-run` 预览、`--project "你的项目路径"` 指定其他项目，或 `--ref <分支或标签>` 选择包含安装器的源码版本。远程入口默认使用 `main`；可用 `--ref` 选择其他分支或标签。

如果已经有本地源码仓库：

```bash
git clone --branch main https://github.com/kyy-logs/code-review-skill.git
cd code-review-skill
python scripts/install.py --agent both --project /path/to/your-project
```

也可以使用 shell 包装：

```bash
bash scripts/install --agent codex --project /path/to/your-project
```

宿主目录：

| 宿主 | 技能 | Reviewer 适配器 | 派发方式 |
|---|---|---|---|
| Claude Code | `.claude/skills/code-review/` | `.claude/agents/reviewer.md` | `subagent_type: reviewer` |
| Codex | `.agents/skills/code-review/` | `.codex/agents/reviewer.toml` | 自定义 agent `reviewer`（`agent_type: reviewer`） |

`--agent` 可取 `claude-code`、`codex` 或 `both`。已有文件默认受保护：安装器会列出冲突并以非零状态退出；`--force` 才会替换，并先备份为带时间戳的 `.bak`。`--dry-run` 只打印计划。安装器不会修改 `.codex/config.toml` 或其他 agent 配置。

`npx -y skills add ... --agent codex --yes` 只安装技能，不安装 reviewer 适配器；需要独立 reviewer 时使用上面的安装器。Node.js 22.20+ 仅用于这个可选的 `npx` 路径。

其他宿主需要把 `skills/code-review/` 安装到其技能目录，并提供独立上下文机制；本仓库只提供 Claude Code 和 Codex 适配器。

完整工作流需要同时安装技能和适配器：只安装技能不会注册独立 reviewer。先安装[运行环境](#运行环境)中列出的依赖。如果 Python 无法导入 PyYAML，请在技能使用的解释器中执行 `python -m pip install PyYAML`；也可以通过 `CODE_REVIEW_PYTHON` 指定其他解释器。

### 运行

在 Claude Code 中提出请求：

```text
帮我 review 这次改动
```

也可以直接调用：

```text
/code-review
```

审查固定提交区间：

```text
使用 code-review 审查提交 abc123..def456
```

支持两种模式：

- `worktree`：审查相对于当前 `HEAD` 的暂存、未暂存和未跟踪改动。
- `commits`：审查固定的 `base..head` 提交区间。

### 查看结果

```text
docs/work/active/{slug}/
├── code-review.md      # 人读报告
├── reviewer.json       # 独立 reviewer 裁决（可选）
└── probes/
    ├── behavior-review.json
    ├── test-coverage.json
    ├── repo-guard.json
    └── impact-analysis.json
```

## 工作流程

```text
确定范围 ──► 探针检查 ──► 同步 ──► 独立复核（可选） ──► 对账 ──► 报告 ──► 门禁
```

1. **确定范围**：选择 `worktree` 或 `commits`，将 base 和 head 记录为 commit ID。
2. **探针检查**：派发四个独立代理，使用同一份范围和 diff，各自写自己的探针 JSON。宿主槽位不足时分批执行；没有代理能力时记录串行回退。跨探针重复问题暂时保留并计数，实际提速和 token 节省尚未验证。
3. **同步**：使用 `collect-metrics` 校验探针 JSON 并计算数量。
4. **独立复核（可选）**：仅在 `review-mode` 返回 `run` 时派发 reviewer。
5. **对账**：high 问题需要关闭，或由复核明确驳回。
6. **报告**：从 JSON 生成人读报告的事实区，再校验展示内容。
7. **门禁**：必需探针失败、存在未处理的 high 问题时，阻塞合并。

### 四个探针

| 探针 | 是否必需 | 回答的问题 |
|---|---|---|
| `behavior-review` | 是 | 改动后的行为是否符合实际契约和实现路径？ |
| `test-coverage` | 是 | 测试是否有效；有覆盖率数据时，是否核对增量覆盖？ |
| `repo-guard` | 是 | 改动是否违反仓库或项目规范？ |
| `impact-analysis` | 否 | 哪些调用方受影响，哪些契约变化，对性能和架构有什么影响？ |

各探针保持明确职责：`behavior-review` 不负责一般格式检查，`repo-guard` 不承担通用行为缺陷扫描。

## 证据契约

每条问题包含：

| 字段 | 含义 |
|---|---|
| `location` | `path:line`；若使用文件级位置，需要说明原因 |
| `summary` | 明确描述问题 |
| `evidence` | 契约、代码路径、测试输出或规则 ID |
| `severity` | `high` / `medium` / `low` |
| `status` | `open` / `reconciled` / `wontfix` / `false-positive` |

high 问题必须引用实际方法签名及违反的契约，或给出具体代码路径。尚未核实证据的推测，最高为 `medium`。

## 配置

`references/probes.yaml` 管理探针注册和 reviewer 策略：

```yaml
reviewer:
  mode: auto        # auto | always | never
  skip_when:
    - no_findings
    - only_docs
  policy: strict    # strict | advisory
```

项目规范可以放在 `.code-review/rules/` 中，也可以通过 `CODE_REVIEW_RULES_DIR` 指定：

```bash
export CODE_REVIEW_RULES_DIR=/path/to/rules
```

项目规则包会**替换**内置规则包，两者不会合并。

## 独立复核

`skills/code-review/references/reviewer.md` 是与宿主无关的 reviewer 指令。`adapters/claude-code/reviewer.md` 是 Claude Code 适配器（安装到 `.claude/agents/reviewer.md`）；`adapters/codex/reviewer.toml` 是 Codex 自定义 agent 定义（安装到 `.codex/agents/reviewer.toml`）。两个适配器只负责宿主路由，都指回同一份 reviewer 指令。

reviewer 读取冻结的技能、案例输入和原始探针结果，不读取参考评论、预期答案或历史报告。宿主无法提供全新上下文时，需要记录这一限制，不得编造复核裁决。

## 能力边界

- 不能替代测试、CI 或人工审查。
- 没有发现问题，不代表改动一定正确。
- 不负责生成覆盖率；提供数据时才使用覆盖率数据。
- 不负责自动修复，不修改被审代码。

## 验证情况

<details>
<summary>11 个历史 Java 案例回归（2026-10-29）</summary>

- 基线为 `494a39bb`，当时尚未将 `behavior-review` 拆为独立探针。本快照验证共享的问题记录和门禁契约，不代表已验证四探针拆分。
- 11/11 案例完成；关闭 reviewer；采用静态审查。
- 原始行为目标命中 5/5；纳入另外两个独立确认的边界缺陷后，应报目标合计命中 5/7。
- 正常与修复对照 4/4 通过，未发生错误阻塞。
- 存在两项确认漏报：解析器的合法输入格式，以及命令渲染中的 JSON 表示往返转换。
- 原始发现 33 条：8 high、20 medium、5 low；确认误报 0 条，但仍有未验证项，不能据此认定误报率为零。
- 未执行完整合并门禁。

这些案例实际覆盖的风险：

| 风险维度 | 对应案例 | 实际结果 |
|---|---|---|
| 资源生命周期 | DBeaver | 发现复制完成后未关闭输入流，命中确认目标。 |
| 执行逻辑 | Kestra、Keycloak 指南 | 发现 Kestra 重复组装解释器和命令，命中确认目标。另报告 Keycloak 的 switch 落穿，下游影响仅获部分支持。 |
| 输入边界与值处理 | Lang-1、Spring AI Alibaba | 发现十六进制溢出处理和空白字符串哨兵问题，命中确认目标。前导零导致返回类型变化的问题仍有契约争议，原评级偏高。 |
| 权限与数据范围 | Keycloak 组权限（m01）、Elasticsearch | 发现把授权资源 ID 当作组 ID，命中确认目标。非默认文件系统绕过权限检查的候选问题，仍需威胁模型与可利用性证据。 |
| API 兼容性 | Kestra | 识别公共 SPI 返回类型变化及新增抽象方法，兼容性破坏有依据；未统计实际受影响的外部插件。 |
| 缓存与状态一致性 | Keycloak 登录缓存（m02） | 报告组织包装后的模型影响缓存失效判断的风险，运行时后果尚未验证。 |
| 性能与重复工作 | Elasticsearch、Kestra、Keycloak 登录缓存 | 报告日志开销、重复渲染或下载、额外查询；未通过基准测试衡量性能影响。 |
| 测试质量与回归保护 | DBeaver、Keycloak、Kestra | 识别关键分支缺少测试、测试绕过变更后的生产入口、测试清理错误，以及缓存失效分支未被覆盖。 |

两项确认漏报分别是：Keycloak 的合法 `tileVisible = "false"` 写法绕过校验；Kestra 的 JSON 渲染与解析往返转换损坏含引号、反斜杠或换行的命令值。

四个对照检查是否误报：Lang-1 修复、正常分页、正常标签规范化，以及不应被误判为递归的合法登录缓存委托路径。某个对照通过，不代表其全部改动都没有缺陷。

评测工具和原始报告不放入发布仓库。这份快照只说明历史回归结果，不能据此宣称通用召回能力。

</details>

## 运行环境

- 支持 Agent Skills 的 Claude Code，或支持自定义 agent 的 Codex。
- Bash、Git、awk、grep、sed。
- Python 3.9+；安装仅使用标准库。运行审查脚本时还需要 PyYAML，用于报告解析和指标处理。
- Node.js 22.20+ 仅在使用可选的 `npx skills` 只装技能快捷方式时需要。

## 仓库结构

```text
code-review-skill/
├── README.md
├── README.zh-CN.md
├── NEWS.md
├── LICENSE
├── VERSION
├── .github/workflows/
│   ├── news-update.yml
│   └── sync-news.yml
├── scripts/
│   ├── install
│   ├── install.py
│   ├── install-remote.py
│   ├── news-update.py
│   └── sync-news.py
├── skills/
│   └── code-review/
│       ├── SKILL.md
│       ├── assets/code-review.md
│       ├── references/
│       │   ├── probes.yaml
│       │   ├── output-schema.md
│       │   ├── reviewer.md
│       │   ├── probes/
│       │   └── rules/
│       └── scripts/
│           ├── review-mode
│           ├── collect-metrics
│           ├── lib-metrics
│           ├── rule-grep
│           └── sync-results.py
├── adapters/
│   ├── claude-code/reviewer.md
│   └── codex/reviewer.toml
└── tests/
```

## 参与贡献

欢迎提交 issue 和 pull request。涉及行为变更时，请说明：

- 审查目标：仓库及 base/head。
- 预期发现的问题或门禁结论。
- 实际发现的问题或门禁结论。
- 能区分预期与实际的证据。

修改探针或输出结构时，需要同时更新探针文档、输出契约和受影响的脚本。

使用 `python -m unittest discover -s tests -v` 运行离线测试。通过 `CODE_REVIEW_TEST_BASH` 指定 Bash 可执行文件后，还会运行 Shell 和安装检查，详见 [tests/README.md（英文）](tests/README.md)。这些检查不调用模型，也不能证明缺陷召回能力。

在 [NEWS.md（英文）](NEWS.md) 中记录面向用户的变化，最新版本放在最前面。`## Unreleased` 块由最近 tag 以来的提交自动生成，并由 `UNRELEASED:START` / `UNRELEASED:END` 标记；push 到 `main` 时只替换该块，已发布段落保持不变。README 预览使用最新正式版本，不展示 Unreleased。建议使用 Conventional Commits（`feat`、`fix`、`perf`、`refactor`）；`docs`、`chore`、`test`、`ci`、`build` 会跳过，旧式提交按关键词兜底。也可以在本地执行 `python scripts/news-update.py`，加上 `--check` 只检查块是否过期。

推送 NEWS 或同步工具的改动后，流水线会自动更新英文 README 的最新动态区域；其余内容正常编辑。也可以在本地执行 `python scripts/sync-news.py`，加上 `--check` 时只检查是否需要更新，不修改文件。自动提交使用内置 `GITHUB_TOKEN`，分支规则需要允许该 bot 推送。

修改英文文档时，请同步更新本中文版。中文翻译及最新动态摘要目前由人工维护。

## 许可证

本仓库使用 [MIT 许可证](LICENSE)。
