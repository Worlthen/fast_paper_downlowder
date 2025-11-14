import requests
import xml.etree.ElementTree as ET
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import quote, urljoin

class PubMedCentralSearcher:
    """PubMed Central平台搜索器 - 生物医学文献"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.search_url = f"{self.base_url}/esearch.fcgi"
        self.fetch_url = f"{self.base_url}/efetch.fcgi"
        self.name = "PubMed Central"
        self.max_results = 50
        self.rate_limit_delay = 0.34  # NCBI推荐的最小间隔 (1/3秒)
        self.logger = logging.getLogger(__name__)
        
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        搜索PubMed Central论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            论文列表，包含标题、作者、摘要、PDF链接等信息
        """
        try:
            # 第一步：搜索PMC ID列表
            search_params = {
                'db': 'pmc',
                'term': query,
                'retmax': min(max_results, self.max_results),
                'retmode': 'json',
                'sort': 'relevance'
            }
            
            self.logger.info(f"搜索PubMed Central: {query}")
            
            # 添加速率限制
            time.sleep(self.rate_limit_delay)
            
            search_response = requests.get(self.search_url, params=search_params, timeout=30)
            search_response.raise_for_status()
            
            search_data = search_response.json()
            pmc_ids = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not pmc_ids:
                self.logger.info("PubMed Central未找到相关论文")
                return []
            
            # 第二步：获取详细信息
            return self._fetch_paper_details(pmc_ids)
            
        except requests.RequestException as e:
            self.logger.error(f"PubMed Central搜索请求失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"PubMed Central搜索解析失败: {e}")
            return []
    
    def _fetch_paper_details(self, pmc_ids: List[str]) -> List[Dict]:
        """获取论文详细信息"""
        papers = []
        
        # NCBI建议分批处理，每批不超过20个ID
        batch_size = 20
        for i in range(0, len(pmc_ids), batch_size):
            batch_ids = pmc_ids[i:i+batch_size]
            
            try:
                # 获取XML格式的详细信息
                fetch_params = {
                    'db': 'pmc',
                    'id': ','.join(batch_ids),
                    'retmode': 'xml'
                }
                
                time.sleep(self.rate_limit_delay)
                fetch_response = requests.get(self.fetch_url, params=fetch_params, timeout=60)
                fetch_response.raise_for_status()
                
                # 解析XML响应
                batch_papers = self._parse_pmc_xml(fetch_response.text)
                papers.extend(batch_papers)
                
            except Exception as e:
                self.logger.error(f"批量获取PMC论文详情失败: {e}")
                continue
        
        return papers
    
    def _parse_pmc_xml(self, xml_content: str) -> List[Dict]:
        """解析PMC XML响应"""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # PMC XML可能有不同的根元素
            if root.tag.endswith('pmc-articleset'):
                articles = root.findall('.//article')
            else:
                articles = [root] if root.tag.endswith('article') else []
            
            for article in articles:
                try:
                    paper = self._parse_pmc_article(article)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"解析PMC文章失败: {e}")
                    continue
                    
        except ET.ParseError as e:
            self.logger.error(f"PMC XML解析失败: {e}")
            
        return papers
    
    def _parse_pmc_article(self, article) -> Optional[Dict]:
        """解析单个PMC文章"""
        try:
            # 提取标题
            title = ""
            title_elem = article.find('.//article-title')
            if title_elem is not None:
                title = ET.tostring(title_elem, encoding='unicode', method='text').strip()
            
            # 提取摘要
            abstract = ""
            abstract_elem = article.find('.//abstract')
            if abstract_elem is not None:
                abstract = ET.tostring(abstract_elem, encoding='unicode', method='text').strip()
            
            # 提取作者
            authors = []
            for contrib in article.findall('.//contrib[@contrib-type="author"]'): 
                name_parts = []
                surname = contrib.find('name/surname')
                given_names = contrib.find('name/given-names')
                
                if surname is not None:
                    name_parts.append(surname.text.strip() if surname.text else "")
                if given_names is not None:
                    name_parts.append(given_names.text.strip() if given_names.text else "")
                
                if name_parts:
                    authors.append(' '.join(name_parts))
            
            # 提取发表日期
            published = ""
            pub_date = article.find('.//pub-date[@pub-type="epub"]')
            if pub_date is None:
                pub_date = article.find('.//pub-date[@date-type="pub"]')
            if pub_date is None:
                pub_date = article.find('.//pub-date')
            
            if pub_date is not None:
                year = pub_date.find('year')
                month = pub_date.find('month')
                day = pub_date.find('day')
                
                date_parts = []
                if year is not None and year.text:
                    date_parts.append(year.text)
                if month is not None and month.text:
                    date_parts.append(month.text.zfill(2))
                if day is not None and day.text:
                    date_parts.append(day.text.zfill(2))
                
                if date_parts:
                    published = '-'.join(date_parts)
            
            # 提取PMC ID
            pmc_id = ""
            for article_id in article.findall('.//article-id'):
                if article_id.get('pub-id-type') == 'pmc':
                    pmc_id = article_id.text.strip()
                    break
            
            # 提取DOI
            doi = ""
            for article_id in article.findall('.//article-id'):
                if article_id.get('pub-id-type') == 'doi':
                    doi = article_id.text.strip()
                    break
            
            # 构建PDF链接
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/" if pmc_id else ""
            
            # 提取期刊信息
            journal_title = ""
            journal_elem = article.find('.//journal-title')
            if journal_elem is not None:
                journal_title = journal_elem.text.strip() if journal_elem.text else ""
            
            return {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'published': published,
                'pdf_url': pdf_url,
                'source': 'PubMed Central',
                'pmc_id': pmc_id,
                'doi': doi,
                'journal': journal_title,
                'open_access': True,  # PMC是开放获取
                'citation_count': None,  # 需要额外查询
                'keywords': []  # 可以从其他字段提取关键词
            }
            
        except Exception as e:
            self.logger.error(f"解析PMC文章详情失败: {e}")
            return None
    
    def get_paper_by_pmc_id(self, pmc_id: str) -> Optional[Dict]:
        """通过PMC ID获取特定论文"""
        try:
            # 清理ID格式
            pmc_id = pmc_id.strip().replace('PMC', '')
            
            fetch_params = {
                'db': 'pmc',
                'id': pmc_id,
                'retmode': 'xml'
            }
            
            time.sleep(self.rate_limit_delay)
            response = requests.get(self.fetch_url, params=fetch_params, timeout=30)
            response.raise_for_status()
            
            papers = self._parse_pmc_xml(response.text)
            return papers[0] if papers else None
            
        except Exception as e:
            self.logger.error(f"获取PMC论文失败 {pmc_id}: {e}")
            return None
    
    def check_availability(self) -> bool:
        """检查PubMed Central API是否可用"""
        try:
            test_params = {
                'db': 'pmc',
                'term': 'test',
                'retmax': 1,
                'retmode': 'json'
            }
            
            response = requests.get(self.search_url, params=test_params, timeout=10)
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
            
            self.logger.info(f"PMC PDF下载成功: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"PMC PDF下载失败: {e}")
            return False