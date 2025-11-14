import requests
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class SemanticScholarSearcher:
    """Semantic Scholar平台搜索器 - AI驱动的学术搜索引擎"""
    
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.search_endpoint = f"{self.base_url}/paper/search"
        self.name = "Semantic Scholar"
        self.max_results = 50
        self.rate_limit_delay = 0.1  # Semantic Scholar API速率限制较宽松
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索Semantic Scholar论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建Semantic Scholar API查询
            params = {
                'query': query,
                'limit': min(max_results, self.max_results),
                'fields': 'title,authors,abstract,year,venue,openAccessPdf,doi,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationTypes,publicationDate,journal'
            }
            
            self.logger.info(f"搜索Semantic Scholar: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_semantic_scholar_response(data)
            
        except requests.RequestException as e:
            self.logger.error(f"Semantic Scholar搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Semantic Scholar JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Semantic Scholar搜索解析失败: {e}")
            return []
    
    def _parse_semantic_scholar_response(self, data: Dict) -> List[Dict]:
        """解析Semantic Scholar API响应"""
        papers = []
        
        try:
            # Semantic Scholar API响应结构
            results = data.get('data', [])
            
            for result in results:
                try:
                    paper = self._parse_semantic_scholar_paper(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析Semantic Scholar论文失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析Semantic Scholar响应失败: {e}")
            
        return papers
    
    def _parse_semantic_scholar_paper(self, paper: Dict) -> Optional[Dict]:
        """解析单个Semantic Scholar论文"""
        try:
            # 提取基本信息
            title = paper.get('title', '')
            
            # 作者 - Semantic Scholar提供结构化作者信息
            authors = []
            authors_data = paper.get('authors', [])
            for author in authors_data:
                if isinstance(author, dict):
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
            
            # 摘要
            abstract = paper.get('abstract', '')
            
            # 发表日期
            published = ""
            publication_date = paper.get('publicationDate')
            year = paper.get('year')
            
            if publication_date:
                published = publication_date
            elif year:
                published = str(year)
            
            # DOI
            doi = paper.get('doi', '')
            
            # 期刊信息
            journal = ""
            venue = paper.get('venue', '')
            if venue:
                if isinstance(venue, str):
                    journal = venue
                elif isinstance(venue, dict):
                    journal = venue.get('name', '')
            
            # 获取开放获取PDF链接
            pdf_url = ""
            open_access_pdf = paper.get('openAccessPdf')
            if open_access_pdf and isinstance(open_access_pdf, dict):
                pdf_url = open_access_pdf.get('url', '')
            elif isinstance(open_access_pdf, str):
                pdf_url = open_access_pdf
            
            # 获取论文ID
            paper_id = paper.get('paperId', '')
            
            # 引用信息
            citation_count = paper.get('citationCount', 0)
            reference_count = paper.get('referenceCount', 0)
            influential_citation_count = paper.get('influentialCitationCount', 0)
            
            # 研究领域
            fields_of_study = paper.get('fieldsOfStudy', [])
            if isinstance(fields_of_study, str):
                fields_of_study = [fields_of_study]
            
            # 出版类型
            publication_types = paper.get('publicationTypes', [])
            if isinstance(publication_types, str):
                publication_types = [publication_types]
            
            # 判断是否为开放获取
            is_open_access = bool(pdf_url) or paper.get('isOpenAccess', False)
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'source': 'Semantic Scholar',
                'paper_id': paper_id,
                'doi': doi,
                'journal': journal,
                'citation_count': citation_count,
                'reference_count': reference_count,
                'influential_citation_count': influential_citation_count,
                'fields_of_study': fields_of_study,
                'publication_types': publication_types,
                'open_access': is_open_access,
                'venue': venue
            }
            
        except Exception as e:
            self.logger.error(f"解析Semantic Scholar论文详情失败: {e}")
            return None
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        """通过Semantic Scholar ID获取特定论文"""
        try:
            url = f"{self.base_url}/paper/{paper_id}"
            params = {
                'fields': 'title,authors,abstract,year,venue,openAccessPdf,doi,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationTypes,publicationDate,journal'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            paper_data = response.json()
            return self._parse_semantic_scholar_paper(paper_data)
            
        except Exception as e:
            self.logger.error(f"获取Semantic Scholar论文失败 {paper_id}: {e}")
            return None
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """通过DOI获取特定论文"""
        try:
            url = f"{self.base_url}/paper/DOI:{doi}"
            params = {
                'fields': 'title,authors,abstract,year,venue,openAccessPdf,doi,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationTypes,publicationDate,journal'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            paper_data = response.json()
            return self._parse_semantic_scholar_paper(paper_data)
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar DOI搜索失败 {doi}: {e}")
            return None
    
    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """通过arXiv ID获取特定论文"""
        try:
            url = f"{self.base_url}/paper/ARXIV:{arxiv_id}"
            params = {
                'fields': 'title,authors,abstract,year,venue,openAccessPdf,doi,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationTypes,publicationDate,journal'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            paper_data = response.json()
            return self._parse_semantic_scholar_paper(paper_data)
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar arXiv ID搜索失败 {arxiv_id}: {e}")
            return None
    
    def search_by_author(self, author_name: str, max_results: int = 20) -> List[Dict]:
        """按作者姓名搜索"""
        try:
            # 先搜索作者ID
            author_search_url = f"{self.base_url}/author/search"
            params = {
                'query': author_name,
                'limit': 5  # 取前5个匹配的作者
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(author_search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            authors = data.get('data', [])
            
            if not authors:
                return []
            
            # 获取第一个匹配作者的论文
            author_id = authors[0].get('authorId')
            if not author_id:
                return []
            
            # 获取该作者的论文
            author_papers_url = f"{self.base_url}/author/{author_id}/papers"
            params = {
                'limit': min(max_results, self.max_results),
                'fields': 'title,authors,abstract,year,venue,openAccessPdf,doi,citationCount,referenceCount,influentialCitationCount,fieldsOfStudy,publicationTypes,publicationDate,journal'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(author_papers_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            papers = data.get('data', [])
            
            parsed_papers = []
            for paper in papers:
                parsed_paper = self._parse_semantic_scholar_paper(paper)
                if parsed_paper:
                    parsed_papers.append(parsed_paper)
            
            return parsed_papers
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar作者搜索失败: {e}")
            return []
    
    def check_availability(self) -> bool:
        """检查Semantic Scholar API是否可用"""
        try:
            params = {
                'query': 'test',
                'limit': 1,
                'fields': 'title'
            }
            
            response = requests.get(self.search_endpoint, params=params, timeout=10)
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
            
            self.logger.info(f"Semantic Scholar PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar PDF下载失败: {e}")
            return False