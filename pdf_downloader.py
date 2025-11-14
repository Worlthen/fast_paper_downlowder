"""
PDF下载管理器
负责管理和协调PDF文件的下载过程
"""

import os
import asyncio
import aiohttp
import aiofiles
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from urllib.parse import urlparse, unquote
from loguru import logger

from config import USER_AGENTS
from paper_parser import PaperInfo


@dataclass
class DownloadTask:
    """下载任务数据结构"""
    paper: PaperInfo
    pdf_url: str
    output_path: str
    platform: str  # 'google_scholar', 'scihub', 'arxiv'
    priority: int = 1
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    status: str = 'pending'  # pending, downloading, completed, failed
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    download_time: Optional[float] = None


@dataclass
class DownloadResult:
    """下载结果数据结构"""
    task: DownloadTask
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    download_time: Optional[float] = None


class PDFDownloader:
    """PDF下载管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_concurrent = self.config.get('max_concurrent', 3)
        self.timeout = self.config.get('timeout', 60)
        self.retry_delay = self.config.get('retry_delay', 5.0)
        self.output_dir = Path(self.config.get('output_dir', './downloads'))
        self.create_output_dir()
        
        # 下载统计
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_size': 0,
            'total_time': 0.0
        }
        
        # 会话管理
        self.session = None
        self.semaphore = None
    
    def create_output_dir(self):
        """创建输出目录"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / 'pdfs').mkdir(exist_ok=True)
        (self.output_dir / 'metadata').mkdir(exist_ok=True)
        (self.output_dir / 'logs').mkdir(exist_ok=True)
    
    def generate_filename(self, paper: PaperInfo, platform: str = 'unknown') -> str:
        """生成文件名"""
        parts = []
        authors_str = paper.get_formatted_authors().strip()
        if authors_str and authors_str.lower() != 'unknown':
            parts.append(authors_str.replace(' ', '_').replace(',', ''))
        if paper.year:
            parts.append(str(paper.year))
        # 清理标题（移除特殊字符，限制长度）
        title = paper.title[:100]
        title = re.sub(r'[^\w\s-]', '', title)
        title = title.replace(' ', '_')
        parts.append(title)
        parts.append(platform)
        filename = "_".join(parts) + ".pdf"
        # 确保文件名安全
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        return filename
    
    def get_file_path(self, paper: PaperInfo, platform: str = 'unknown') -> str:
        """获取完整的文件路径"""
        filename = self.generate_filename(paper, platform)
        return str(self.output_dir / 'pdfs' / filename)
    
    async def create_session(self):
        """创建aiohttp会话"""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.max_concurrent,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'application/pdf,application/octet-stream;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Connection': 'keep-alive'
            }
        )
        
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def close_session(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
    
    async def download_pdf(self, task: DownloadTask) -> DownloadResult:
        """下载单个PDF文件"""
        async with self.semaphore:
            start_time = datetime.now()
            
            try:
                logger.info(f"开始下载: {task.paper.title} (来自 {task.platform})")
                task.status = 'downloading'
                
                # 检查URL是否有效
                if not task.pdf_url or not task.pdf_url.startswith(('http://', 'https://')):
                    raise ValueError(f"无效的PDF URL: {task.pdf_url}")
                
                # 构建请求头（包含合理的 Referer）
                req_headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/pdf,application/octet-stream;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                    'Connection': 'keep-alive',
                    'Referer': self._build_referer(task.pdf_url)
                }

                # 下载文件（首次尝试）
                async with self.session.get(task.pdf_url, headers=req_headers, allow_redirects=True) as response:
                    if response.status != 200:
                        # 对403执行一次重试（更换UA与Referer）
                        if response.status == 403:
                            logger.debug("首次请求被403拒绝，尝试使用备用头部重试")
                            retry_headers = dict(req_headers)
                            retry_headers['User-Agent'] = random.choice(USER_AGENTS)
                            retry_headers['Referer'] = 'https://scholar.google.com/'
                            async with self.session.get(task.pdf_url, headers=retry_headers, allow_redirects=True) as retry_resp:
                                if retry_resp.status != 200:
                                    raise aiohttp.ClientError(f"HTTP {retry_resp.status}: {retry_resp.reason}")
                                content_type = retry_resp.headers.get('content-type', '').lower()
                                task.file_size = retry_resp.content_length
                                async with aiofiles.open(task.output_path, 'wb') as f:
                                    async for chunk in retry_resp.content.iter_chunked(8192):
                                        await f.write(chunk)
                        else:
                            raise aiohttp.ClientError(f"HTTP {response.status}: {response.reason}")
                    else:
                        content_type = response.headers.get('content-type', '').lower()
                        task.file_size = response.content_length
                        async with aiofiles.open(task.output_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                
                # 验证下载的文件
                if not await self._validate_pdf(task.output_path):
                    try:
                        os.remove(task.output_path)
                    except Exception:
                        pass
                    raise ValueError("下载的文件不是有效的PDF")
                
                # 记录成功信息
                download_time = (datetime.now() - start_time).total_seconds()
                task.download_time = download_time
                task.status = 'completed'
                
                self.stats['completed_tasks'] += 1
                self.stats['total_size'] += task.file_size or 0
                self.stats['total_time'] += download_time
                
                logger.success(f"下载成功: {task.paper.title} ({self._format_size(task.file_size)} in {download_time:.1f}s)")
                
                return DownloadResult(
                    task=task,
                    success=True,
                    file_path=task.output_path,
                    file_size=task.file_size,
                    download_time=download_time
                )
                
            except Exception as e:
                # 记录失败信息
                task.status = 'failed'
                task.error_message = str(e)
                
                self.stats['failed_tasks'] += 1
                
                logger.error(f"下载失败: {task.paper.title} - {e}")
                
                return DownloadResult(
                    task=task,
                    success=False,
                    error_message=str(e)
                )
    
    async def _validate_pdf(self, file_path: str) -> bool:
        """验证PDF文件"""
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # 小于1KB的文件可能无效
                return False
            
            # 检查文件头与是否为HTML
            async with aiofiles.open(file_path, 'rb') as f:
                head = await f.read(512)
                if not head:
                    return False
                if head[:4] == b'%PDF':
                    return True
                lowered = head.lower()
                if b'<!doctype html' in lowered or b'<html' in lowered or b'<head' in lowered:
                    return False
                # 对部分站点的跳转页（如错误JSON/文本）进行排除
                if lowered.startswith(b'{') or b'title' in lowered and b'</' in lowered:
                    return False
                return False
                
        except Exception as e:
            logger.warning(f"PDF验证失败: {e}")
            return False
    
    async def download_batch(self, tasks: List[DownloadTask]) -> List[DownloadResult]:
        """批量下载PDF文件"""
        if not tasks:
            return []
        
        self.stats['total_tasks'] = len(tasks)
        
        logger.info(f"开始批量下载 {len(tasks)} 个文件")
        
        # 创建会话
        await self.create_session()
        
        try:
            # 创建下载任务
            download_tasks = []
            for task in tasks:
                # 检查文件是否已存在
                if os.path.exists(task.output_path):
                    logger.info(f"文件已存在，跳过: {task.paper.title}")
                    result = DownloadResult(
                        task=task,
                        success=True,
                        file_path=task.output_path,
                        file_size=os.path.getsize(task.output_path)
                    )
                    self.stats['completed_tasks'] += 1
                    download_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # 空任务
                else:
                    download_tasks.append(asyncio.create_task(self.download_pdf(task)))
            
            # 执行所有下载任务
            results = await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # 处理结果
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"任务 {i} 执行异常: {result}")
                    # 创建失败结果
                    failed_result = DownloadResult(
                        task=tasks[i],
                        success=False,
                        error_message=str(result)
                    )
                    valid_results.append(failed_result)
                else:
                    valid_results.append(result)
            
            # 保存元数据
            await self._save_metadata(tasks)
            
            # 生成报告
            self._generate_report()
            
            return valid_results
            
        finally:
            # 关闭会话
            await self.close_session()
    
    async def _save_metadata(self, tasks: List[DownloadTask]):
        """保存元数据"""
        metadata_dir = self.output_dir / 'metadata'
        
        for task in tasks:
            if task.status == 'completed':
                metadata = {
                    'title': task.paper.title,
                    'authors': task.paper.authors,
                    'year': task.paper.year,
                    'journal': task.paper.journal,
                    'doi': task.paper.doi,
                    'platform': task.platform,
                    'download_time': task.created_at.isoformat(),
                    'file_size': task.file_size,
                    'file_path': task.output_path,
                    'pdf_url': task.pdf_url
                }
                
                # 生成元数据文件名
                base_filename = os.path.basename(task.output_path).replace('.pdf', '')
                metadata_file = metadata_dir / f"{base_filename}.json"
                
                try:
                    async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
                except Exception as e:
                    logger.warning(f"保存元数据失败: {e}")
    
    def _generate_report(self):
        """生成下载报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tasks': self.stats['total_tasks'],
            'completed_tasks': self.stats['completed_tasks'],
            'failed_tasks': self.stats['failed_tasks'],
            'success_rate': self.stats['completed_tasks'] / max(self.stats['total_tasks'], 1),
            'total_size': self.stats['total_size'],
            'total_size_formatted': self._format_size(self.stats['total_size']),
            'total_time': self.stats['total_time'],
            'average_speed': self.stats['total_size'] / max(self.stats['total_time'], 1) if self.stats['total_time'] > 0 else 0
        }
        
        # 保存报告
        report_file = self.output_dir / 'logs' / f"download_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"下载报告已保存: {report_file}")
            logger.info(f"下载统计: {report['completed_tasks']}/{report['total_tasks']} 成功, "
                       f"总大小: {report['total_size_formatted']}, "
                       f"成功率: {report['success_rate']:.1%}")
            
        except Exception as e:
            logger.warning(f"保存下载报告失败: {e}")

    def _build_referer(self, url: str) -> str:
        """根据URL构建合理的Referer"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            return 'https://scholar.google.com/'
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes is None or size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
    
    def get_download_summary(self) -> Dict:
        """获取下载摘要"""
        return {
            'total_tasks': self.stats['total_tasks'],
            'completed_tasks': self.stats['completed_tasks'],
            'failed_tasks': self.stats['failed_tasks'],
            'success_rate': self.stats['completed_tasks'] / max(self.stats['total_tasks'], 1),
            'total_size': self.stats['total_size'],
            'total_size_formatted': self._format_size(self.stats['total_size']),
            'total_time': self.stats['total_time']
        }


# 同步包装器
def download_pdfs_sync(tasks: List[DownloadTask], config: Dict = None) -> List[DownloadResult]:
    """同步版本的PDF下载"""
    downloader = PDFDownloader(config)
    
    async def _run():
        return await downloader.download_batch(tasks)
    
    return asyncio.run(_run())


# 测试函数
import random
import re

async def test_pdf_downloader():
    """测试PDF下载器"""
    config = {
        'max_concurrent': 2,
        'output_dir': './test_downloads'
    }
    
    downloader = PDFDownloader(config)
    
    # 创建测试任务（使用示例PDF URL）
    test_tasks = []
    
    # 这里使用一些示例PDF URL进行测试
    test_urls = [
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "https://www.africau.edu/images/default/sample.pdf",
    ]
    
    for i, url in enumerate(test_urls):
        paper = PaperInfo(
            title=f"测试论文 {i+1}",
            authors=[f"作者{i+1}"],
            year=2023 + i
        )
        
        task = DownloadTask(
            paper=paper,
            pdf_url=url,
            output_path=downloader.get_file_path(paper, 'test'),
            platform='test'
        )
        
        test_tasks.append(task)
    
    # 执行下载
    results = await downloader.download_batch(test_tasks)
    
    # 显示结果
    print("\n下载结果:")
    for result in results:
        status = "✅ 成功" if result.success else "❌ 失败"
        print(f"{status} {result.task.paper.title}")
        if result.success:
            print(f"   文件: {result.file_path}")
            print(f"   大小: {downloader._format_size(result.file_size)}")
            print(f"   时间: {result.download_time:.1f}s")
        else:
            print(f"   错误: {result.error_message}")
        print()
    
    # 显示统计信息
    summary = downloader.get_download_summary()
    print("下载统计:")
    print(f"总任务数: {summary['total_tasks']}")
    print(f"成功: {summary['completed_tasks']}")
    print(f"失败: {summary['failed_tasks']}")
    print(f"成功率: {summary['success_rate']:.1%}")
    print(f"总大小: {summary['total_size_formatted']}")