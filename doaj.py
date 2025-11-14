import requests
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class DOAJSearcher:
    """DOAJ (Directory of Open Access Journals) 搜索器 - 开放获取期刊"""
    
    def __init__(self):
        self.base_url = "https://doaj.org/api/search/articles"
        self.name = "DOAJ"
        self.max_results = 50
        self.rate_limit_delay = 1  # DOAJ API速率限制
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索DOAJ开放获取期刊论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建DOAJ API查询
            params = {
                'q': query,
                'pageSize': min(max_results, self.max_results),
                'sort': 'relevance',
                'ref': 'homepage'
            }
            
            self.logger.info(f"搜索DOAJ: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_doaj_response(data)
            
        except requests.RequestException as e:
            self.logger.error(f"DOAJ搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"DOAJ JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"DOAJ搜索解析失败: {e}")
            return []
    
    def _parse_doaj_response(self, data: Dict) -> List[Dict]:
        """解析DOAJ API响应"""
        papers = []
        
        try:
            # DOAJ API响应结构
            results = data.get('results', [])
            
            for result in results:
                try:
                    paper = self._parse_doaj_article(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析DOAJ文章失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析DOAJ响应失败: {e}")
            
        return papers
    
    def _parse_doaj_article(self, article: Dict) -> Optional[Dict]:
        """解析单个DOAJ文章"""
        try:
            # 提取基本信息
            bibjson = article.get('bibjson', {})
            
            # 标题
            title = bibjson.get('title', '')
            
            # 作者
            authors = []
            for author in bibjson.get('author', []):
                name_parts = []
                if 'name' in author:
                    authors.append(author['name'])
                else:
                    # 尝试从姓和名组合
                    if 'firstname' in author:
                        name_parts.append(author['firstname'])
                    if 'lastname' in author:
                        name_parts.append(author['lastname'])
                    if name_parts:
                        authors.append(' '.join(name_parts))
            
            # 摘要
            abstract = bibjson.get('abstract', '')
            
            # 发表日期
            published = ""
            year = bibjson.get('year')
            month = bibjson.get('month')
            if year:
                published = str(year)
                if month:
                    published += f"-{str(month).zfill(2)}"
            
            # 期刊信息
            journal = bibjson.get('journal', {})
            journal_title = journal.get('title', '')
            
            # 获取PDF链接
            pdf_url = ""
            for link in bibjson.get('link', []):
                if link.get('type') == 'fulltext' and 'url' in link:
                    url = link['url']
                    # 检查是否为PDF链接
                    if url.lower().endswith('.pdf') or 'pdf' in url.lower():
                        pdf_url = url
                        break
            
            # 获取网页链接
            fulltext_url = ""
            for link in bibjson.get('link', []):
                if link.get('type') == 'fulltext' and 'url' in link:
                    fulltext_url = link['url']
                    break
            
            # 关键词
            keywords = bibjson.get('keywords', [])
            
            # DOI
            identifier = bibjson.get('identifier', [])
            doi = ""
            for ident in identifier:
                if ident.get('type') == 'doi':
                    doi = ident.get('id', '')
                    break
            
            # 语言
            language = bibjson.get('language', [])
            if isinstance(language, list) and language:
                language = language[0]
            elif not language:
                language = "en"
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'fulltext_url': fulltext_url,
                'source': 'DOAJ',
                'journal': journal_title,
                'doi': doi,
                'keywords': keywords,
                'language': language,
                'open_access': True,  # DOAJ只收录开放获取期刊
                'citation_count': None,  # DOAJ不直接提供引用数
                'subject': bibjson.get('subject', [])
            }
            
        except Exception as e:
            self.logger.error(f"解析DOAJ文章详情失败: {e}")
            return None
    
    def search_by_journal(self, journal_name: str, max_results: int = 20) -> List[Dict]:
        """按期刊名称搜索"""
        try:
            # DOAJ支持按期刊搜索
            journal_search_url = "https://doaj.org/api/search/journals"
            params = {
                'q': journal_name,
                'pageSize': 10
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(journal_search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            journals = data.get('results', [])
            
            if not journals:
                return []
            
            # 获取第一个匹配期刊的文章
            journal = journals[0]
            journal_id = journal.get('id')
            
            if journal_id:
                # 使用该期刊的文章搜索接口
                articles_url = f"https://doaj.org/api/search/articles/journal.id:{journal_id}"
                params = {
                    'pageSize': min(max_results, self.max_results),
                    'sort': 'relevance'
                }
                
                time.sleep(self.rate_limit_delay)
                response = requests.get(articles_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                return self._parse_doaj_response(data)
            
            return []
            
        except Exception as e:
            self.logger.error(f"DOAJ按期刊搜索失败: {e}")
            return []
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """通过DOI获取特定论文"""
        try:
            # DOAJ支持DOI搜索
            params = {
                'q': f'doi:{doi}',
                'pageSize': 1
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results:
                return self._parse_doaj_article(results[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"DOAJ DOI搜索失败 {doi}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查DOAJ API是否可用"""
        try:
            params = {
                'q': 'test',
                'pageSize': 1
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            return response.status_code == 200
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
            
            self.logger.info(f"DOAJ PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"DOAJ PDF下载失败: {e}")
            return False