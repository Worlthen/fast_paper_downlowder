import requests
import json
import time
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin, urlparse
from bs4 import BeautifulSoup

class AcademiaSearcher:
    """Academia.edu平台搜索器 - 学术分享平台"""
    
    def __init__(self):
        self.base_url = "https://www.academia.edu"
        self.search_url = f"{self.base_url}/search"
        self.name = "Academia.edu"
        self.max_results = 30
        self.rate_limit_delay = 2  # Academia.edu有反爬虫机制
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
        搜索Academia.edu公开论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建搜索URL
            search_query = quote(query)
            url = f"{self.search_url}?q={search_query}"
            
            self.logger.info(f"搜索Academia.edu: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析HTML响应
            return self._parse_academia_search(response.text, query)
            
        except requests.RequestException as e:
            self.logger.error(f"Academia.edu搜索请求失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Academia.edu搜索解析失败: {e}")
            return []
    
    def _parse_academia_search(self, html_content: str, original_query: str) -> List[Dict]:
        """解析Academia.edu搜索结果HTML"""
        papers = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找论文条目 - Academia.edu的HTML结构可能会变化
            # 使用多种选择器以提高成功率
            document_selectors = [
                'div[data-testid="document-item"]',
                'div[class*="document-item"]',
                'div[class*="document"]',
                'div[class*="paper-item"]',
                'div[class*="search-result"]',
                'article[class*="document"]'
            ]
            
            document_items = []
            for selector in document_selectors:
                items = soup.select(selector)
                if items:
                    document_items = items
                    break
            
            if not document_items:
                # 尝试更通用的方法
                document_items = soup.find_all('div', class_=re.compile(r'.*document.*|.*paper.*', re.I))
            
            self.logger.info(f"找到 {len(document_items)} 个Academia.edu文档条目")
            
            for item in document_items[:self.max_results]:
                try:
                    paper = self._parse_academia_document_item(item)
                    if paper and self._is_relevant_paper(paper, original_query):
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析Academia.edu文档条目失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析Academia.edu搜索结果失败: {e}")
            
        return papers
    
    def _parse_academia_document_item(self, item) -> Optional[Dict]:
        """解析单个Academia.edu文档条目"""
        try:
            # 提取标题
            title = ""
            title_selectors = [
                'h3[class*="title"]',
                'h2[class*="title"]',
                'a[class*="title"]',
                'h3',
                'h2'
            ]
            
            for selector in title_selectors:
                title_elem = item.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            if not title:
                return None
            
            # 提取链接
            document_url = ""
            link_selectors = [
                'a[class*="document-link"]',
                'a[href*="/documents/"]',
                'a[href*="/paper/"]',
                'h3 a',
                'h2 a',
                'a'
            ]
            
            for selector in link_selectors:
                link_elem = item.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        document_url = urljoin(self.base_url, href)
                    else:
                        document_url = href
                    break
            
            # 提取作者
            authors = []
            author_selectors = [
                'div[class*="author"]',
                'span[class*="author"]',
                'a[href*="/profile/"]',
                'div[class*="contributor"]',
                'span[class*="name"]'
            ]
            
            for selector in author_selectors:
                author_elems = item.select(selector)
                if author_elems:
                    for author_elem in author_elems:
                        author_name = author_elem.get_text(strip=True)
                        if author_name and len(author_name) < 100 and author_name not in authors:
                            authors.append(author_name)
                    break
            
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
            
            # 提取文档类型
            document_type = ""
            type_selectors = [
                'span[class*="type"]',
                'div[class*="type"]',
                'span[class*="category"]'
            ]
            
            for selector in type_selectors:
                type_elem = item.select_one(selector)
                if type_elem:
                    document_type = type_elem.get_text(strip=True)
                    break
            
            # 提取PDF链接（如果可用）
            pdf_url = ""
            pdf_selectors = [
                'a[href*=".pdf"]',
                'a[class*="download"]',
                'a:contains("Download")',
                'a:contains("PDF")',
                'button[class*="download"]'
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
            if not pdf_url and document_url:
                pdf_url = self._try_to_find_pdf_url(document_url)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': '',  # 摘要通常需要访问详细页面
                'published': year,
                'pdf_url': pdf_url,
                'document_url': document_url,
                'source': 'Academia.edu',
                'document_type': document_type,
                'open_access': bool(pdf_url),  # 如果有PDF链接，认为是开放获取
                'year': year
            }
            
        except Exception as e:
            self.logger.error(f"解析Academia.edu文档条目详情失败: {e}")
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
    
    def _try_to_find_pdf_url(self, document_url: str) -> str:
        """尝试从文档页面找到PDF链接"""
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(document_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找PDF链接
            pdf_selectors = [
                'a[href*=".pdf"]',
                'a[data-testid="download"]',
                'a[class*="download"]',
                'a:contains("Download")',
                'a:contains("PDF")',
                'button[data-testid="download"]',
                'button[class*="download"]'
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
            self.logger.warning(f"尝试查找PDF链接失败 {document_url}: {e}")
            return ""
    
    def get_document_by_url(self, document_url: str) -> Optional[Dict]:
        """通过Academia.edu URL获取文档详情"""
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(document_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取详细信息
            title = ""
            title_selectors = [
                'h1[class*="document-title"]',
                'h1[data-testid="document-title"]',
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
                    if author_name and len(author_name) < 100:
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
            pdf_url = self._try_to_find_pdf_url(document_url)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': '',
                'pdf_url': pdf_url,
                'document_url': document_url,
                'source': 'Academia.edu',
                'open_access': bool(pdf_url)
            }
            
        except Exception as e:
            self.logger.error(f"获取Academia.edu文档详情失败 {document_url}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查Academia.edu是否可用"""
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
            
            self.logger.info(f"Academia.edu PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Academia.edu PDF下载失败: {e}")
            return False