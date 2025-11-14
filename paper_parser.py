"""
论文列表解析模块
负责解析各种格式的论文列表文件
"""

import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from loguru import logger


@dataclass
class PaperInfo:
    """论文信息数据结构"""
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "abstract": self.abstract,
            "keywords": self.keywords
        }
    
    def get_search_query(self) -> str:
        """生成搜索查询字符串"""
        # 优先使用标题，如果没有则使用作者+年份
        if self.title:
            query = self.title
        else:
            query = " ".join(self.authors)
            if self.year:
                query += f" {self.year}"
        return query
    
    def get_formatted_authors(self) -> str:
        """格式化作者列表"""
        if not self.authors:
            return "Unknown"
        
        if len(self.authors) == 1:
            return self.authors[0]
        elif len(self.authors) == 2:
            return " & ".join(self.authors)
        else:
            return f"{self.authors[0]} et al."


class PaperListParser:
    """论文列表解析器"""
    
    def __init__(self):
        # 定义各种格式的正则表达式
        self.patterns = {
            # 标准格式: Author1, Author2. (Year). Title. Journal.
            'standard': re.compile(r'^(?P<authors>[^.]+)\.?\s*\((?P<year>\d{4})\)\.?\s*(?P<title>[^.]+)\.?\s*(?P<journal>[^.]*?)\.?$'),
            
            # APA格式: Author1, & Author2. (Year). Title. Journal.
            'apa': re.compile(r'^(?P<authors>[^.]+)\.?\s*\((?P<year>\d{4})\)\.?\s*(?P<title>[^.]+)\.?\s*(?P<journal>[^.]*?)\.?$'),
            
            # 简化格式: Author et al. (Year). Title.
            'simple': re.compile(r'^(?P<authors>[^.]+)\.?\s*\((?P<year>\d{4})\)\.?\s*(?P<title>[^.]+)\.?$'),
            
            # 只有标题的格式
            'title_only': re.compile(r'^(?P<title>[^.]+)\.?$'),
            
            # DOI格式
            'doi': re.compile(r'doi:\s*(?P<doi>10\.\d{4,}/[^\s]+)'),
            
            # 作者提取模式
            'authors': re.compile(r'(?P<author>[A-Za-z\s\.]+?)(?:,|\s*&|\s+et\s+al)'),
        }
    
    def parse_line(self, line: str) -> Optional[PaperInfo]:
        """解析单行论文信息"""
        line = line.strip()
        if not line:
            return None
        
        # 尝试不同的解析模式
        for pattern_name, pattern in self.patterns.items():
            if pattern_name == 'title_only':
                match = pattern.match(line)
                if match:
                    title = match.group('title').strip()
                    return PaperInfo(title=title, authors=[])
            
            elif pattern_name in ['standard', 'apa', 'simple']:
                match = pattern.match(line)
                if match:
                    authors_str = match.group('authors').strip()
                    year = int(match.group('year')) if match.group('year') else None
                    title = match.group('title').strip()
                    journal = match.group('journal').strip() if match.group('journal') else None
                    
                    authors = self._parse_authors(authors_str)
                    
                    return PaperInfo(
                        title=title,
                        authors=authors,
                        year=year,
                        journal=journal
                    )
        
        # 如果所有模式都失败，尝试提取标题
        # 移除可能的年份信息
        clean_line = re.sub(r'\(\d{4}\)', '', line).strip()
        if clean_line and len(clean_line) > 10:  # 假设标题至少10个字符
            return PaperInfo(title=clean_line, authors=[])
        
        logger.warning(f"无法解析行: {line}")
        return None
    
    def _parse_authors(self, authors_str: str) -> List[str]:
        """解析作者字符串"""
        authors = []
        
        # 分割作者（使用逗号、&、et al.等）
        # 处理 "Author1, Author2, & Author3" 格式
        authors_str = re.sub(r'\s*&\s*', ', ', authors_str)
        
        # 处理 "Author et al." 格式
        if 'et al.' in authors_str.lower():
            # 提取主要作者
            main_author = re.sub(r'\s+et\s+al\.?', '', authors_str, flags=re.IGNORECASE).strip()
            if main_author:
                authors.append(main_author)
                authors.append("et al.")
        else:
            # 按逗号分割
            author_parts = [part.strip() for part in authors_str.split(',')]
            for part in author_parts:
                if part and len(part) > 1:  # 避免空字符串和单字符
                    authors.append(part)
        
        return authors
    
    def parse_file(self, file_path: str) -> List[PaperInfo]:
        """解析论文列表文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return []
        
        papers = []
        
        try:
            # 根据文件扩展名选择解析方法
            if file_path.suffix.lower() == '.csv':
                papers = self._parse_csv(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                papers = self._parse_excel(file_path)
            elif file_path.suffix.lower() == '.json':
                papers = self._parse_json(file_path)
            else:
                # 默认按行解析文本文件
                papers = self._parse_text(file_path)
            
            logger.info(f"成功解析 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            logger.error(f"解析文件失败 {file_path}: {e}")
            return []
    
    def _parse_text(self, file_path: Path) -> List[PaperInfo]:
        """解析文本文件"""
        papers = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue  # 跳过空行和注释
            
            paper = self.parse_line(line)
            if paper:
                papers.append(paper)
            else:
                logger.warning(f"第 {line_num} 行解析失败: {line}")
        
        return papers
    
    def _parse_csv(self, file_path: Path) -> List[PaperInfo]:
        """解析CSV文件"""
        try:
            df = pd.read_csv(file_path)
            papers = []
            
            # 尝试识别列名
            title_col = None
            authors_col = None
            year_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if 'title' in col_lower:
                    title_col = col
                elif 'author' in col_lower:
                    authors_col = col
                elif 'year' in col_lower:
                    year_col = col
            
            # 如果没有找到合适的列名，使用第一列作为标题
            if not title_col and len(df.columns) > 0:
                title_col = df.columns[0]
            
            for _, row in df.iterrows():
                title = str(row[title_col]) if title_col and pd.notna(row[title_col]) else ""
                authors = []
                
                if authors_col and pd.notna(row[authors_col]):
                    authors_str = str(row[authors_col])
                    authors = self._parse_authors(authors_str)
                
                year = None
                if year_col and pd.notna(row[year_col]):
                    try:
                        year = int(row[year_col])
                    except (ValueError, TypeError):
                        pass
                
                if title:
                    papers.append(PaperInfo(title=title, authors=authors, year=year))
            
            return papers
            
        except Exception as e:
            logger.error(f"CSV解析失败: {e}")
            return self._parse_text(file_path)  # 回退到文本解析
    
    def _parse_excel(self, file_path: Path) -> List[PaperInfo]:
        """解析Excel文件"""
        try:
            df = pd.read_excel(file_path)
            return self._parse_csv(file_path)  # 重用CSV解析逻辑
        except Exception as e:
            logger.error(f"Excel解析失败: {e}")
            return self._parse_text(file_path)  # 回退到文本解析
    
    def _parse_json(self, file_path: Path) -> List[PaperInfo]:
        """解析JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            papers = []
            
            # 支持多种JSON格式
            if isinstance(data, list):
                for item in data:
                    paper = self._parse_json_item(item)
                    if paper:
                        papers.append(paper)
            elif isinstance(data, dict):
                # 可能是单个论文或包含papers键的字典
                if 'papers' in data:
                    for item in data['papers']:
                        paper = self._parse_json_item(item)
                        if paper:
                            papers.append(paper)
                else:
                    paper = self._parse_json_item(data)
                    if paper:
                        papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
            return self._parse_text(file_path)  # 回退到文本解析
    
    def _parse_json_item(self, item: dict) -> Optional[PaperInfo]:
        """解析JSON中的单个论文项"""
        try:
            title = item.get('title', '')
            authors = item.get('authors', [])
            year = item.get('year')
            journal = item.get('journal')
            doi = item.get('doi')
            abstract = item.get('abstract')
            keywords = item.get('keywords', [])
            
            if not title:
                return None
            
            # 处理作者字段可能是字符串的情况
            if isinstance(authors, str):
                authors = self._parse_authors(authors)
            
            return PaperInfo(
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                doi=doi,
                abstract=abstract,
                keywords=keywords
            )
            
        except Exception as e:
            logger.error(f"JSON项解析失败: {e}")
            return None
    
    def save_papers_list(self, papers: List[PaperInfo], output_path: str, format: str = 'txt'):
        """保存论文列表到文件"""
        output_path = Path(output_path)
        
        try:
            if format.lower() == 'txt':
                with open(output_path, 'w', encoding='utf-8') as f:
                    for paper in papers:
                        authors_str = paper.get_formatted_authors()
                        year_str = f"({paper.year})" if paper.year else ""
                        journal_str = f". {paper.journal}" if paper.journal else ""
                        f.write(f"{authors_str} {year_str}. {paper.title}{journal_str}.\n")
            
            elif format.lower() == 'json':
                papers_data = [paper.to_dict() for paper in papers]
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(papers_data, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == 'csv':
                import pandas as pd
                papers_data = [paper.to_dict() for paper in papers]
                df = pd.DataFrame(papers_data)
                df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"论文列表已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存论文列表失败: {e}")