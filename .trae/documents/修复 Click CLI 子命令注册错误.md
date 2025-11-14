## 问题原因

* `main` 使用 `@click.command()`，因此是 `click.Command`，不支持 `add_command`；只能在 `click.Group` 上注册子命令

* 错误触发点：`main.py:387` 调用 `main.add_command(create_sample)`；根因在 `main.py:116`

## 修复方案

* 将 `@click.command()` 替换为 `@click.group(invoke_without_command=True)`，保留所有现有 `@click.option(...)`

* 在布尔选项 `--async/--sync` 上显式指定参数名为 `async_mode`：`@click.option('--async/--sync', 'async_mode', default=True, help=...)`，避免后续因关键字 `async`（保留字）导致的参数绑定错误

* 保持现有的 `main.add_command(create_sample)`；或可选改为 `@main.command('create-sample')` 直接装饰绑定（两者等价），本次采用保持现状最小改动

## 验证步骤

* 运行 `python main.py --help`，确认出现子命令 `create-sample`

* 运行 `python main.py create-sample -o sample_papers.txt -c 3`，确认示例文件生成成功

* 运行主流程：`python main.py -i papers.txt -o ./downloads -p all -n 5 -C 3 --async --no-overwrite -l INFO`，确认主功能不受影响

* 切换同步模式验证：`python main.py -i papers.txt --sync`，确认 `async_mode=False` 生效

## 预期影响

* 修复子命令注册错误，主命令行为保持不变；支持在无子命令时直接执行主流程，在有子命令时仅执行对应子命令

## 后续建议（可选）

* 若未来添加更多子命令，统一改为以 `@main.command()` 装饰的方式组织，提升可读性与一致性

