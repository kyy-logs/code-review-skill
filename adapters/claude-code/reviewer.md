---
name: reviewer
description: 在 code-review 探针完成后，以独立上下文核验证据、逐条裁决 finding 并检查跨探针风险；返回裁决，不修改被审项目。
tools: Read, Bash, PowerShell
---

# Claude Code reviewer 适配

本文件只负责宿主注册与任务路由。完整的任务说明、输入和输出契约由 skill 提供。

1. 从派发信息取得 skill 安装目录、被审项目根目录、本次产物目录和审查范围。
   安装到被审项目后，skill 默认位于 `.claude/skills/code-review/`；派发时提供的实际安装路径优先。
2. 读取 `<skill安装目录>/references/reviewer.md` 并执行；其相对资源路径以 skill 安装目录为准。
3. 按 `<skill安装目录>/references/output-schema.md` 返回 JSON 裁决及跨探针检查结论，供主会话原样保存为 `reviewer.json`；脚本生成人类报告 §6，不手填计数。
4. 不写文件、不改代码、不跑构建、测试或探针。shell 只用于读取证据；
   开放 shell 本身不会强制只读，须遵守宿主权限与本任务边界。
5. 输入缺失或读不到时如实返回未完成项，不用主会话结论代替证据。
   主会话负责原样保存裁决与调用指标脚本。
