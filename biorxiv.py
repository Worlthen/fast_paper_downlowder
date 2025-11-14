import requests
import xml.etree.ElementTree as ET
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class BioRxivSearcher:
    """bioRxiv/medRxiv平台搜索器 - 生命科学预印本"""
    
    def __init__(self):
        self.base_url = "https://api.biorxiv.org"
        self.search_endpoint = f"{self.base_url}/details"
        self.name = "bioRxiv/medRxiv"
        self.max_results = 50
        self.rate_limit_delay = 1  # bioRxiv API速率限制
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20, server: str = "biorxiv") -> List[Dict]:
        """
        搜索bioRxiv/medRxiv预印本论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            server: 服务器选择 ("biorxiv" 或 "medrxiv")
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建bioRxiv API查询
            params = {
                'query': query,
                'limit': min(max_results, self.max_results),
                'format': 'json'
            }
            
            # 构建完整的搜索URL
            search_url = f"{self.search_endpoint}/{server}"
            
            self.logger.info(f"搜索{server}: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_biorxiv_response(data, server)
            
        except requests.RequestException as e:
            self.logger.error(f"{server}搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"{server} JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"{server}搜索解析失败: {e}")
            return []
    
    def _parse_biorxiv_response(self, data: Dict, server: str) -> List[Dict]:
        """解析bioRxiv/medRxiv API响应"""
        papers = []
        
        try:
            # bioRxiv API响应结构
            collection = data.get('collection', [])
            
            for item in collection:
                try:
                    paper = self._parse_biorxiv_article(item, server)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析{server}文章失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析{server}响应失败: {e}")
            
        return papers
    
    def _parse_biorxiv_article(self, article: Dict, server: str) -> Optional[Dict]:
        """解析单个bioRxiv/medRxiv文章"""
        try:
            # 提取基本信息
            title = article.get('title', '')
            
            # 作者 - bioRxiv提供作者列表
            authors = []
            authors_data = article.get('authors', [])
            for author in authors_data:
                if isinstance(author, str):
                    authors.append(author)
                elif isinstance(author, dict):
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
            
            # 摘要
            abstract = article.get('abstract', '')
            
            # 发表日期
            published = ""
            date = article.get('date', '')
            if date:
                published = date
            
            # DOI
            doi = article.get('doi', '')
            
            # 获取PDF链接
            pdf_url = ""
            
            # 构建PDF URL
            if server == "biorxiv":
                # bioRxiv PDF URL格式
                biorxiv_id = article.get('biorxiv_id', '')
                if biorxiv_id:
                    pdf_url = f"https://www.biorxiv.org/content/{biorxiv_id}.full.pdf"
            elif server == "medrxiv":
                # medRxiv PDF URL格式
                medrxiv_id = article.get('medrxiv_id', '')
                if medrxiv_id:
                    pdf_url = f"https://www.medrxiv.org/content/{medrxiv_id}.full.pdf"
            
            # 如果没有ID，尝试从DOI构建
            if not pdf_url and doi:
                # 从DOI提取ID部分
                doi_parts = doi.split('/')
                if len(doi_parts) >= 2:
                    article_id = doi_parts[-1]
                    if server == "biorxiv":
                        pdf_url = f"https://www.biorxiv.org/content/early/{published}/{article_id}.full.pdf"
                    elif server == "medrxiv":
                        pdf_url = f"https://www.medrxiv.org/content/early/{published}/{article_id}.full.pdf"
            
            # 获取文章URL
            article_url = ""
            if doi:
                article_url = f"https://doi.org/{doi}"
            elif server == "biorxiv" and article.get('biorxiv_id'):
                biorxiv_id = article.get('biorxiv_id')
                article_url = f"https://www.biorxiv.org/content/{biorxiv_id}"
            elif server == "medrxiv" and article.get('medrxiv_id'):
                medrxiv_id = article.get('medrxiv_id')
                article_url = f"https://www.medrxiv.org/content/{medrxiv_id}"
            
            # 获取文章ID
            article_id = ""
            if server == "biorxiv":
                article_id = article.get('biorxiv_id', '')
            elif server == "medrxiv":
                article_id = article.get('medrxiv_id', '')
            
            # 分类/关键词
            keywords = []
            category = article.get('category', '')
            if category:
                keywords.append(category)
            
            # 服务器信息
            server_info = {
                'name': server,
                'full_name': 'bioRxiv' if server == 'biorxiv' else 'medRxiv'
            }
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'article_url': article_url,
                'source': server_info['full_name'],
                'server': server,
                'article_id': article_id,
                'doi': doi,
                'keywords': keywords,
                'category': category,
                'open_access': True,  # bioRxiv/medRxiv是开放获取
                'citation_count': None,  # 预印本平台不直接提供引用数
                'preprint': True  # 标记为预印本
            }
            
        except Exception as e:
            self.logger.error(f"解析{server}文章详情失败: {e}")
            return None
    
    def search_both_servers(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        同时搜索bioRxiv和medRxiv
        
        Args:
            query: 搜索关键词
            max_results: 每个服务器的最大结果数
            
        Returns:
            合并的论文列表
        """
        all_papers = []
        
        try:
            # 搜索bioRxiv
            biorxiv_papers = self.search(query, max_results // 2, "biorxiv")
            all_papers.extend(biorxiv_papers)
            
            # 搜索medRxiv
            medrxiv_papers = self.search(query, max_results // 2, "medrxiv")
            all_papers.extend(medrxiv_papers)
            
            # 去重（基于DOI）
            seen_dois = set()
            unique_papers = []
            for paper in all_papers:
                doi = paper.get('doi', '')
                if doi and doi not in seen_dois:
                    seen_dois.add(doi)
                    unique_papers.append(paper)
                elif not doi:
                    # 没有DOI的论文也保留
                    unique_papers.append(paper)
            
            return unique_papers
            
        except Exception as e:
            self.logger.error(f"搜索bioRxiv/medRxiv失败: {e}")
            return []
    
    def get_recent_papers(self, days: int = 7, server: str = "biorxiv", max_results: int = 20) -> List[Dict]:
        """获取最近发表的论文"""
        try:
            # 构建获取最近论文的URL
            recent_url = f"{self.base_url}/details/{server}/recent"
            params = {
                'days': days,
                'limit': min(max_results, self.max_results),
                'format': 'json'
            }
            
            self.logger.info(f"获取{server}最近{days}天的论文")
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(recent_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_biorxiv_response(data, server)
            
        except Exception as e:
            self.logger.error(f"获取{server}最近论文失败: {e}")
            return []
    
    def get_paper_by_doi(self, doi: str, server: str = "biorxiv") -> Optional[Dict]:
        """通过DOI获取特定论文"""
        try:
            # 清理DOI格式
            doi = doi.strip()
            if doi.startswith('doi:'):
                doi = doi[4:]
            
            params = {
                'doi': doi,
                'format': 'json'
            }
            
            search_url = f"{self.base_url}/details/{server}"
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            papers = self._parse_biorxiv_response(data, server)
            
            return papers[0] if papers else None
            
        except Exception as e:
            self.logger.error(f"通过DOI获取{server}论文失败 {doi}: {e}")
            return None
    
    def check_server_availability(self, server: str = "biorxiv") -> bool:
        """检查特定服务器是否可用"""
        try:
            test_url = f"{self.base_url}/details/{server}"
            params = {
                'limit': 1,
                'format': 'json'
            }
            
            response = requests.get(test_url, params=params, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def check_availability(self) -> bool:
        """检查bioRxiv/medRxiv API是否可用（默认检查bioRxiv）"""
        return self.check_server_availability("biorxiv")
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # bioRxiv/medRxiv通常不需要特殊的headers
            response = requests.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"bioRxiv/medRxiv PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"bioRxiv/medRxiv PDF下载失败: {e}")
            return False