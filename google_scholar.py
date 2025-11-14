"""
Google Scholar搜索模块
负责从Google Scholar搜索学术论文
"""

import re
import time
import random
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger

from config import USER_AGENTS
from paper_parser import PaperInfo


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    title: str
    authors: str
    year: Optional[int]
    journal: Optional[str]
    abstract: Optional[str]
    url: Optional[str]
    pdf_url: Optional[str]
    citation_url: Optional[str]
    cited_by_count: Optional[int]
    related_articles_url: Optional[str]
    snippet: Optional[str]


class GoogleScholarSearcher:
    """Google Scholar搜索器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'https://scholar.google.com')
        self.search_path = self.config.get('search_path', '/scholar')
        self.max_results = self.config.get('max_results', 10)
        self.delay = self.config.get('delay', 2.0)
        self.timeout = self.config.get('timeout', 30)
        self.use_selenium = self.config.get('use_selenium', True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.driver = None
        if self.use_selenium:
            self._init_selenium_driver()
    
    def _init_selenium_driver(self):
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
            
            # 安装并获取ChromeDriver路径
            driver_path = ChromeDriverManager().install()
            self.driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("Selenium WebDriver初始化成功")
            
        except Exception as e:
            logger.warning(f"Selenium WebDriver初始化失败: {e}，将使用requests模式")
            self.use_selenium = False
    
    def search(self, query: str, max_results: int = None) -> List[SearchResult]:
        """搜索学术论文"""
        if max_results is None:
            max_results = self.max_results
        
        logger.info(f"Google Scholar搜索: '{query}' (最多{max_results}个结果)")
        
        try:
            if self.use_selenium:
                return self._search_with_selenium(query, max_results)
            else:
                return self._search_with_requests(query, max_results)
        except Exception as e:
            logger.error(f"Google Scholar搜索失败: {e}")
            return []
    
    def search_paper(self, paper: PaperInfo, max_results: int = None) -> List[SearchResult]:
        """根据PaperInfo搜索论文"""
        query = paper.get_search_query()
        return self.search(query, max_results)
    
    def _search_with_selenium(self, query: str, max_results: int) -> List[SearchResult]:
        """使用Selenium搜索"""
        if not self.driver:
            logger.error("Selenium WebDriver未初始化")
            return []
        
        try:
            # 构建搜索URL
            search_url = f"{self.base_url}{self.search_path}?q={quote_plus(query)}&num={max_results}"
            
            logger.debug(f"访问URL: {search_url}")
            self.driver.get(search_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "gs_r"))
            )
            
            # 添加随机延迟避免被检测
            time.sleep(random.uniform(1, self.delay))
            
            # 解析搜索结果
            return self._parse_selenium_results()
            
        except TimeoutException:
            logger.error("页面加载超时")
            return []
        except Exception as e:
            logger.error(f"Selenium搜索失败: {e}")
            return []
    
    def _search_with_requests(self, query: str, max_results: int) -> List[SearchResult]:
        """使用requests搜索"""
        try:
            # 构建搜索URL
            search_url = f"{self.base_url}{self.search_path}"
            params = {
                'q': query,
                'num': max_results,
                'hl': 'en',
                'as_sdt': '0,5'  # 只显示学术文章
            }
            
            logger.debug(f"请求URL: {search_url}, 参数: {params}")
            
            response = self.session.get(search_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # 添加随机延迟
            time.sleep(random.uniform(0.5, self.delay))
            
            # 解析HTML结果
            return self._parse_html_results(response.text)
            
        except requests.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"Requests搜索失败: {e}")
            return []
    
    def _parse_selenium_results(self) -> List[SearchResult]:
        """解析Selenium搜索结果"""
        results = []
        
        try:
            # 查找所有搜索结果项
            result_elements = self.driver.find_elements(By.CLASS_NAME, "gs_r")
            
            for element in result_elements:
                try:
                    result = self._parse_single_result_selenium(element)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"解析单个结果失败: {e}")
                    continue
            
            logger.info(f"解析到 {len(results)} 个搜索结果")
            return results
            
        except Exception as e:
            logger.error(f"解析Selenium结果失败: {e}")
            return []
    
    def _parse_html_results(self, html: str) -> List[SearchResult]:
        """解析HTML搜索结果"""
        results = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有搜索结果项
            result_elements = soup.find_all('div', class_='gs_r')
            
            for element in result_elements:
                try:
                    result = self._parse_single_result_html(element)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"解析单个结果失败: {e}")
                    continue
            
            logger.info(f"解析到 {len(results)} 个搜索结果")
            return results
            
        except Exception as e:
            logger.error(f"解析HTML结果失败: {e}")
            return []
    
    def _parse_single_result_selenium(self, element) -> Optional[SearchResult]:
        """解析单个Selenium搜索结果"""
        try:
            # 提取标题和链接
            title_elem = element.find_element(By.CSS_SELECTOR, "h3.gs_rt a")
            title = title_elem.text.strip()
            url = title_elem.get_attribute("href")
            
            # 提取作者和出版信息
            authors_elem = element.find_element(By.CSS_SELECTOR, "div.gs_a")
            authors_text = authors_elem.text.strip()
            authors, year, journal = self._parse_author_info(authors_text)
            
            # 提取摘要片段
            snippet_elem = element.find_elements(By.CLASS_NAME, "gs_rs")
            snippet = snippet_elem[0].text.strip() if snippet_elem else None
            
            # 提取PDF链接
            pdf_url = None
            pdf_link_elem = element.find_elements(By.CSS_SELECTOR, "div.gs_ggs a")
            if pdf_link_elem:
                pdf_url = pdf_link_elem[0].get_attribute('href')
            
            # 提取引用链接
            citation_url = None
            cited_by_count = None
            bottom_links = element.find_elements(By.CLASS_NAME, "gs_fl")
            if bottom_links:
                for link in bottom_links[0].find_elements(By.TAG_NAME, "a"):
                    href = link.get_attribute('href')
                    text = link.text
                    if "Cited by" in text:
                        match = re.search(r'Cited by (\d+)', text)
                        if match:
                            cited_by_count = int(match.group(1))
                    elif "scholar?cites=" in href:
                        citation_url = href
            
            return SearchResult(
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                abstract=None, # 从Google搜索结果中很难直接获取完整的摘要
                url=url,
                pdf_url=pdf_url,
                citation_url=citation_url,
                cited_by_count=cited_by_count,
                related_articles_url=None,
                snippet=snippet
            )
            
        except Exception as e:
            logger.debug(f"解析单个Selenium结果失败: {e}")
            return None
    
    def _parse_single_result_html(self, element) -> Optional[SearchResult]:
        """解析单个HTML搜索结果"""
        try:
            # 提取标题
            title_elem = element.find('h3', class_='gs_rt')
            if not title_elem:
                title_elem = element.find(class_='gs_rt')
            title = title_elem.get_text(strip=True) if title_elem else ""
            url_elem = title_elem.find('a') if title_elem else None
            url = url_elem.get('href') if url_elem else None
            
            # 提取作者和出版信息
            authors_elem = element.find('div', class_='gs_a')
            authors_text = authors_elem.get_text(strip=True) if authors_elem else ""
            authors, year, journal = self._parse_author_info(authors_text)
            
            # 提取摘要片段
            snippet_elem = element.find('div', class_='gs_rs')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else None
            
            # 提取PDF链接
            pdf_url = None
            pdf_link_elem = element.select_one('div.gs_ggs a')
            if pdf_link_elem:
                pdf_url = pdf_link_elem.get('href')
            
            # 提取引用信息
            citation_url = None
            cited_by_count = None
            bottom_links = element.find('div', class_='gs_fl')
            if bottom_links:
                for link in bottom_links.find_all('a'):
                    href = link.get('href')
                    text = link.get_text()
                    if "Cited by" in text:
                        match = re.search(r'Cited by (\d+)', text)
                        if match:
                            cited_by_count = int(match.group(1))
                    elif href and "scholar?cites=" in href:
                        citation_url = urljoin(self.base_url, href)
            
            return SearchResult(
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                abstract=None, # 从Google搜索结果中很难直接获取完整的摘要
                url=url,
                pdf_url=pdf_url,
                citation_url=citation_url,
                cited_by_count=cited_by_count,
                related_articles_url=None,
                snippet=snippet
            )
            
        except Exception as e:
            logger.warning(f"解析单个HTML结果失败: {e}")
            return None
    
    def _parse_author_info(self, authors_text: str) -> Tuple[str, Optional[int], Optional[str]]:
        """解析作者信息文本"""
        authors = ""
        year = None
        journal = ""
        
        try:
            # 提取年份
            year_match = re.search(r'\b(19|20)\d{2}\b', authors_text)
            if year_match:
                year = int(year_match.group())
            
            # 分割作者和期刊信息
            parts = re.split(r'\s*-\s*', authors_text)
            
            if len(parts) >= 1:
                authors = parts[0].strip()
            
            if len(parts) >= 2:
                # 第二部分可能包含期刊或其他信息
                journal_part = parts[1].strip()
                # 移除年份信息
                journal = re.sub(r'\b(19|20)\d{2}\b', '', journal_part).strip()
            
        except Exception as e:
            logger.warning(f"解析作者信息失败: {e}, 原文本: {authors_text}")
        
        return authors, year, journal
    
    def get_pdf_url(self, result: SearchResult) -> Optional[str]:
        """获取PDF下载链接"""
        if result.pdf_url:
            return result.pdf_url
        
        # 如果没有直接的PDF链接，尝试访问论文页面获取
        if result.url:
            try:
                logger.debug(f"尝试从论文页面获取PDF: {result.url}")
                response = self.session.get(result.url, timeout=self.timeout)
                
                # 查找PDF链接
                pdf_match = re.search(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', response.text)
                if pdf_match:
                    pdf_url = pdf_match.group(1)
                    # 处理相对URL
                    if pdf_url.startswith('/'):
                        pdf_url = urljoin(self.base_url, pdf_url)
                    
                    logger.info(f"找到PDF链接: {pdf_url}")
                    return pdf_url
                    
            except Exception as e:
                logger.warning(f"获取PDF链接失败: {e}")
        
        return None
    
    def close(self):
        """关闭搜索器"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver已关闭")
            except Exception as e:
                logger.warning(f"关闭WebDriver失败: {e}")