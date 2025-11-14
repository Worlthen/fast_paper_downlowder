import requests
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class CORESearcher:
    """CORE平台搜索器 - 全球开放获取论文库"""
    
    def __init__(self):
        self.base_url = "https://api.core.ac.uk/v3"
        self.search_endpoint = f"{self.base_url}/search/works"
        self.name = "CORE"
        self.max_results = 50
        self.rate_limit_delay = 0.5  # CORE API速率限制
        self.logger = logging.getLogger(__name__)
        # 注意：CORE API可能需要API密钥，这里使用免费版本
        self.api_key = None  # 如果需要，可以在这里设置API密钥
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索CORE开放获取论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建CORE API查询
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            params = {
                'q': query,
                'limit': min(max_results, self.max_results),
                'sort': 'relevance',
                'scroll': False
            }
            
            self.logger.info(f"搜索CORE: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.search_endpoint, headers=headers, params=params, timeout=30)
            
            # 处理不同的响应状态
            if response.status_code == 401:
                self.logger.warning("CORE API需要认证，尝试无认证访问")
                # 尝试无认证访问（限制更严格）
                time.sleep(self.rate_limit_delay * 2)
                response = requests.get(self.search_endpoint, params=params, timeout=30)
            
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_core_response(data)
            
        except requests.RequestException as e:
            self.logger.error(f"CORE搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"CORE JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"CORE搜索解析失败: {e}")
            return []
    
    def _parse_core_response(self, data: Dict) -> List[Dict]:
        """解析CORE API响应"""
        papers = []
        
        try:
            # CORE API响应结构可能不同
            results = data.get('results', [])
            if not results and isinstance(data, list):
                results = data  # 有些版本直接返回列表
            
            for result in results:
                try:
                    paper = self._parse_core_work(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析CORE论文失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析CORE响应失败: {e}")
            
        return papers
    
    def _parse_core_work(self, work: Dict) -> Optional[Dict]:
        """解析单个CORE论文"""
        try:
            # 提取基本信息
            title = work.get('title', '')
            
            # 作者 - CORE可能有不同的格式
            authors = []
            authors_data = work.get('authors', [])
            if isinstance(authors_data, list):
                for author in authors_data:
                    if isinstance(author, str):
                        authors.append(author)
                    elif isinstance(author, dict):
                        name = author.get('name', '')
                        if name:
                            authors.append(name)
            elif isinstance(authors_data, str):
                authors = [authors_data]
            
            # 摘要
            abstract = work.get('abstract', '')
            if not abstract:
                # 尝试其他可能的字段
                abstract = work.get('description', '')
            
            # 发表日期
            published = ""
            date_published = work.get('publishedDate') or work.get('datePublished') or work.get('year')
            if date_published:
                published = str(date_published)
                # 尝试标准化日期格式
                if len(published) == 4:  # 只有年份
                    published += "-01-01"
                elif len(published) == 7:  # 年月
                    published += "-01"
            
            # DOI
            doi = work.get('doi', '')
            
            # 期刊信息
            journal_title = ""
            journal_data = work.get('journal', {})
            if isinstance(journal_data, dict):
                journal_title = journal_data.get('title', '')
            elif isinstance(journal_data, str):
                journal_title = journal_data
            
            # 获取下载链接
            download_url = ""
            
            # 尝试不同的链接字段
            full_text = work.get('fullText', '')
            if full_text and self._is_pdf_url(full_text):
                download_url = full_text
            
            # 尝试fullTextIdentifier
            if not download_url:
                full_text_identifier = work.get('fullTextIdentifier', '')
                if full_text_identifier and self._is_pdf_url(full_text_identifier):
                    download_url = full_text_identifier
            
            # 尝试links
            if not download_url:
                links = work.get('links', [])
                for link in links:
                    if isinstance(link, dict):
                        url = link.get('url', '')
                        if url and self._is_pdf_url(url):
                            download_url = url
                            break
            
            # 尝试repositories
            if not download_url:
                repositories = work.get('repositories', [])
                for repo in repositories:
                    if isinstance(repo, dict):
                        url = repo.get('url', '')
                        if url and self._is_pdf_url(url):
                            download_url = url
                            break
            
            # 语言
            language = work.get('language', 'en')
            if isinstance(language, list) and language:
                language = language[0]
            elif not language:
                language = 'en'
            
            # 关键词
            keywords = []
            subjects = work.get('subjects', [])
            if isinstance(subjects, list):
                keywords = [str(subject) for subject in subjects if subject]
            
            # CORE ID
            core_id = work.get('id', '')
            
            # 出版商
            publisher = work.get('publisher', '')
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': download_url,
                'source': 'CORE',
                'core_id': core_id,
                'doi': doi,
                'journal': journal_title,
                'publisher': publisher,
                'language': language,
                'keywords': keywords,
                'open_access': True,  # CORE主要收录开放获取内容
                'citation_count': work.get('citationCount'),
                'download_url': download_url
            }
            
        except Exception as e:
            self.logger.error(f"解析CORE论文详情失败: {e}")
            return None
    
    def _is_pdf_url(self, url: str) -> bool:
        """检查URL是否指向PDF文件"""
        if not url:
            return False
        
        url_lower = url.lower()
        # 检查URL后缀
        if url_lower.endswith('.pdf'):
            return True
        
        # 检查URL中是否包含pdf关键词
        pdf_indicators = ['pdf', 'download', 'fulltext']
        return any(indicator in url_lower for indicator in pdf_indicators)
    
    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """通过DOI搜索论文"""
        try:
            # CORE支持DOI搜索
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            params = {
                'q': f'doi:"{doi}"',
                'limit': 1
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, headers=headers, params=params, timeout=30)
            
            if response.status_code == 401:
                time.sleep(self.rate_limit_delay * 2)
                response = requests.get(self.search_endpoint, params=params, timeout=30)
            
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results:
                return self._parse_core_work(results[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"CORE DOI搜索失败 {doi}: {e}")
            return None
    
    def search_by_publisher(self, publisher: str, max_results: int = 20) -> List[Dict]:
        """按出版商搜索"""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            params = {
                'q': f'publisher:"{publisher}"',
                'limit': min(max_results, self.max_results)
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, headers=headers, params=params, timeout=30)
            
            if response.status_code == 401:
                time.sleep(self.rate_limit_delay * 2)
                response = requests.get(self.search_endpoint, params=params, timeout=30)
            
            response.raise_for_status()
            
            data = response.json()
            return self._parse_core_response(data)
            
        except Exception as e:
            self.logger.error(f"CORE出版商搜索失败: {e}")
            return []
    
    def check_availability(self) -> bool:
        """检查CORE API是否可用"""
        try:
            params = {
                'q': 'test',
                'limit': 1
            }
            
            response = requests.get(self.search_endpoint, params=params, timeout=10)
            return response.status_code in [200, 401]  # 401也表示API可达，只是需要认证
        except:
            return False
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # 添加User-Agent头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"CORE PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"CORE PDF下载失败: {e}")
            return False