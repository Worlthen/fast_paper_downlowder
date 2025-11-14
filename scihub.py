"""
Sci-Hub搜索和下载模块
负责从Sci-Hub搜索和下载学术论文
"""

import re
import time
import random
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import SCIHUB_MIRRORS, USER_AGENTS
from paper_parser import PaperInfo


@dataclass
class SciHubResult:
    """Sci-Hub搜索结果数据结构"""
    title: str
    authors: str
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    pdf_url: Optional[str]
    download_url: Optional[str]
    available: bool


class SciHubSearcher:
    """Sci-Hub搜索器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.mirrors = self.config.get('mirrors', SCIHUB_MIRRORS)
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.delay = self.config.get('delay', 2.0)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.current_mirror = None

    
    def _select_working_mirror(self) -> bool:
        """选择可用的Sci-Hub镜像"""
        for mirror in self.mirrors:
            try:
                logger.debug(f"测试Sci-Hub镜像: {mirror}")
                response = self.session.get(mirror, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    self.current_mirror = mirror
                    logger.info(f"选择Sci-Hub镜像: {mirror}")
                    return True
            except Exception as e:
                logger.warning(f"镜像 {mirror} 不可用: {e}")
                continue
        
        logger.error("所有Sci-Hub镜像都不可用")
        return False
    
    def search_by_doi(self, doi: str) -> Optional[SciHubResult]:
        """通过DOI搜索论文"""
        if not self.current_mirror:
            logger.error("没有可用的Sci-Hub镜像")
            return None
        
        doi = self._clean_doi(doi)
        logger.info(f"通过DOI搜索: {doi}")
        
        try:
            # 构建搜索URL
            search_url = f"{self.current_mirror}/{doi}"
            
            for attempt in range(self.max_retries):
                try:
                    response = self.session.get(search_url, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        return self._parse_article_page(response.text, doi)
                    elif response.status_code == 404:
                        logger.warning(f"DOI未找到: {doi}")
                        return None
                    else:
                        logger.warning(f"搜索失败，状态码: {response.status_code}")
                        
                except requests.RequestException as e:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(random.uniform(1, self.delay * (attempt + 1)))
                        continue
                    else:
                        raise
            
            return None
            
        except Exception as e:
            logger.error(f"DOI搜索失败: {e}")
            return None
    
    def search_by_title(self, title: str) -> Optional[SciHubResult]:
        """通过标题搜索论文"""
        if not self.current_mirror:
            logger.error("没有可用的Sci-Hub镜像")
            return None
        
        logger.info(f"通过标题搜索: {title}")
        
        try:
            # 构建搜索URL（使用Sci-Hub的搜索功能）
            search_url = f"{self.current_mirror}/"
            
            # Sci-Hub通常通过POST表单提交搜索
            data = {
                'request': title
            }
            
            for attempt in range(self.max_retries):
                try:
                    response = self.session.post(search_url, data=data, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        # 检查是否直接跳转到文章页面
                        if '/abs/' in response.url or '/doi/' in response.url:
                            return self._parse_article_page(response.text, title=title)
                        else:
                            # 解析搜索结果页面
                            return self._parse_search_results(response.text, title)
                    else:
                        logger.warning(f"搜索失败，状态码: {response.status_code}")
                        
                except requests.RequestException as e:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(random.uniform(1, self.delay * (attempt + 1)))
                        continue
                    else:
                        raise
            
            return None
            
        except Exception as e:
            logger.error(f"标题搜索失败: {e}")
            return None
    
    def search_paper(self, paper: PaperInfo) -> Optional[SciHubResult]:
        """根据PaperInfo搜索论文"""
        if not self.current_mirror:
            if not self._select_working_mirror():
                return None
        
        # 优先使用DOI搜索
        if paper.doi:
            result = self.search_by_doi(paper.doi)
            if result and result.available:
                return result
        
        # 其次使用标题搜索
        if paper.title:
            result = self.search_by_title(paper.title)
            if result:
                return result
        
        return None
    
    def _clean_doi(self, doi: str) -> str:
        """清理DOI字符串"""
        # 移除DOI前缀
        doi = re.sub(r'^doi:\s*', '', doi, flags=re.IGNORECASE)
        doi = re.sub(r'^https?://doi\.org/', '', doi)
        doi = doi.strip()
        
        # 确保DOI格式正确
        if not doi.startswith('10.'):
            logger.warning(f"无效的DOI格式: {doi}")
        
        return doi
    
    def _parse_search_results(self, html: str, query: str) -> Optional[SciHubResult]:
        """解析搜索结果页面"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Sci-Hub的搜索结果页面结构可能不同
            # 查找最相关的结果
            articles = soup.find_all('div', class_='article')
            if not articles:
                articles = soup.find_all('div', recursive=True)
            
            for article in articles:
                title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    
                    # 检查标题相似度
                    if self._is_similar_title(title, query):
                        # 提取文章信息
                        return self._extract_article_info(article, title)
            
            logger.info(f"未找到匹配的论文: {query}")
            return None
            
        except Exception as e:
            logger.error(f"解析搜索结果失败: {e}")
            return None
    
    def _parse_article_page(self, html: str, doi: str = None, title: str = None) -> Optional[SciHubResult]:
        """解析文章页面"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找PDF下载按钮/链接
            pdf_url = None
            
            # 常见的PDF按钮选择器
            selectors = [
                'button[onclick*="pdf"]',
                'a[href*=".pdf"]',
                'iframe[src*=".pdf"]',
                'embed[src*=".pdf"]',
                '#pdf',
                '.pdf',
                '[onclick*="download"]'
            ]
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'button':
                        onclick = element.get('onclick', '')
                        pdf_match = re.search(r'[\'"]([^\'"]*\.pdf[^\'"]*)[\'"]', onclick)
                        if pdf_match:
                            pdf_url = pdf_match.group(1)
                    elif element.name == 'a':
                        pdf_url = element.get('href')
                    elif element.name in ['iframe', 'embed']:
                        pdf_url = element.get('src')
                    
                    if pdf_url:
                        break
            
            # 处理相对URL
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = urljoin(self.current_mirror, pdf_url)
            
            # 提取文章信息
            title_extracted = self._extract_title_from_page(soup) or title or "Unknown Title"
            authors = self._extract_authors_from_page(soup)
            year = self._extract_year_from_page(soup)
            journal = self._extract_journal_from_page(soup)
            
            return SciHubResult(
                title=title_extracted,
                authors=authors,
                year=year,
                journal=journal,
                doi=doi,
                pdf_url=pdf_url,
                download_url=pdf_url,
                available=bool(pdf_url)
            )
            
        except Exception as e:
            logger.error(f"解析文章页面失败: {e}")
            return None
    
    def _extract_article_info(self, article_element, title: str) -> SciHubResult:
        """从文章元素提取信息"""
        try:
            # 提取作者信息
            authors = "Unknown Authors"
            authors_elem = article_element.find(['p', 'div'], class_=re.compile(r'.*author.*', re.I))
            if authors_elem:
                authors = authors_elem.get_text(strip=True)
            
            # 提取年份
            year = None
            year_match = re.search(r'\b(19|20)\d{2}\b', article_element.get_text())
            if year_match:
                year = int(year_match.group())
            
            # 提取期刊
            journal = None
            journal_elem = article_element.find(['p', 'div'], class_=re.compile(r'.*journal.*', re.I))
            if journal_elem:
                journal = journal_elem.get_text(strip=True)
            
            # 查找PDF链接
            pdf_url = None
            pdf_link = article_element.find('a', href=re.compile(r'.*\.pdf.*'))
            if pdf_link:
                pdf_url = pdf_link.get('href')
                if pdf_url and not pdf_url.startswith('http'):
                    pdf_url = urljoin(self.current_mirror, pdf_url)
            
            return SciHubResult(
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                doi=None,
                pdf_url=pdf_url,
                download_url=pdf_url,
                available=bool(pdf_url)
            )
            
        except Exception as e:
            logger.error(f"提取文章信息失败: {e}")
            return SciHubResult(
                title=title,
                authors="Unknown Authors",
                year=None,
                journal=None,
                doi=None,
                pdf_url=None,
                download_url=None,
                available=False
            )
    
    def _extract_title_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """从页面提取标题"""
        # 尝试不同的标题选择器
        selectors = [
            'h1',
            'title',
            '.title',
            '#title',
            '[class*="title"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:  # 合理的标题长度
                    return title
        
        return None
    
    def _extract_authors_from_page(self, soup: BeautifulSoup) -> str:
        """从页面提取作者信息"""
        # 尝试不同的作者选择器
        selectors = [
            '.authors',
            '#authors',
            '[class*="author"]',
            'p:contains("Authors")',
            'div:contains("Authors")'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    authors = element.get_text(strip=True)
                    if authors and len(authors) > 3:
                        return authors
            except:
                continue
        
        return "Unknown Authors"
    
    def _extract_year_from_page(self, soup: BeautifulSoup) -> Optional[int]:
        """从页面提取年份"""
        text = soup.get_text()
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match:
            return int(year_match.group())
        return None
    
    def _extract_journal_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """从页面提取期刊信息"""
        # 尝试不同的期刊选择器
        selectors = [
            '.journal',
            '#journal',
            '[class*="journal"]',
            '.publication',
            '[class*="publication"]'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    journal = element.get_text(strip=True)
                    if journal and len(journal) > 2:
                        return journal
            except:
                continue
        
        return None
    
    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """检查两个标题是否相似"""
        # 简单的相似度检查
        title1_words = set(title1.lower().split())
        title2_words = set(title2.lower().split())
        
        # 计算交集比例
        intersection = title1_words.intersection(title2_words)
        union = title1_words.union(title2_words)
        
        if len(union) == 0:
            return False
        
        similarity = len(intersection) / len(union)
        return similarity > 0.5  # 相似度阈值
    
    def download_pdf(self, result: SciHubResult, output_path: str) -> bool:
        """下载PDF文件"""
        if not result.download_url:
            logger.error(f"没有可用的下载链接: {result.title}")
            return False
        
        try:
            logger.info(f"下载PDF: {result.title}")
            
            response = self.session.get(result.download_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and len(response.content) < 1000:
                logger.error(f"下载的内容不是PDF或文件太小: {content_type}")
                return False
            
            # 保存文件
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"PDF下载成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF下载失败: {e}")
            return False
    
    def close(self):
        """关闭搜索器"""
        if self.session:
            self.session.close()