import requests
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class ZenodoSearcher:
    """Zenodo平台搜索器 - 研究数据仓储"""
    
    def __init__(self):
        self.base_url = "https://zenodo.org/api"
        self.search_endpoint = f"{self.base_url}/records"
        self.name = "Zenodo"
        self.max_results = 50
        self.rate_limit_delay = 0.5  # Zenodo API速率限制
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索Zenodo研究记录
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建Zenodo API查询
            params = {
                'q': query,
                'size': min(max_results, self.max_results),
                'sort': 'bestmatch',
                'access_right': 'open',  # 只搜索开放获取的内容
                'type': 'publication'   # 只搜索出版物
            }
            
            self.logger.info(f"搜索Zenodo: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析JSON响应
            data = response.json()
            return self._parse_zenodo_response(data)
            
        except requests.RequestException as e:
            self.logger.error(f"Zenodo搜索请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Zenodo JSON解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Zenodo搜索解析失败: {e}")
            return []
    
    def _parse_zenodo_response(self, data: Dict) -> List[Dict]:
        """解析Zenodo API响应"""
        papers = []
        
        try:
            # Zenodo API响应结构
            hits = data.get('hits', {})
            records = hits.get('hits', [])
            
            for record in records:
                try:
                    paper = self._parse_zenodo_record(record)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析Zenodo记录失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"解析Zenodo响应失败: {e}")
            
        return papers
    
    def _parse_zenodo_record(self, record: Dict) -> Optional[Dict]:
        """解析单个Zenodo记录"""
        try:
            # 提取基本信息
            metadata = record.get('metadata', {})
            
            title = metadata.get('title', '')
            
            # 作者
            authors = []
            creators = metadata.get('creators', [])
            for creator in creators:
                if isinstance(creator, dict):
                    name = creator.get('name', '')
                    if name:
                        authors.append(name)
            
            # 摘要/描述
            abstract = metadata.get('description', '')
            
            # 发表日期
            published = ""
            publication_date = metadata.get('publication_date')
            if publication_date:
                published = publication_date
            else:
                # 使用创建日期作为备选
                created = record.get('created')
                if created:
                    published = created[:10]  # 只取日期部分
            
            # DOI
            doi = metadata.get('doi', '')
            
            # 期刊信息（如果有）
            journal = ""
            journal_title = metadata.get('journal', {}).get('title', '')
            if journal_title:
                journal = journal_title
            
            # 获取PDF链接
            pdf_url = ""
            files = record.get('files', [])
            
            # 优先选择PDF文件
            for file in files:
                if isinstance(file, dict):
                    file_type = file.get('type', '').lower()
                    file_key = file.get('key', '').lower()
                    
                    if file_type == 'pdf' or file_key.endswith('.pdf'):
                        pdf_url = file.get('links', {}).get('self', '')
                        if pdf_url:
                            break
            
            # 如果没有直接的PDF链接，尝试其他文件类型
            if not pdf_url and files:
                for file in files:
                    if isinstance(file, dict):
                        file_url = file.get('links', {}).get('self', '')
                        if file_url:
                            pdf_url = file_url
                            break
            
            # 记录ID
            record_id = record.get('id', '')
            
            # 记录URL
            record_url = record.get('links', {}).get('self', '')
            
            # 资源类型
            resource_type = metadata.get('resource_type', {}).get('type', '')
            
            # 关键词/主题
            keywords = []
            subjects = metadata.get('subjects', [])
            keywords.extend([str(subject) for subject in subjects if subject])
            
            # 添加关键词字段
            keywords.extend(metadata.get('keywords', []))
            
            # 语言
            language = metadata.get('language', 'eng')
            
            # 许可证
            license_info = ""
            license_data = metadata.get('license', {})
            if isinstance(license_data, dict):
                license_info = license_data.get('id', '')
            elif isinstance(license_data, str):
                license_info = license_data
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'source': 'Zenodo',
                'record_id': record_id,
                'record_url': record_url,
                'doi': doi,
                'journal': journal,
                'resource_type': resource_type,
                'keywords': keywords,
                'language': language,
                'license': license_info,
                'open_access': True,  # 我们搜索的是开放获取内容
                'citation_count': None,  # Zenodo不直接提供引用数
                'files_count': len(files)
            }
            
        except Exception as e:
            self.logger.error(f"解析Zenodo记录详情失败: {e}")
            return None
    
    def search_by_type(self, query: str, record_type: str, max_results: int = 20) -> List[Dict]:
        """按记录类型搜索"""
        try:
            params = {
                'q': query,
                'size': min(max_results, self.max_results),
                'sort': 'bestmatch',
                'access_right': 'open',
                'type': record_type
            }
            
            self.logger.info(f"搜索Zenodo {record_type}类型: {query}")
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_zenodo_response(data)
            
        except Exception as e:
            self.logger.error(f"Zenodo按类型搜索失败: {e}")
            return []
    
    def get_record_by_id(self, record_id: str) -> Optional[Dict]:
        """通过记录ID获取特定记录"""
        try:
            url = f"{self.base_url}/records/{record_id}"
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            record_data = response.json()
            return self._parse_zenodo_record(record_data)
            
        except Exception as e:
            self.logger.error(f"获取Zenodo记录失败 {record_id}: {e}")
            return None
    
    def get_record_by_doi(self, doi: str) -> Optional[Dict]:
        """通过DOI获取特定记录"""
        try:
            # Zenodo支持DOI查询
            params = {
                'q': f'doi:{doi}',
                'size': 1
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.search_endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            hits = data.get('hits', {})
            records = hits.get('hits', [])
            
            if records:
                return self._parse_zenodo_record(records[0])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Zenodo DOI搜索失败 {doi}: {e}")
            return None
    
    def search_communities(self, query: str, max_results: int = 20) -> List[Dict]:
        """搜索Zenodo社区"""
        try:
            communities_url = f"{self.base_url}/communities"
            params = {
                'q': query,
                'size': min(max_results, self.max_results),
                'sort': 'bestmatch'
            }
            
            self.logger.info(f"搜索Zenodo社区: {query}")
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(communities_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            communities = []
            
            hits = data.get('hits', {})
            records = hits.get('hits', [])
            
            for record in records:
                try:
                    metadata = record.get('metadata', {})
                    community = {
                        'title': metadata.get('title', ''),
                        'description': metadata.get('description', ''),
                        'id': record.get('id', ''),
                        'links': record.get('links', {})
                    }
                    communities.append(community)
                except Exception as e:
                    self.logger.warning(f"解析Zenodo社区失败: {e}")
                    continue
            
            return communities
            
        except Exception as e:
            self.logger.error(f"Zenodo社区搜索失败: {e}")
            return []
    
    def check_availability(self) -> bool:
        """检查Zenodo API是否可用"""
        try:
            params = {
                'q': 'test',
                'size': 1
            }
            
            response = requests.get(self.search_endpoint, params=params, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # Zenodo通常不需要特殊的headers
            response = requests.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"Zenodo PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Zenodo PDF下载失败: {e}")
            return False