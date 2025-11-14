"""
学术论文自动下载器主协调器
负责协调各个模块，实现完整的下载流程
新增平台支持：
- arXiv: 预印本论文平台
- PubMed Central: 生物医学文献
- DOAJ: 开放获取期刊
- CORE: 全球开放获取论文库
- Semantic Scholar: AI驱动的学术搜索引擎
- ResearchGate: 学术社交网络（公开PDF）
- Academia.edu: 学术分享平台
- Zenodo: 研究数据仓储
- HAL: 法国开放获取仓储
- bioRxiv/medRxiv: 生命科学预印本
"""

import asyncio
import random
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

from config import DEFAULT_CONFIG
from paper_parser import PaperListParser, PaperInfo
from google_scholar import GoogleScholarSearcher, SearchResult
from scihub import SciHubSearcher, SciHubResult
from pdf_downloader import PDFDownloader, DownloadTask, DownloadResult
from arxiv import ArXivSearcher
from pubmed import PubMedCentralSearcher
from doaj import DOAJSearcher
from core import CORESearcher
from semantic_scholar import SemanticScholarSearcher
from researchgate import ResearchGateSearcher
from academia import AcademiaSearcher
from zenodo import ZenodoSearcher
from hal import HALSearcher
from biorxiv import BioRxivSearcher


@dataclass
class SearchConfig:
    """搜索配置"""
    platforms: List[str]  # ['google_scholar', 'scihub', 'arxiv', 'pubmed', 'doaj', 'core', 'semantic_scholar', 'researchgate', 'academia', 'zenodo', 'hal', 'biorxiv']
    max_results_per_platform: int = 5
    use_async: bool = True
    retry_failed: bool = True
    max_retries: int = 3


@dataclass
class DownloadConfig:
    """下载配置"""
    output_dir: str = "./downloads"
    max_concurrent_downloads: int = 3
    overwrite_existing: bool = False
    save_metadata: bool = True
    organize_by_platform: bool = False


class PaperDownloaderCoordinator:
    """论文下载协调器"""
    
    def __init__(self, search_config: SearchConfig = None, download_config: DownloadConfig = None):
        """
        初始化协调器
        
        支持的平台：
        - google_scholar: Google Scholar搜索
        - scihub: Sci-Hub下载
        - arxiv: arXiv预印本
        - pubmed: PubMed Central生物医学文献
        - doaj: DOAJ开放获取期刊
        - core: CORE全球开放获取论文库
        - semantic_scholar: Semantic Scholar AI学术搜索
        - researchgate: ResearchGate学术社交网络
        - academia: Academia.edu学术分享平台
        - zenodo: Zenodo研究数据仓储
        - hal: HAL法国开放获取仓储
        - biorxiv: bioRxiv/medRxiv生命科学预印本
        """
        self.search_config = search_config or SearchConfig(platforms=['google_scholar', 'scihub'])
        self.download_config = download_config or DownloadConfig()
        
        # 初始化各个模块
        self.parser = PaperListParser()
        self.google_scholar = GoogleScholarSearcher()
        self.scihub = SciHubSearcher()
        
        # 新增平台模块
        self.arxiv = ArXivSearcher()
        self.pubmed = PubMedCentralSearcher()
        self.doaj = DOAJSearcher()
        self.core = CORESearcher()
        self.semantic_scholar = SemanticScholarSearcher()
        self.researchgate = ResearchGateSearcher()
        self.academia = AcademiaSearcher()
        self.zenodo = ZenodoSearcher()
        self.hal = HALSearcher()
        self.biorxiv = BioRxivSearcher()
        
        self.pdf_downloader = PDFDownloader({
            'max_concurrent': self.download_config.max_concurrent_downloads,
            'output_dir': self.download_config.output_dir
        })
        
        # 统计信息
        self.stats = {
            'total_papers': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'platform_stats': {
                'google_scholar': {'searches': 0, 'success': 0},
                'scihub': {'searches': 0, 'success': 0},
                'arxiv': {'searches': 0, 'success': 0},
                'pubmed': {'searches': 0, 'success': 0},
                'doaj': {'searches': 0, 'success': 0},
                'core': {'searches': 0, 'success': 0},
                'semantic_scholar': {'searches': 0, 'success': 0},
                'researchgate': {'searches': 0, 'success': 0},
                'academia': {'searches': 0, 'success': 0},
                'zenodo': {'searches': 0, 'success': 0},
                'hal': {'searches': 0, 'success': 0},
                'biorxiv': {'searches': 0, 'success': 0}
            }
        }
    
    async def process_paper_list(self, input_file: str) -> Dict:
        """处理论文列表文件"""
        logger.info(f"开始处理论文列表文件: {input_file}")
        
        # 解析论文列表
        papers = self.parser.parse_file(input_file)
        if not papers:
            logger.error("未能解析到任何论文")
            return {'success': False, 'error': 'No papers found in input file'}
        
        self.stats['total_papers'] = len(papers)
        logger.info(f"解析到 {len(papers)} 篇论文")
        
        # 搜索论文
        search_results = await self._search_papers(papers)
        
        # 下载PDF
        download_results = await self._download_pdfs(search_results)
        
        # 生成最终报告
        return self._generate_final_report(papers, search_results, download_results)
    
    async def _search_papers(self, papers: List[PaperInfo]) -> List[Dict]:
        """搜索论文"""
        logger.info(f"开始搜索 {len(papers)} 篇论文")
        
        search_results = []
        
        if self.search_config.use_async:
            # 异步搜索
            tasks = []
            for paper in papers:
                task = asyncio.create_task(self._search_single_paper_async(paper))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"搜索任务异常: {result}")
                    search_results.append({'success': False, 'error': str(result)})
                else:
                    search_results.append(result)
        else:
            # 同步搜索
            for paper in papers:
                result = await self._search_single_paper_async(paper)
                search_results.append(result)
        
        return search_results
    
    async def _search_single_paper_async(self, paper: PaperInfo) -> Dict:
        """异步搜索单篇论文"""
        logger.info(f"搜索论文: {paper.title}")
        
        search_result = {
            'paper': paper,
            'success': False,
            'platform': None,
            'pdf_url': None,
            'search_results': [],
            'error': None
        }
        
        # 按优先级搜索不同平台
        for platform in self.search_config.platforms:
            try:
                result = await self._search_on_platform(paper, platform)
                if result and result.get('pdf_url'):
                    search_result.update({
                        'success': True,
                        'platform': platform,
                        'pdf_url': result['pdf_url'],
                        'search_results': result.get('details', [])
                    })
                    self.stats['successful_searches'] += 1
                    self.stats['platform_stats'][platform]['success'] += 1
                    logger.success(f"在 {platform} 找到PDF: {paper.title}")
                    break
                else:
                    logger.info(f"在 {platform} 未找到PDF: {paper.title}")
                    
            except Exception as e:
                logger.warning(f"在 {platform} 搜索失败: {paper.title} - {e}")
                continue
            
            # 平台间延迟
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        if not search_result['success']:
            self.stats['failed_searches'] += 1
            search_result['error'] = 'No PDF found on any platform'
            logger.error(f"所有平台搜索失败: {paper.title}")
        
        return search_result
    
    async def _search_on_platform(self, paper: PaperInfo, platform: str) -> Optional[Dict]:
        """在特定平台搜索"""
        self.stats['platform_stats'][platform]['searches'] += 1
        
        if platform == 'google_scholar':
            return await self._search_google_scholar(paper)
        elif platform == 'scihub':
            return await self._search_scihub(paper)
        elif platform == 'arxiv':
            return await self._search_arxiv(paper)
        elif platform == 'pubmed':
            return await self._search_pubmed(paper)
        elif platform == 'doaj':
            return await self._search_doaj(paper)
        elif platform == 'core':
            return await self._search_core(paper)
        elif platform == 'semantic_scholar':
            return await self._search_semantic_scholar(paper)
        elif platform == 'researchgate':
            return await self._search_researchgate(paper)
        elif platform == 'academia':
            return await self._search_academia(paper)
        elif platform == 'zenodo':
            return await self._search_zenodo(paper)
        elif platform == 'hal':
            return await self._search_hal(paper)
        elif platform == 'biorxiv':
            return await self._search_biorxiv(paper)
        else:
            logger.warning(f"不支持的平台: {platform}")
            return None
    
    async def _search_google_scholar(self, paper: PaperInfo) -> Optional[Dict]:
        """在Google Scholar搜索"""
        try:
            results = await asyncio.to_thread(self.google_scholar.search_paper, paper, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 优先选择开放获取来源的PDF链接
            import urllib.parse
            open_hosts = {
                'arxiv.org',
                'www.ncbi.nlm.nih.gov',
                'core.ac.uk',
                'www.semanticscholar.org',
                'www.researchgate.net',
                'www.academia.edu',
                'zenodo.org',
                'hal.archives-ouvertes.fr'
            }
            preferred_result = None
            for result in results:
                if result.pdf_url:
                    host = urllib.parse.urlparse(result.pdf_url).netloc
                    if host in open_hosts or host.endswith('.edu') or host.endswith('.ac.uk'):
                        return {
                            'pdf_url': result.pdf_url,
                            'details': [{
                                'title': result.title,
                                'authors': result.authors,
                                'year': result.year,
                                'journal': result.journal,
                                'cited_by': result.cited_by_count
                            }]
                        }
                    if preferred_result is None:
                        preferred_result = result
            # 若没有开放获取链接，退回第一个可用PDF
            if preferred_result and preferred_result.pdf_url:
                return {
                    'pdf_url': preferred_result.pdf_url,
                    'details': [{
                        'title': preferred_result.title,
                        'authors': preferred_result.authors,
                        'year': preferred_result.year,
                        'journal': preferred_result.journal,
                        'cited_by': preferred_result.cited_by_count
                    }]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Google Scholar搜索失败: {e}")
            return None
    
    async def _search_scihub(self, paper: PaperInfo) -> Optional[Dict]:
        """在Sci-Hub搜索"""
        try:
            result = await asyncio.to_thread(self.scihub.search_paper, paper)
            
            if result and result.available and result.download_url:
                return {
                    'pdf_url': result.download_url,
                    'details': [{
                        'title': result.title,
                        'authors': result.authors,
                        'year': result.year,
                        'journal': result.journal,
                        'doi': result.doi
                    }]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Sci-Hub搜索失败: {e}")
            return None
    
    async def _search_arxiv(self, paper: PaperInfo) -> Optional[Dict]:
        """在arXiv搜索预印本论文"""
        try:
            # 构建搜索查询
            search_query = paper.title
            if paper.authors:
                author_query = " ".join(paper.authors[:3])  # 使用前3个作者
                search_query = f"{search_query} {author_query}"
            
            results = await asyncio.to_thread(self.arxiv.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': 'arXiv preprint',
                            'arxiv_id': result.get('arxiv_id', ''),
                            'categories': result.get('categories', [])
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"arXiv搜索失败: {e}")
            return None
    
    async def _search_pubmed(self, paper: PaperInfo) -> Optional[Dict]:
        """在PubMed Central搜索生物医学文献"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.pubmed.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'pmc_id': result.get('pmc_id', ''),
                            'doi': result.get('doi', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"PubMed Central搜索失败: {e}")
            return None
    
    async def _search_doaj(self, paper: PaperInfo) -> Optional[Dict]:
        """在DOAJ搜索开放获取期刊"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.doaj.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'doi': result.get('doi', ''),
                            'keywords': result.get('keywords', [])
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"DOAJ搜索失败: {e}")
            return None
    
    async def _search_core(self, paper: PaperInfo) -> Optional[Dict]:
        """在CORE搜索全球开放获取论文"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.core.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'doi': result.get('doi', ''),
                            'citation_count': result.get('citation_count'),
                            'publisher': result.get('publisher', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"CORE搜索失败: {e}")
            return None
    
    async def _search_semantic_scholar(self, paper: PaperInfo) -> Optional[Dict]:
        """在Semantic Scholar搜索AI驱动的学术内容"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.semantic_scholar.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'doi': result.get('doi', ''),
                            'citation_count': result.get('citation_count'),
                            'fields_of_study': result.get('fields_of_study', [])
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Semantic Scholar搜索失败: {e}")
            return None
    
    async def _search_researchgate(self, paper: PaperInfo) -> Optional[Dict]:
        """在ResearchGate搜索学术社交网络"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.researchgate.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result.get('year', paper.year),
                            'paper_url': result.get('paper_url', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"ResearchGate搜索失败: {e}")
            return None
    
    async def _search_academia(self, paper: PaperInfo) -> Optional[Dict]:
        """在Academia.edu搜索学术分享平台"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.academia.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result.get('year', paper.year),
                            'document_url': result.get('document_url', ''),
                            'document_type': result.get('document_type', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Academia.edu搜索失败: {e}")
            return None
    
    async def _search_zenodo(self, paper: PaperInfo) -> Optional[Dict]:
        """在Zenodo搜索研究数据仓储"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.zenodo.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'doi': result.get('doi', ''),
                            'resource_type': result.get('resource_type', ''),
                            'record_id': result.get('record_id', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Zenodo搜索失败: {e}")
            return None
    
    async def _search_hal(self, paper: PaperInfo) -> Optional[Dict]:
        """在HAL搜索法国开放获取仓储"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            results = await asyncio.to_thread(self.hal.search, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'journal': result.get('journal', ''),
                            'doi': result.get('doi', ''),
                            'hal_id': result.get('hal_id', ''),
                            'document_type': result.get('document_type', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"HAL搜索失败: {e}")
            return None
    
    async def _search_biorxiv(self, paper: PaperInfo) -> Optional[Dict]:
        """在bioRxiv/medRxiv搜索生命科学预印本"""
        try:
            # 构建搜索查询
            search_query = paper.title
            
            # 同时搜索bioRxiv和medRxiv
            results = await asyncio.to_thread(self.biorxiv.search_both_servers, search_query, self.search_config.max_results_per_platform)
            
            if not results:
                return None
            
            # 选择最相关的结果
            for result in results:
                if result.get('pdf_url'):
                    return {
                        'pdf_url': result['pdf_url'],
                        'details': [{
                            'title': result['title'],
                            'authors': result['authors'],
                            'year': result['published'][:4] if result['published'] else paper.year,
                            'server': result.get('server', ''),
                            'doi': result.get('doi', ''),
                            'category': result.get('category', ''),
                            'article_id': result.get('article_id', '')
                        }]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"bioRxiv/medRxiv搜索失败: {e}")
            return None
    
    async def _download_pdfs(self, search_results: List[Dict]) -> List[DownloadResult]:
        """下载PDF文件"""
        # 创建下载任务
        download_tasks = []
        
        for result in search_results:
            if not result.get('success') or not result.get('pdf_url'):
                continue
            
            paper = result['paper']
            pdf_url = result['pdf_url']
            platform = result['platform']
            
            # 生成输出路径
            output_path = self.pdf_downloader.get_file_path(paper, platform)
            
            # 检查文件是否已存在
            if Path(output_path).exists() and not self.download_config.overwrite_existing:
                logger.info(f"文件已存在，跳过: {paper.title}")
                self.stats['successful_downloads'] += 1
                continue
            
            # 创建下载任务
            task = DownloadTask(
                paper=paper,
                pdf_url=pdf_url,
                output_path=output_path,
                platform=platform
            )
            
            download_tasks.append(task)
        
        if not download_tasks:
            logger.info("没有需要下载的文件")
            return []
        
        logger.info(f"开始下载 {len(download_tasks)} 个PDF文件")
        
        # 执行批量下载
        download_results = await self.pdf_downloader.download_batch(download_tasks)

        # 对失败的下载进行平台回退尝试
        fallback_results: List[DownloadResult] = []
        for res in download_results:
            if res and not res.success:
                paper = res.task.paper
                tried_platform = res.task.platform
                fb_res = await self._attempt_fallback_download(paper, tried_platform)
                if fb_res:
                    fallback_results.append(fb_res)
        # 合并结果
        download_results.extend(fallback_results)
        
        # 更新统计信息
        for result in download_results:
            if result.success:
                self.stats['successful_downloads'] += 1
            else:
                self.stats['failed_downloads'] += 1
        
        return download_results

    async def _attempt_fallback_download(self, paper: PaperInfo, tried_platform: str) -> Optional[DownloadResult]:
        """当首选平台下载失败时，尝试其他平台进行回退下载"""
        for platform in self.search_config.platforms:
            if platform == tried_platform:
                continue
            try:
                result = await self._search_on_platform(paper, platform)
                if result and result.get('pdf_url'):
                    pdf_url = result['pdf_url']
                    output_path = self.pdf_downloader.get_file_path(paper, platform)
                    task = DownloadTask(
                        paper=paper,
                        pdf_url=pdf_url,
                        output_path=output_path,
                        platform=platform
                    )
                    logger.info(f"尝试回退平台下载: {paper.title} 来自 {platform}")
                    batch_res = await self.pdf_downloader.download_batch([task])
                    if batch_res and batch_res[0].success:
                        return batch_res[0]
            except Exception as e:
                logger.debug(f"回退平台 {platform} 尝试失败: {e}")
                continue
        return None
    
    def _generate_final_report(self, papers: List[PaperInfo], search_results: List[Dict], 
                              download_results: List[DownloadResult]) -> Dict:
        """生成最终报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_papers': len(papers),
                'successful_searches': self.stats['successful_searches'],
                'failed_searches': self.stats['failed_searches'],
                'successful_downloads': self.stats['successful_downloads'],
                'failed_downloads': self.stats['failed_downloads'],
                'search_success_rate': self.stats['successful_searches'] / max(len(papers), 1),
                'download_success_rate': self.stats['successful_downloads'] / max(self.stats['successful_searches'], 1)
            },
            'platform_stats': self.stats['platform_stats'],
            'details': {
                'successful_downloads': [],
                'failed_searches': [],
                'failed_downloads': []
            }
        }
        
        # 详细的成功下载信息
        for result in search_results:
            if result.get('success'):
                paper_info = {
                    'title': result['paper'].title,
                    'authors': result['paper'].authors,
                    'year': result['paper'].year,
                    'platform': result['platform'],
                    'pdf_url': result['pdf_url']
                }
                report['details']['successful_downloads'].append(paper_info)
            else:
                failed_info = {
                    'title': result['paper'].title,
                    'authors': result['paper'].authors,
                    'error': result.get('error', 'Unknown error')
                }
                report['details']['failed_searches'].append(failed_info)
        
        # 失败的下载
        for result in download_results:
            if not result.success:
                failed_info = {
                    'title': result.task.paper.title,
                    'error': result.error_message
                }
                report['details']['failed_downloads'].append(failed_info)
        
        logger.info("=" * 60)
        logger.info("下载任务完成")
        logger.info(f"总计论文: {report['summary']['total_papers']}")
        logger.info(f"搜索成功: {report['summary']['successful_searches']} "
                   f"({report['summary']['search_success_rate']:.1%})")
        logger.info(f"下载成功: {report['summary']['successful_downloads']} "
                   f"({report['summary']['download_success_rate']:.1%})")
        logger.info("=" * 60)
        
        return report
    
    def close(self):
        """关闭协调器"""
        try:
            self.google_scholar.close()
            self.scihub.close()
            logger.info("论文下载协调器已关闭")
        except Exception as e:
            logger.warning(f"关闭协调器时出错: {e}")


# 关键词搜索协调器
class SearchCoordinator:
    def __init__(self):
        self.searchers = {
            'arxiv': ArXivSearcher(),
            'pubmed': PubMedCentralSearcher(),
            'doaj': DOAJSearcher(),
            'core': CORESearcher(),
            'semantic_scholar': SemanticScholarSearcher(),
            'researchgate': ResearchGateSearcher(),
            'academia': AcademiaSearcher(),
            'zenodo': ZenodoSearcher(),
            'hal': HALSearcher(),
            'biorxiv': BioRxivSearcher(),
        }

    async def search(self, keyword: str, platforms: List[str] = None, max_results: int = 10) -> List[Dict]:
        selected = platforms or list(self.searchers.keys())
        results: List[Dict] = []
        for platform in selected:
            searcher = self.searchers.get(platform)
            if not searcher:
                continue
            try:
                items = searcher.search(keyword, max_results)
                for item in items:
                    results.append(self._normalize_result(platform, item))
            except Exception as e:
                logger.warning(f"平台搜索失败: {platform} - {e}")
        return results

    async def check_platform_availability(self, platform: str) -> bool:
        searcher = self.searchers.get(platform)
        if not searcher:
            return False
        try:
            if hasattr(searcher, 'check_availability'):
                return bool(searcher.check_availability())
            probe = searcher.search('test', 1)
            return bool(probe)
        except Exception:
            return False

    def _normalize_result(self, platform: str, item: Dict) -> Dict:
        year = None
        published = item.get('published')
        if isinstance(published, str) and len(published) >= 4:
            year = published[:4]
        else:
            year = item.get('year')
        pdf_url = item.get('pdf_url') or item.get('download_url')
        return {
            'platform': platform,
            'title': item.get('title'),
            'authors': item.get('authors'),
            'year': year,
            'doi': item.get('doi'),
            'pdf_url': pdf_url,
        }