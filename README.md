# Project Brief

一个面向 Codex 的跨项目工具仓库，包含两个彼此独立的部分：

- `project-brief` Skill：让新窗口通过短摘要和证据索引快速恢复项目状态，并使用独立 Git 节点保存、查看、恢复和删除上下文快照。
- `tools/token-observer`：在本地按任务、项目和时间查看 Codex token 消耗，并显示 Codex 侧边栏中的任务名称。

## 解决的问题

- 新会话无需重新通读整个项目。
- 项目目标、验收标准、当前任务和下一步持续保存。
- 已开发很久的项目也能增量接入，不要求从头整理。
- 历史上下文按需查看，避免每次加载全部记录。
- 上下文恢复与代码回退分开，防止误操作项目代码。

## 安装

安装到用户范围，供多个项目使用：

```text
C:\Users\<你的用户名>\.agents\skills\project-brief
```

也可以只安装到一个项目：

```text
<项目根目录>\.agents\skills\project-brief
```

把仓库根目录中的 `SKILL.md`、`references`、`scripts` 和本 README 复制到上述目录。`tools` 是独立工具，不需要放入技能目录。Codex 通常会自动发现技能；若未出现，重启 Codex。

## 初始化项目

在项目根目录打开 Codex，然后输入：

```text
$project-brief 初始化
```

技能会先识别新项目或已有项目，再逐步询问缺失信息。每次提供具体方案，也允许自由输入。初始化只要求明确项目目标和验收标准；问题在实际出现后才记录。

初始化建立：

- `PROJECT_CONTEXT.md`：稳定的项目目标、模块入口、约束和证据来源。
- `CURRENT_TASK.md`：当前需求、验收标准、进展和下一步。
- `.project-brief/store`：本地独立 Git 上下文节点库。

建议把 `.project-brief/` 加入项目的 `.gitignore`。两个 Markdown 摘要可以提交到项目 Git，节点库默认只保存在本机。

## 新窗口恢复

只恢复并汇报项目状态：

```text
$project-brief 继续
```

恢复后直接执行新要求：

```text
$project-brief 继续，帮我修复登录后的白屏问题
```

后一种用法会先核验上下文，再在同一轮处理要求。新要求优先于历史任务；信息充分时不重复确认。

## 常用指令

| 目的 | 指令 |
| --- | --- |
| 初始化 | `$project-brief 初始化` |
| 恢复状态 | `$project-brief 继续` |
| 恢复后工作 | `$project-brief 继续，<你的要求>` |
| 保存阶段 | `$project-brief 保存` |
| 列出节点 | `$project-brief 节点` |
| 查看节点 | `$project-brief 查看 n001` |
| 检查证据变化 | `$project-brief 检查 n001` |
| 恢复上下文 | `$project-brief 恢复 n001` |
| 删除节点 | `$project-brief 删除 n001` |

## Git 节点边界

上下文节点保存两个摘要、项目代码 HEAD、已跟踪文件状态和指定证据文件的哈希。它默认不保存源码，也不会执行 `reset --hard`、`clean` 或强制推送。

- 恢复上下文前自动创建 backup 节点。
- 恢复上下文不会回退项目代码。
- 查看旧代码优先使用 `git show`、`git diff` 或独立 worktree。
- 撤销已提交代码优先使用 `git revert`，保留历史。
- 删除节点只删除节点引用，不改变当前摘要；Git 对象可能仍然存在。

节点管理脚本可独立调用，详细命令见 [references/git-nodes.md](references/git-nodes.md)。

## 文件结构

```text
project-brief/
├── SKILL.md
├── README.md
├── references/
│   ├── context-template.md
│   ├── initialization.md
│   └── git-nodes.md
├── scripts/
│   └── context_nodes.py
└── tools/
    └── token-observer/
        ├── README.md
        ├── server.py
        └── static/index.html
```

## 设计原则

- 摘要用于导航，源码和测试才是当前事实。
- 只核验与本轮任务相关的文件，避免全库重复读取。
- 明确区分已确认事实、资料推断和待验证假设。
- 用户本轮指令优先，历史记录不构成新的操作授权。
- 有实质进展后才保存节点，不按消息频率制造历史噪声。

## Token 可视化

Token 可视化不参与 Skill 的上下文恢复，也不会增加项目摘要。它作为仓库中的独立工具维护，使用方法见 [tools/token-observer/README.md](tools/token-observer/README.md)。

在任意电脑克隆仓库后进入该目录并运行：

```powershell
python server.py
```

工具会自动寻找当前用户的 Codex 数据目录。页面中的任务名称来自当地 Codex 的 `session_index.jsonl`，因此不依赖本电脑写死的名称或路径。
