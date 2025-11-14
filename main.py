"""
学术论文自动下载器 - 主程序
提供用户友好的命令行界面
"""

import os
import sys
import asyncio
import click
from pathlib import Path
from typing import List, Optional
from loguru import logger
import yaml
from datetime import datetime

from config import LOG_FORMAT, SUPPORTED_PLATFORMS
from paper_parser import PaperListParser
from coordinator import PaperDownloaderCoordinator, SearchConfig, DownloadConfig


# 配置日志
def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """设置日志配置"""
    logger.remove()  # 移除默认处理器
    
    # 控制台日志
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=level,
        colorize=True
    )
    
    # 文件日志
    if log_file:
        logger.add(
            log_file,
            format=LOG_FORMAT,
            level=level,
            rotation="10 MB",
            retention="10 days",
            compression="zip"
        )


# 加载配置文件
def load_config(config_file: str) -> dict:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"配置文件加载成功: {config_file}")
        return config
    except Exception as e:
        logger.warning(f"配置文件加载失败 {config_file}: {e}，使用默认配置")
        return {}


# 验证输入文件
def validate_input_file(input_file: str) -> bool:
    """验证输入文件"""
    if not os.path.exists(input_file):
        logger.error(f"输入文件不存在: {input_file}")
        return False
    
    # 支持的文件格式
    supported_extensions = ['.txt', '.csv', '.xlsx', '.xls', '.json']
    file_ext = Path(input_file).suffix.lower()
    
    if file_ext not in supported_extensions:
        logger.error(f"不支持的文件格式: {file_ext}")
        logger.info(f"支持的格式: {', '.join(supported_extensions)}")
        return False
    
    return True


# 显示欢迎信息
def show_welcome():
    """显示欢迎信息"""
    welcome_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    学术论文自动下载器 Academic Paper Downloader            ║
║                                                                              ║
║  🔍 支持多平台搜索 (Google Scholar, Sci-Hub, arXiv)                         ║
║  📄 自动解析论文列表文件                                                     ║
║  💾 批量下载PDF文件                                                         ║
║  ⚡ 异步处理，高效快速                                                      ║
║  🛡️  智能错误处理和重试机制                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    click.echo(welcome_text)


# 显示完成信息
def show_completion_summary(report: dict):
    """显示完成摘要"""
    summary = report.get('summary', {})
    
    search_success_rate_str = f"{summary.get('search_success_rate', 0):.1%}"
    download_success_rate_str = f"{summary.get('download_success_rate', 0):.1%}"

    completion_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              任务完成！                                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  总论文数: {summary.get('total_papers', 0):\u003c45} ║
║  搜索成功: {summary.get('successful_searches', 0):\u003c45} ║
║  搜索失败: {summary.get('failed_searches', 0):\u003c45} ║
║  下载成功: {summary.get('successful_downloads', 0):\u003c45} ║
║  下载失败: {summary.get('failed_downloads', 0):\u003c45} ║
║  搜索成功率: {search_success_rate_str:\u003c45} ║
║  下载成功率: {download_success_rate_str:\u003c45} ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    click.echo(completion_text)


@click.group(invoke_without_command=True)
@click.option(
    '--input', '-i',
    required=False,
    type=click.Path(exists=True),
    help='输入文件路径（包含论文列表）'
)
@click.option(
    '--output', '-o',
    default='./downloads',
    type=click.Path(),
    help='输出目录路径（默认: ./downloads）'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径（YAML格式）'
)
@click.option(
    '--platforms', '-p',
    default='all',
    help='搜索平台，逗号分隔 (google_scholar,scihub,arxiv,all) 默认: all'
)
@click.option(
    '--max-results', '-n',
    default=5,
    type=int,
    help='每个平台最大搜索结果数（默认: 5）'
)
@click.option(
    '--max-concurrent', '-C',
    default=3,
    type=int,
    help='最大并发下载数（默认: 3）'
)
@click.option(
    '--async/--sync', 'async_mode',
    default=True,
    help='使用异步/同步模式（默认: 异步）'
)
@click.option(
    '--overwrite/--no-overwrite',
    default=False,
    help='覆盖已存在的文件（默认: 不覆盖）'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    help='日志级别（默认: INFO）'
)
@click.option(
    '--log-file',
    type=click.Path(),
    help='日志文件路径'
)
@click.option(
    '--proxy',
    is_flag=True,
    help='使用代理（需要在配置文件中配置）'
)
@click.option(
    '--test-mode',
    is_flag=True,
    help='测试模式（只处理前3篇论文）'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='静默模式（只显示错误信息）'
)
@click.version_option(version='1.0.0', prog_name='Academic Paper Downloader')
@click.pass_context
def main(ctx, input, output, config, platforms, max_results, max_concurrent, async_mode, 
         overwrite, log_level, log_file, proxy, test_mode, quiet):
    """
    学术论文自动下载器
    
    自动从多个学术平台（Google Scholar、Sci-Hub、arXiv）搜索并下载PDF文件。
    
    示例:
    
        \b
        # 基本使用
        python main.py -i papers.txt
        
        \b
        # 指定输出目录和平台
        python main.py -i papers.txt -o ./my_papers -p google_scholar,scihub
        
        \b
        # 使用详细日志和测试模式
        python main.py -i papers.txt -l DEBUG --test-mode
    """
    
    # 设置日志
    if quiet:
        log_level = 'ERROR'
    
    setup_logging(log_level, log_file)
    
    # 显示欢迎信息
    if not quiet:
        show_welcome()
    
    # 若有子命令，主流程不执行
    if ctx.invoked_subcommand is not None:
        return

    # 若无子命令，则要求输入文件
    if not input:
        click.echo('Error: 需要提供 --input/-i 输入文件路径')
        sys.exit(2)
    # 验证输入文件
    if not validate_input_file(input):
        sys.exit(1)
    
    # 加载配置
    config_data = {}
    if config:
        config_data = load_config(config)
    
    # 解析平台参数
    if platforms == 'all':
        selected_platforms = SUPPORTED_PLATFORMS
    else:
        selected_platforms = [p.strip() for p in platforms.split(',')]
        # 验证平台名称
        for platform in selected_platforms:
            if platform not in SUPPORTED_PLATFORMS:
                logger.error(f"不支持的平台: {platform}")
                logger.info(f"支持的平台: {', '.join(SUPPORTED_PLATFORMS)}")
                sys.exit(1)
    
    # 创建搜索和下载配置
    search_config = SearchConfig(
        platforms=selected_platforms,
        max_results_per_platform=max_results,
        use_async=async_mode
    )
    
    download_config = DownloadConfig(
        output_dir=output,
        max_concurrent_downloads=max_concurrent,
        overwrite_existing=overwrite,
        save_metadata=True
    )
    
    # 显示配置信息
    if not quiet:
        click.echo("\n📋 配置信息:")
        click.echo(f"  输入文件: {input}")
        click.echo(f"  输出目录: {output}")
        click.echo(f"  搜索平台: {', '.join(selected_platforms)}")
        click.echo(f"  最大结果数: {max_results}")
        click.echo(f"  并发下载数: {max_concurrent}")
        click.echo(f"  异步模式: {'是' if async_mode else '否'}")
        click.echo(f"  覆盖现有文件: {'是' if overwrite else '否'}")
        click.echo(f"  测试模式: {'是' if test_mode else '否'}")
        click.echo()
    
    # 运行主程序
    try:
        # 创建协调器
        coordinator = PaperDownloaderCoordinator(search_config, download_config)
        
        # 处理论文列表
        if not quiet:
            click.echo("🚀 开始处理论文列表...")
        
        # 运行异步主程序
        report = asyncio.run(run_main(coordinator, input, test_mode))
        
        # 显示完成信息
        if not quiet:
            show_completion_summary(report)
        
        # 保存报告
        report_file = Path(output) / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_report(report, report_file)
        
        if not quiet:
            click.echo(f"📊 详细报告已保存到: {report_file}")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)
    finally:
        # 清理资源
        try:
            coordinator.close()
        except:
            pass


async def run_main(coordinator: PaperDownloaderCoordinator, input_file: str, test_mode: bool):
    """运行主程序"""
    if test_mode:
        # 测试模式：只处理前3篇论文
        logger.info("测试模式：只处理前3篇论文")
        
        # 解析论文列表
        parser = PaperListParser()
        all_papers = parser.parse_file(input_file)
        
        if len(all_papers) > 3:
            test_papers = all_papers[:3]
            # 保存测试文件
            test_file = "test_papers.txt"
            parser.save_papers_list(test_papers, test_file)
            
            try:
                report = await coordinator.process_paper_list(test_file)
            finally:
                # 清理测试文件
                if os.path.exists(test_file):
                    os.remove(test_file)
        else:
            report = await coordinator.process_paper_list(input_file)
    else:
        report = await coordinator.process_paper_list(input_file)
    
    return report


def save_report(report: dict, report_file: Path):
    """保存报告到文件"""
    try:
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"报告已保存到: {report_file}")
    except Exception as e:
        logger.error(f"保存报告失败: {e}")


 


if __name__ == '__main__':
    main()
