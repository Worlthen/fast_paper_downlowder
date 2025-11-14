import requests
import json
import time
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin, urlparse
from bs4 import BeautifulSoup

class ResearchGateSearcher:
    """ResearchGate平台搜索器 - 学术社交网络（公开PDF）"""
    
    def __init__(self):
        self.base_url = "https://www.researchgate.net"
        self.search_url = f"{self.base_url}/search/publication"
        self.name = "ResearchGate"
        self.max_results = 30
        self.rate_limit_delay = 2  # ResearchGate有严格的反爬虫机制
        self.logger = logging.getLogger(__name__)
        
        # 模拟浏览器请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索ResearchGate公开论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # ResearchGate使用不同的搜索机制
            search_query = quote(query)
            
            # 构建搜索URL
            url = f"{self.search_url}?q={search_query}&type=publication"
            
            self.logger.info(f"搜索ResearchGate: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析HTML响应
            return self._parse_researchgate_search(response.text, query)
            
        except requests.RequestException as e:
            self.logger.error(f"ResearchGate搜索请求失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"ResearchGate搜索解析失败: {e}")
            return []
    
    def _parse_researchgate_search(self, html_content: str, original_query: str) -> List[Dict]:
        """解析ResearchGate搜索结果HTML"""
        papers = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找论文条目 - ResearchGate的HTML结构可能会变化
            # 使用多种选择器以提高成功率
            publication_selectors = [
                'div[data-testid="publication-item"]',
                'div[class*="publication-item"]',
                'div[class*="nova-c-card"]',
                'div[class*="search-result-item"]',
                'div[class*="publication"]'
            ]
            
            publication_items = []
            for selector in publication_selectors:
                items = soup.select(selector)
                if items:
                    publication_items = items
                    break
            
            if not publication_items:
                # 尝试更通用的方法
                publication_items = soup.find_all('div', class_=re.compile(r'.*publication.*', re.I))
            
            self.logger.info(f"找到 {len(publication_items)} 个ResearchGate论文条目")
            
            for item in publication_items[:self.max_results]:
                try:
                    paper = self._parse_researchgate_publication_item(item)
                    if paper and self._is_relevant_paper(paper, original_query):
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析ResearchGate论文条目失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析ResearchGate搜索结果失败: {e}")
            
        return papers
    
    def _parse_researchgate_publication_item(self, item) -> Optional[Dict]:
        """解析单个ResearchGate论文条目"""
        try:
            # 提取标题
            title = ""
            title_selectors = [
                'h3[class*="title"]',
                'a[data-testid="publication-title"]',
                'a[class*="publication-title"]',
                'div[class*="title"] h3',
                'h3'
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            if not title:
                return None
            
            # 提取链接
            paper_url = ""
            link_selectors = [
                'a[data-testid="publication-title"]',
                'a[class*="publication-title"]',
                'a[href*="/publication/"]',
                'h3 a',
                'a'
            ]
            
            for selector in link_selectors:
                link_elem = item.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        paper_url = urljoin(self.base_url, href)
                    else:
                        paper_url = href
                    break
            
            # 提取作者
            authors = []
            author_selectors = [
                'div[class*="author"]',
                'span[class*="author"]',
                'a[class*="author"]',
                'div[class*="contributor"]'
            ]
            
            for selector in author_selectors:
                author_elems = item.select(selector)
                if author_elems:
                    for author_elem in author_elems:
                        author_name = author_elem.get_text(strip=True)
                        if author_name and author_name not in authors:
                            authors.append(author_name)
                    break
            
            # 提取摘要（通常需要访问详细页面）
            abstract = ""
            
            # 提取发表年份
            year = ""
            year_patterns = [
                r'\b(19|20)\d{2}\b',  # 1900-2099
            ]
            
            text_content = item.get_text()
            for pattern in year_patterns:
                match = re.search(pattern, text_content)
                if match:
                    year = match.group()
                    break
            
            # 提取PDF链接（如果可用）
            pdf_url = ""
            pdf_selectors = [
                'a[href*=".pdf"]',
                'a[data-testid="full-text"]',
                'a[class*="full-text"]',
                'a:contains("Full-text")',
                'a:contains("PDF")'
            ]
            
            for selector in pdf_selectors:
                pdf_elem = item.select_one(selector)
                if pdf_elem and pdf_elem.get('href'):
                    href = pdf_elem.get('href')
                    if href.startswith('/'):
                        pdf_url = urljoin(self.base_url, href)
                    else:
                        pdf_url = href
                    break
            
            # 如果没有直接的PDF链接，尝试构建可能的PDF链接
            if not pdf_url and paper_url:
                pdf_url = self._try_to_find_pdf_url(paper_url)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': year,
                'pdf_url': pdf_url,
                'paper_url': paper_url,
                'source': 'ResearchGate',
                'open_access': bool(pdf_url),  # 如果有PDF链接，认为是开放获取
                'citation_count': None,  # 需要访问详细页面获取
                'year': year
            }
            
        except Exception as e:
            self.logger.error(f"解析ResearchGate论文条目详情失败: {e}")
            return None
    
    def _is_relevant_paper(self, paper: Dict, query: str) -> bool:
        """检查论文是否与查询相关"""
        try:
            query_lower = query.lower()
            title = paper.get('title', '').lower()
            
            # 简单的相关性检查
            query_words = query_lower.split()
            title_words = title.split()
            
            # 计算匹配的词数
            matches = sum(1 for word in query_words if word in title)
            
            # 如果至少有一个词匹配，认为是相关的
            return matches > 0 or query_lower in title
            
        except Exception:
            return True  # 如果检查失败，默认包含
    
    def _try_to_find_pdf_url(self, paper_url: str) -> str:
        """尝试从论文页面找到PDF链接"""
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(paper_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找PDF链接
            pdf_selectors = [
                'a[href*=".pdf"]',
                'a[data-testid="full-text"]',
                'a[class*="full-text"]',
                'a:contains("Full-text")',
                'a:contains("Download")',
                'button[data-testid="full-text"]'
            ]
            
            for selector in pdf_selectors:
                elem = soup.select_one(selector)
                if elem:
                    href = elem.get('href') or elem.get('data-href')
                    if href:
                        if href.startswith('/'):
                            return urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            return href
            
            # 尝试JavaScript中的PDF链接
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # 查找包含.pdf的URL
                    pdf_matches = re.findall(r'https?://[^\s"\']+\.pdf[^\s"\']*', script.string)
                    if pdf_matches:
                        return pdf_matches[0]
            
            return ""
            
        except Exception as e:
            self.logger.warning(f"尝试查找PDF链接失败 {paper_url}: {e}")
            return ""
    
    def get_paper_by_url(self, paper_url: str) -> Optional[Dict]:
        """通过ResearchGate URL获取论文详情"""
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(paper_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取详细信息
            title = ""
            title_selectors = [
                'h1[class*="publication-title"]',
                'h1[data-testid="publication-title"]',
                'h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # 提取作者
            authors = []
            author_selectors = [
                'div[class*="author"]',
                'a[href*="/profile/"]',
                'span[class*="name"]'
            ]
            
            for selector in author_selectors:
                author_elems = soup.select(selector)
                for author_elem in author_elems:
                    author_name = author_elem.get_text(strip=True)
                    if author_name and len(author_name) < 100:  # 过滤掉过长的文本
                        authors.append(author_name)
                if authors:
                    break
            
            # 提取摘要
            abstract = ""
            abstract_selectors = [
                'div[class*="abstract"]',
                'div[data-testid="abstract"]',
                'div[class*="description"]'
            ]
            
            for selector in abstract_selectors:
                abstract_elem = soup.select_one(selector)
                if abstract_elem:
                    abstract = abstract_elem.get_text(strip=True)
                    break
            
            # 提取PDF链接
            pdf_url = self._try_to_find_pdf_url(paper_url)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': '',
                'pdf_url': pdf_url,
                'paper_url': paper_url,
                'source': 'ResearchGate',
                'open_access': bool(pdf_url)
            }
            
        except Exception as e:
            self.logger.error(f"获取ResearchGate论文详情失败 {paper_url}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查ResearchGate是否可用"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # 使用与搜索相同的headers
            response = requests.get(pdf_url, headers=self.headers, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"ResearchGate PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"ResearchGate PDF下载失败: {e}")
            return False