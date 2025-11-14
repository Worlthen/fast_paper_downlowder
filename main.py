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








@click.command()
@click.option(
    '--input', '-i',
    required=True,
    type=click.Path(exists=True, readable=True, dir_okay=False),
    help='包含论文标题的输入文件路径 (.txt, .csv, .xlsx, .xls, .json)。'
)
@click.option(
    '--output', '-o',
    default='./downloads',
    type=click.Path(file_okay=False, resolve_path=True),
    help='下载论文的输出目录。'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    help='设置日志记录级别。'
)
@click.option(
    '--log-file',
    type=click.Path(dir_okay=False),
    help='将日志输出到指定文件。'
)
@click.option(
    '--proxy',
    is_flag=True,
    help='启用在 config.yaml 中配置的网络代理。'
)
@click.version_option(version='1.0.0', prog_name='Fast Paper Downloader')
def main(input: str, output: str, log_level: str, log_file: Optional[str], proxy: bool):
    """
    一个根据标题自动下载论文的命令行工具。
    """
    # 1. 配置日志
    setup_logging(log_level, log_file)
    logger.info("Fast Paper Downloader 启动")

    # 2. 验证输入文件
    if not validate_input_file(input):
        sys.exit(1)

    # 3. 加载并配置代理
    if proxy:
        # 注意：配置文件路径是硬编码的，以简化操作
        config = load_config('config.yaml')
        if 'proxy' in config and config.get('proxy'):
            http_proxy = config['proxy'].get('http')
            https_proxy = config['proxy'].get('https')
            
            if http_proxy:
                os.environ['HTTP_PROXY'] = http_proxy
            if https_proxy:
                os.environ['HTTPS_PROXY'] = https_proxy

            if http_proxy or https_proxy:
                logger.info("已启用网络代理。")
            else:
                logger.warning("代理标志已设置，但在 config.yaml 中未找到有效的 http/https 代理配置。")
        else:
            logger.warning("代理标志已设置，但在 config.yaml 中未找到代理配置。")

    # 4. 创建搜索和下载配置（使用硬编码的简化值）
    search_config = SearchConfig(
        platforms=SUPPORTED_PLATFORMS,  # 使用所有支持的平台
        max_results_per_platform=5,     # 每个平台最多5个结果
        use_async=True                  # 始终使用异步模式
    )
    
    download_config = DownloadConfig(
        output_dir=output,
        max_concurrent_downloads=5,     # 硬编码并发数
        overwrite_existing=False,       # 不覆盖现有文件
        save_metadata=True              # 保存元数据
    )

    # 5. 初始化下载协调器
    coordinator = PaperDownloaderCoordinator(search_config, download_config)
    
    logger.info(f"输入文件: {input}")
    logger.info(f"输出目录: {os.path.abspath(output)}")
    logger.info("🚀 开始处理论文列表...")

    # 6. 运行主下载程序
    try:
        report = asyncio.run(coordinator.process_paper_list(input))
        
        # 7. 显示完成摘要
        summary = report.get('summary', {})
        logger.info("=" * 60)
        logger.info("✅ 所有任务已完成！")
        logger.info(
            f"处理结果: 总数={summary.get('total_papers', 0)}, "
            f"搜索成功={summary.get('successful_searches', 0)}, "
            f"下载成功={summary.get('successful_downloads', 0)}"
        )
        logger.info(f"下载的论文已保存到: {os.path.abspath(output)}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("用户中断了程序执行。")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行期间发生意外错误: {e}")
        sys.exit(1)
    finally:
        try:
            coordinator.close()
        except Exception as e:
            logger.debug(f"关闭协调器时发生错误: {e}")








 


if __name__ == '__main__':
    main()
