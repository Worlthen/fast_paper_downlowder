import requests
import xml.etree.ElementTree as ET
import time
import logging
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional

class ArXivSearcher:
    """arXiv平台搜索器 - 预印本论文平台"""
    
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.name = "arXiv"
        self.max_results = 50
        self.rate_limit_delay = 3  # arXiv API速率限制
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索arXiv论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 构建arXiv API查询
            search_query = f"all:{quote(query)}"
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': min(max_results, self.max_results),
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            self.logger.info(f"搜索arXiv: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析XML响应
            return self._parse_arxiv_response(response.text)
            
        except requests.RequestException as e:
            self.logger.error(f"arXiv搜索请求失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"arXiv搜索解析失败: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[Dict]:
        """解析arXiv API的XML响应"""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            # 处理命名空间
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # 查找所有论文条目
            entries = root.findall('.//atom:entry', ns)
            
            for entry in entries:
                try:
                    paper = self._parse_entry(entry, ns)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析单个论文条目失败: {e}")
                    continue
                    
        except ET.ParseError as e:
            self.logger.error(f"XML解析失败: {e}")
            
        return papers
    
    def _parse_entry(self, entry, ns) -> Optional[Dict]:
        """解析单个论文条目"""
        try:
            # 提取基本信息
            title = entry.find('atom:title', ns)
            title = title.text.strip() if title is not None else ""
            
            summary = entry.find('atom:summary', ns)
            summary = summary.text.strip() if summary is not None else ""
            
            published = entry.find('atom:published', ns)
            published = published.text[:10] if published is not None else ""  # 只取日期部分
            
            # 提取作者
            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns)
                if name is not None:
                    authors.append(name.text.strip())
            
            # 提取PDF链接
            pdf_url = ""
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    pdf_url = link.get('href')
                    break
            
            # 提取arXiv ID
            arxiv_id = ""
            id_elem = entry.find('atom:id', ns)
            if id_elem is not None:
                arxiv_id = id_elem.text.split('/')[-1]  # 提取最后的ID部分
            
            # 提取分类
            categories = []
            for category in entry.findall('atom:category', ns):
                term = category.get('term')
                if term:
                    categories.append(term)
            
            # 提取评论（如果有）
            comment = ""
            comment_elem = entry.find('arxiv:comment', ns)
            if comment_elem is not None:
                comment = comment_elem.text.strip()
            
            # 提取期刊引用（如果有）
            journal_ref = ""
            journal_elem = entry.find('arxiv:journal_ref', ns)
            if journal_elem is not None:
                journal_ref = journal_elem.text.strip()
            
            return {
                'title': title,
                'authors': authors,
                'abstract': summary,
                'published': published,
                'pdf_url': pdf_url,
                'source': 'arXiv',
                'arxiv_id': arxiv_id,
                'categories': categories,
                'comment': comment,
                'journal_ref': journal_ref,
                'open_access': True,  # arXiv是开放获取
                'citation_count': None,  # arXiv不直接提供引用数
                'doi': None  # 可能需要额外查询获取DOI
            }
            
        except Exception as e:
            self.logger.error(f"解析论文条目失败: {e}")
            return None
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """通过arXiv ID获取特定论文"""
        try:
            # 清理ID格式
            arxiv_id = arxiv_id.strip().replace('arXiv:', '')
            
            params = {
                'id_list': arxiv_id,
                'max_results': 1
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            papers = self._parse_arxiv_response(response.text)
            return papers[0] if papers else None
            
        except Exception as e:
            self.logger.error(f"获取arXiv论文失败 {arxiv_id}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查arXiv API是否可用"""
        try:
            response = requests.get(self.base_url, params={'max_results': 1}, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def download_pdf(self, pdf_url: str, filepath: str) -> bool:
        """下载PDF文件"""
        try:
            # 添加User-Agent头，避免被阻止
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f"PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"PDF下载失败: {e}")
            return False