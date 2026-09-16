# Git 上下文节点规范

使用 scripts/context_nodes.py，指定 --root 项目绝对路径。节点只保存根目录两个摘要和 metadata.json；独立 Git 库位于 `.project-brief/store`，不修改项目的 Git 配置、索引、代码分支或提交。多个 Codex 会话不能同时写同一项目的摘要或节点库；遇到并发先协调任务归属。

## 操作

```powershell
python context_nodes.py --root 'D:\your-project' init
python context_nodes.py --root 'D:\your-project' save n001 --message '确认需求和问题证据' --evidence src/main.py
python context_nodes.py --root 'D:\your-project' list
python context_nodes.py --root 'D:\your-project' show n001
python context_nodes.py --root 'D:\your-project' show n001 --file CURRENT_TASK.md
python context_nodes.py --root 'D:\your-project' check n001
python context_nodes.py --root 'D:\your-project' restore n001
python context_nodes.py --root 'D:\your-project' delete n001
```

调用时把 python 和脚本路径替换为实际绝对路径；--evidence 可重复，填写任务证据文件的项目相对路径。仅记录代码 HEAD、已跟踪文件状态和指定证据文件哈希，不保存源码。check 只检测已列证据，不代表全库验证；恢复后必须核验当前源码，不能直接把历史任务状态说成当前事实。

save 前先增量更新摘要，关键证据必须传 --evidence。节点 ID 唯一，名称用 ASCII 字母、数字、连字符和下划线。建议以任务 ID 加时间命名，消息说明阶段和实际验证。阶段完成后自动保存新的上下文节点；不要每条消息保存，也不要每次启动通读历史节点。

restore 只恢复两个摘要，自动先保存 backup 节点；不回退代码。delete 只删除指定节点引用，不删除当前摘要，也不是机密数据的彻底抹除；对象可能仍在 Git 中。删除必须明确节点 ID，不推测用户希望批量清理。可按用户明确给定的保留数量/范围逐项删除；默认保留历史，不自动清理。

## 项目代码节点和回退

用户要求保存代码时，先查看项目 Git 状态和差异，确定应包含的文件；只暂存这些路径，不执行 git add .，不混入用户无关工作。提供真实提交 hash，并将它写进上下文节点。代码未提交时，上下文节点不能恢复该现场。无 Git 的项目仅在用户明确要求管理代码后初始化项目 Git；上下文库本身不需要项目已有 Git。

用户要求查看旧代码时，优先 git show / diff；需要运行旧版本可建立独立 worktree。要求撤销指定已提交改动时优先 git revert，保留历史；遇到冲突按当前任务解决。用户说“退回节点”且没区分上下文和代码时，先展示节点元信息并询问范围，不执行代码回退。

禁止把恢复摘要默认解释成 reset --hard、clean、强推、删除项目或清理未提交代码。删除代码分支/标签前先确认引用、未合并提交与工作树使用情况。此技能不推送远端；外部推送仍需任务已有授权。

## 持久化和维护

项目根目录的摘要可随项目普通 Git 提交以便协作。`.project-brief/store` 是嵌套 Git 库，建议在项目现有 .gitignore 中添加 `.project-brief/`（先阅读、去重，不覆盖原内容）；它不会自动随项目 push。迁移电脑需单独备份该目录，或明确设计远程同步。不要称本地存储为云备份。

摘要文件缺失不代表项目需要重新初始化。维护时先用 `list` 找到首行显示的最近节点（列表按保存时间倒序），并用 `show <ID> --file PROJECT_CONTEXT.md` 或 `show <ID> --file CURRENT_TASK.md` 读取缺失内容；只补缺失文件，不覆盖仍存在且更新的摘要。随后必须根据当前 Git 状态、差异和相关文件校正恢复内容。没有节点时，从仍存在的摘要和当前项目最小证据重建；这属于维护修复，不创建新的初始化流程。

版本化摘要的事实应标注核验日期、来源、当前代码版本、确认/待验证；当前需求必须有任务 ID、验收标准、问题复现及下一步。复杂内容分到项目专门文档，摘要只留索引。节点历史按需查看，默认恢复只读当前摘要。
