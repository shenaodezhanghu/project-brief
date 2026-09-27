"""Install or update the Project Brief block in the effective root agent rules."""
import argparse
from pathlib import Path

START = '<!-- project-brief:start -->'
END = '<!-- project-brief:end -->'
BLOCK = """<!-- project-brief:start -->
## Project Brief 自动上下文

本项目使用 `PROJECT_CONTEXT.md` 和 `CURRENT_TASK.md` 保存跨会话上下文。

- 开始任何项目任务时，先读取这两个文件，再按当前任务核验必要源码；摘要不替代代码和测试事实。
- 只要本轮修改了项目文件，就必须在最终回复前根据本轮差异和验证结果增量更新摘要，删除失效状态。用户无需另发“维护”指令。
- 完成一个完整用户需求、可独立验收的改动或实质阶段后，保存 Project Brief Git 上下文节点；细小编辑不单独制造节点。
- 摘要缺失时从最近节点或当前项目最小证据自动修复，不要求重新初始化。
- `$project-brief 维护` 只用于同步用户、其他工具或其他会话造成的外部变化。
- 会话交接只能先建议；未经用户明确确认，不创建新任务或执行完整交接。用户未回应时继续当前工作，自动摘要维护仍照常完成。
<!-- project-brief:end -->"""


def install(root: Path) -> tuple[str, Path]:
    override = root / 'AGENTS.override.md'
    target = override if override.exists() else root / 'AGENTS.md'
    original = target.read_text(encoding='utf-8-sig') if target.exists() else ''
    starts = original.count(START)
    ends = original.count(END)
    if starts != ends or starts > 1:
        raise ValueError(f'{target.name} contains malformed or duplicate project-brief markers')

    if starts == 1:
        left = original.index(START)
        right = original.index(END, left) + len(END)
        updated = original[:left].rstrip() + ('\n\n' if original[:left].strip() else '') + BLOCK
        suffix = original[right:].strip()
        if suffix:
            updated += '\n\n' + suffix
        action = 'updated'
    else:
        updated = original.rstrip()
        if updated:
            updated += '\n\n'
        updated += BLOCK
        action = 'created' if not target.exists() else 'appended'

    target.write_text(updated.rstrip() + '\n', encoding='utf-8', newline='\n')
    return action, target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error('project root must be a directory')
    try:
        action, target = install(root)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{action}: {target}')


if __name__ == '__main__':
    main()
