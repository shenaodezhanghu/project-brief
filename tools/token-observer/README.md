# Codex Token Observer

本地只读的 Codex token 可视化工具。它扫描本机 Codex 会话日志，按主会话、子代理运行、项目和时间展示 token 使用情况，不读取或展示聊天正文。

工具只使用 Python 标准库，不需要安装第三方依赖，适合随仓库复制到其他 Windows、macOS 或 Linux 电脑使用。

## 启动

```powershell
python server.py
```

然后打开 `http://127.0.0.1:4176/`。可用 `--port` 指定端口，或用 `--sessions-dir` 指定 Codex `sessions` 目录：

```powershell
python server.py --port 4180 --sessions-dir 'C:\Users\you\.codex\sessions'
```

页面每次刷新都会重新读取日志。工具不修改日志，也不会上传数据。

默认读取当前用户的 `~/.codex/sessions`；如果设置了 `CODEX_HOME`，则读取 `$CODEX_HOME/sessions`。因此换电脑后通常无需修改脚本。

主会话名称来自当地 Codex 数据目录中的 `session_index.jsonl`，使用最新的侧边栏名称，并链接到对应的 `codex://threads/<ID>`。子代理显示父任务名称；无法找到名称时才回退到项目名和缩短 ID。任务名称不会写死在脚本中，例如本机的“制作skill”来自本机索引，换电脑后会显示那台电脑保存的实际名称。

## 跨电脑使用

1. 在目标电脑安装 Python 3.10 或更高版本。
2. 克隆本仓库并进入 `tools/token-observer`。
3. 运行 `python server.py`。
4. 打开 `http://127.0.0.1:4176/`。

如果 Codex 数据不在默认目录，使用：

```powershell
python server.py --sessions-dir 'D:\path\to\.codex\sessions'
```

## 指标

- **总 token**：日志报告的 `total_tokens` 增量。
- **输入**：`input_tokens`，其中已经包含缓存输入。
- **缓存输入**：`cached_input_tokens`。
- **非缓存输入**：输入减缓存输入。
- **输出**：`output_tokens`。推理输出单独显示，但不再加到总 token 中。

同一会话可能跨多个日志文件；工具按会话 ID 合并，并根据累计计数计算时间增量。若计数器重新开始，则将该点视为新的累计区段。数据来自 Codex 本地内部日志格式，版本变化可能导致字段暂时不可用；缺失值不会当作零补造。

主会话是用户在 Codex 中看到的任务；子代理运行是主会话内部启动的独立执行记录。二者都消耗 token，因此总量默认包含两者，但页面会分别计数并支持按类型筛选。

## 对比使用与未使用 Skill

Codex 日志没有可靠的“是否调用某个 Skill”字段，因此看板不猜测。请在会话表的“实验标签”列给主会话选择“使用 Skill”或“未使用 Skill”。标签保存在当前浏览器的 `localStorage`，不会写入 Codex 日志或上传。

对比卡片按主会话计算平均总 token，并把该主会话的子代理消耗计入同一任务。为了让结果有意义，请给两组安排目标、规模和验收标准接近的任务；每组至少 3–5 个任务，避免用一个简单任务和一个复杂任务直接比较。

## 隐私

接口只返回会话 ID、时间、项目目录、来源类型和 token 数字。网页与服务均绑定 `127.0.0.1`。页面中会显示本机项目路径，因此不要将页面或导出的截图公开分享。
