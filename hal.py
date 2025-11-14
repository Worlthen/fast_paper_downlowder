import requests
import xml.etree.ElementTree as ET
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class HALSearcher:
    """HAL平台搜索器 - 法国开放获取仓储"""
    
    def __init__(self):
        self.base_url = "https://api.archives-ouvertes.fr"
        self.search_endpoint = f"{self.base_url}/search"
        self.name = "HAL"
        self.max_results = 50
        self.rate_limit_delay = 1  # HAL API速率限制
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索HAL开放获取论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建HAL API查询
            params = {
                'q': query,
                'rows': min(max_results, self.max_results),
                'sort': 'relevance desc',
                'wt': 'json',  # 返回JSON格式
                'fl': 'title_s,authFullName_s,abstract_s,producedDate_s,doiId_s,uri_s,fileMain_s,keyword_s,journalTitle_s,docType_s,language_s'  # 指定返回字段
            }
            
            self.logger.info(f"搜索HAL: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_hal_response(data)
            
        except requests.RequestException as e:
            self.logger.error(f"HAL搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"HAL JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"HAL搜索解析失败: {e}")
            return []
    
    def _parse_hal_response(self, data: Dict) -> List[Dict]:
        """解析HAL API响应"""
        papers = []
        
        try:
            # HAL API响应结构
            response = data.get('response', {})
            docs = response.get('docs', [])
            
            for doc in docs:
                try:
                    paper = self._parse_hal_document(doc)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析HAL文档失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析HAL响应失败: {e}")
            
        return papers
    
    def _parse_hal_document(self, doc: Dict) -> Optional[Dict]:
        """解析单个HAL文档"""
        try:
            # 提取标题
            title = ""
            title_s = doc.get('title_s', [])
            if isinstance(title_s, list) and title_s:
                title = title_s[0]
            elif isinstance(title_s, str):
                title = title_s
            
            # 作者
            authors = []
            auth_full_names = doc.get('authFullName_s', [])
            if isinstance(auth_full_names, list):
                authors = auth_full_names
            elif isinstance(auth_full_names, str):
                authors = [auth_full_names]
            
            # 摘要
            abstract = ""
            abstract_s = doc.get('abstract_s', [])
            if isinstance(abstract_s, list) and abstract_s:
                abstract = abstract_s[0]
            elif isinstance(abstract_s, str):
                abstract = abstract_s
            
            # 发表日期
            published = ""
            produced_date = doc.get('producedDate_s', [])
            if isinstance(produced_date, list) and produced_date:
                published = produced_date[0]
            elif isinstance(produced_date, str):
                published = produced_date
            
            # DOI
            doi = ""
            doi_id = doc.get('doiId_s', [])
            if isinstance(doi_id, list) and doi_id:
                doi = doi_id[0]
            elif isinstance(doi_id, str):
                doi = doi_id
            
            # 期刊标题
            journal_title = ""
            journal_title_s = doc.get('journalTitle_s', [])
            if isinstance(journal_title_s, list) and journal_title_s:
                journal_title = journal_title_s[0]
            elif isinstance(journal_title_s, str):
                journal_title = journal_title_s
            
            # 获取PDF链接
            pdf_url = ""
            file_main = doc.get('fileMain_s', [])
            if isinstance(file_main, list) and file_main:
                pdf_url = file_main[0]
            elif isinstance(file_main, str):
                pdf_url = file_main
            
            # 构建完整的PDF URL（如果需要）
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = urljoin(self.base_url, pdf_url)
            
            # 记录URL
            uri = ""
            uri_s = doc.get('uri_s', [])
            if isinstance(uri_s, list) and uri_s:
                uri = uri_s[0]
            elif isinstance(uri_s, str):
                uri = uri_s
            
            # 关键词
            keywords = []
            keyword_s = doc.get('keyword_s', [])
            if isinstance(keyword_s, list):
                keywords = keyword_s
            elif isinstance(keyword_s, str):
                keywords = [keyword_s]
            
            # 文档类型
            doc_type = ""
            doc_type_s = doc.get('docType_s', [])
            if isinstance(doc_type_s, list) and doc_type_s:
                doc_type = doc_type_s[0]
            elif isinstance(doc_type_s, str):
                doc_type = doc_type_s
            
            # 语言
            language = ""
            language_s = doc.get('language_s', [])
            if isinstance(language_s, list) and language_s:
                language = language_s[0]
            elif isinstance(language_s, str):
                language = language_s
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'source': 'HAL',
                'uri': uri,
                'doi': doi,
                'journal': journal_title,
                'keywords': keywords,
                'document_type': doc_type,
                'language': language,
                'open_access': True,  # HAL是开放获取仓储
                'citation_count': None,  # HAL不直接提供引用数
                'hal_id': doc.get('halId_s', '')
            }
            
        except Exception as e:
            self.logger.error(f"解析HAL文档详情失败: {e}")
            return None
    
    def search_by_author(self, author_name: str, max_results: int = 20) -> List[Dict]:
        """按作者姓名搜索"""
        try:
            params = {
                'q': f'authFullName_s:"{author_name}"',
                'rows': min(max_results, self.max_results),
                'sort': 'producedDate_s desc',  # 按日期降序
                'wt': 'json',
                'fl': 'title_s,authFullName_s,abstract_s,producedDate_s,doiId_s,uri_s,fileMain_s,keyword_s,journalTitle_s,docType_s,language_s'
            }
            
            self.logger.info(f"搜索HAL作者: {author_name}")
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_hal_response(data)
            
        except Exception as e:
            self.logger.error(f"HAL作者搜索失败: {e}")
            return []
    
    def search_by_journal(self, journal_title: str, max_results: int = 20) -> List[Dict]:
        """按期刊名称搜索"""
        try:
            params = {
                'q': f'journalTitle_s:"{journal_title}"',
                'rows': min(max_results, self.max_results),
                'sort': 'producedDate_s desc',
                'wt': 'json',
                'fl': 'title_s,authFullName_s,abstract_s,producedDate_s,doiId_s,uri_s,fileMain_s,keyword_s,journalTitle_s,docType_s,language_s'
            }
            
            self.logger.info(f"搜索HAL期刊: {journal_title}")
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_hal_response(data)
            
        except Exception as e:
            self.logger.error(f"HAL期刊搜索失败: {e}")
            return []
    
    def get_document_by_hal_id(self, hal_id: str) -> Optional[Dict]:
        """通过HAL ID获取特定文档"""
        try:
            # 清理ID格式
            hal_id = hal_id.strip()
            if not hal_id.startswith('hal-'):
                hal_id = f"hal-{hal_id}"
            
            params = {
                'q': f'halId_s:"{hal_id}"',
                'rows': 1,
                'wt': 'json',
                'fl': 'title_s,authFullName_s,abstract_s,producedDate_s,doiId_s,uri_s,fileMain_s,keyword_s,journalTitle_s,docType_s,language_s'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            response_data = data.get('response', {})
            docs = response_data.get('docs', [])
            
            if docs:
                return self._parse_hal_document(docs[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取HAL文档失败 {hal_id}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查HAL API是否可用"""
        try:
            params = {
                'q': 'test',
                'rows': 1,
                'wt': 'json'
            }
            
            response = requests.get(self.search_endpoint, params=params, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # HAL通常不需要特殊的headers
            response = requests.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"HAL PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"HAL PDF下载失败: {e}")
            return False