"""
学术论文自动下载器 - 简化版本
不依赖外部库的基础实现
"""

import sys
import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse
import time
import random


class PaperInfo:
    """论文信息类"""
    def __init__(self, title: str, authors: List[str] = None, year: int = None):
        self.title = title
        self.authors = authors or []
        self.year = year
    
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
    
    def get_search_query(self) -> str:
        """生成搜索查询字符串"""
        if self.title:
            return self.title
        else:
            query = " ".join(self.authors)
            if self.year:
                query += f" {self.year}"
            return query


class PaperListParser:
    """论文列表解析器"""
    
    def __init__(self):
        # 修复后的正则表达式模式
        self.patterns = {
            'standard': re.compile(r'^(?P<authors>[^.]+?)\s*\((?P<year>\d{4})\)\s*(?P<title>[^.]+?)(?:\.(?P<journal>[^.]*))?\.?$'),
            'simple': re.compile(r'^(?P<authors>[^.]+?)\s*\((?P<year>\d{4})\)\s*(?P<title>[^.]+?)(?:\.(?P<journal>[^.]*))?\.?$'),
            'title_only': re.compile(r'^(?P<title>[^.\n]+?)\.?$'),
        }
    
    def parse_line(self, line: str) -> Optional[PaperInfo]:
        """解析单行论文信息"""
        line = line.strip()
        if not line:
            return None
        
        # 尝试不同的解析模式
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(line)
            if match:
                if pattern_name == 'title_only':
                    title = match.group('title').strip().rstrip('.')
                    return PaperInfo(title=title)
                else:
                    authors_str = match.group('authors').strip().rstrip('.')
                    year = int(match.group('year')) if match.group('year') else None
                    title = match.group('title').strip().rstrip('.')
                    
                    authors = self._parse_authors(authors_str)
                    return PaperInfo(title=title, authors=authors, year=year)
        
        # 如果所有模式都失败，尝试提取标题
        clean_line = re.sub(r'\(\d{4}\)', '', line).strip()
        if clean_line and len(clean_line) > 10:
            return PaperInfo(title=clean_line)
        
        return None
    
    def _parse_authors(self, authors_str: str) -> List[str]:
        """解析作者字符串"""
        authors = []
        authors_str = authors_str.strip().rstrip('.')
        
        # 处理 "Author et al." 格式
        if 'et al.' in authors_str.lower():
            main_author = re.sub(r'\s+et\s+al\.?', '', authors_str, flags=re.IGNORECASE).strip()
            if main_author:
                authors.append(main_author)
                authors.append("et al.")
        else:
            # 按逗号分割
            author_parts = [part.strip() for part in authors_str.split(',')]
            for part in author_parts:
                if part and len(part) > 1:
                    authors.append(part)
        
        return authors
    
    def parse_file(self, file_path: str) -> List[PaperInfo]:
        """解析论文列表文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"错误: 文件不存在: {file_path}")
            return []
        
        papers = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                
                paper = self.parse_line(line)
                if paper:
                    papers.append(paper)
                else:
                    print(f"警告: 第 {line_num} 行解析失败: {line}")
            
            print(f"成功解析 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            print(f"解析文件失败 {file_path}: {e}")
            return []


class SimplePDFDownloader:
    """简化版PDF下载器"""
    
    def __init__(self, output_dir: str = "./downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / 'pdfs').mkdir(exist_ok=True)
        (self.output_dir / 'metadata').mkdir(exist_ok=True)
    
    def generate_filename(self, paper: PaperInfo, platform: str = 'unknown') -> str:
        """生成文件名"""
        authors = paper.get_formatted_authors().replace(' ', '_').replace(',', '')
        year = str(paper.year) if paper.year else 'unknown'
        
        # 清理标题
        title = paper.title[:80]  # 限制长度
        title = re.sub(r'[^\w\s-]', '', title)  # 移除特殊字符
        title = title.replace(' ', '_')
        
        filename = f"{authors}_{year}_{title}_{platform}.pdf"
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # 确保文件名安全
        
        return filename
    
    def download_pdf(self, paper: PaperInfo, pdf_url: str, platform: str = 'unknown') -> bool:
        """下载PDF文件"""
        try:
            print(f"下载PDF: {paper.title}")
            
            # 生成文件名和路径
            filename = self.generate_filename(paper, platform)
            output_path = self.output_dir / 'pdfs' / filename
            
            # 检查文件是否已存在
            if output_path.exists():
                print(f"文件已存在，跳过: {filename}")
                return True
            
            # 下载文件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            request = urllib.request.Request(pdf_url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    print(f"下载失败，HTTP状态码: {response.status}")
                    return False
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                
                # 保存文件
                with open(output_path, 'wb') as f:
                    f.write(response.read())
            
            # 验证文件
            if output_path.stat().st_size < 1024:  # 小于1KB可能无效
                print(f"下载的文件太小，可能无效")
                output_path.unlink()  # 删除无效文件
                return False
            
            print(f"下载成功: {filename}")
            
            # 保存元数据
            self._save_metadata(paper, platform, str(output_path))
            
            return True
            
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def _save_metadata(self, paper: PaperInfo, platform: str, file_path: str):
        """保存元数据"""
        try:
            metadata = {
                'title': paper.title,
                'authors': paper.authors,
                'year': paper.year,
                'platform': platform,
                'download_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'file_path': file_path
            }
            
            # 生成元数据文件名
            base_name = Path(file_path).stem
            metadata_file = self.output_dir / 'metadata' / f"{base_name}.json"
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存元数据失败: {e}")


class SimpleGoogleScholarSearcher:
    """简化版Google Scholar搜索器"""
    
    def __init__(self):
        self.base_url = "https://scholar.google.com"
        self.search_path = "/scholar"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """搜索学术论文"""
        try:
            print(f"Google Scholar搜索: '{query}'")
            
            # 构建搜索URL
            params = {
                'q': query,
                'num': max_results,
                'hl': 'en'
            }
            
            query_string = urllib.parse.urlencode(params)
            url = f"{self.base_url}{self.search_path}?{query_string}"
            
            print(f"请求URL: {url}")
            
            # 发送请求
            request = urllib.request.Request(url, headers=self.headers)
            
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    print(f"搜索失败，HTTP状态码: {response.status}")
                    return []
                
                html = response.read().decode('utf-8')
            
            # 简单的HTML解析
            results = self._parse_results(html)
            
            print(f"找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def _parse_results(self, html: str) -> List[Dict]:
        """解析搜索结果"""
        results = []
        
        try:
            # 简单的正则表达式解析
            # 查找标题
            title_pattern = r'<h3[^>]*class="gs_rt"[^>]*>(.*?)<\/h3>'
            titles = re.findall(title_pattern, html, re.DOTALL)
            
            # 查找PDF链接
            pdf_pattern = r'<div[^>]*class="gs_ggs"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>'
            pdf_links = re.findall(pdf_pattern, html, re.DOTALL)
            
            # 查找作者信息
            author_pattern = r'<div[^>]*class="gs_a"[^>]*>(.*?)<\/div>'
            authors = re.findall(author_pattern, html, re.DOTALL)
            
            # 组合结果
            for i, title in enumerate(titles[:5]):  # 限制结果数量
                # 清理HTML标签
                title_clean = re.sub(r'<[^>]*>', '', title).strip()
                
                pdf_url = pdf_links[i] if i < len(pdf_links) else None
                author_info = authors[i] if i < len(authors) else ""
                
                # 提取年份
                year_match = re.search(r'\b(19|20)\d{2}\b', author_info)
                year = int(year_match.group()) if year_match else None
                
                # 提取作者
                author_clean = re.sub(r'<[^>]*>', '', author_info).strip()
                
                result = {
                    'title': title_clean,
                    'authors': author_clean,
                    'year': year,
                    'pdf_url': pdf_url
                }
                
                results.append(result)
            
        except Exception as e:
            print(f"解析结果失败: {e}")
        
        return results


class PaperDownloaderSimple:
    """简化版论文下载器主类"""
    
    def __init__(self, output_dir: str = "./downloads"):
        self.parser = PaperListParser()
        self.downloader = SimplePDFDownloader(output_dir)
        self.searcher = SimpleGoogleScholarSearcher()
        self.stats = {
            'total_papers': 0,
            'successful_searches': 0,
            'successful_downloads': 0,
            'failed_searches': 0,
            'failed_downloads': 0
        }
    
    def process_paper_list(self, input_file: str, max_results: int = 3) -> Dict:
        """处理论文列表"""
        print(f"\n开始处理论文列表: {input_file}")
        
        # 解析论文列表
        papers = self.parser.parse_file(input_file)
        if not papers:
            return {'success': False, 'error': 'No papers found'}
        
        self.stats['total_papers'] = len(papers)
        print(f"解析到 {len(papers)} 篇论文")
        
        # 处理每篇论文
        for i, paper in enumerate(papers, 1):
            print(f"\n[{i}/{len(papers)}] 处理论文: {paper.title}")
            
            # 搜索论文
            search_results = self.searcher.search(paper.get_search_query(), max_results)
            
            if search_results:
                self.stats['successful_searches'] += 1
                
                # 尝试下载第一个有PDF链接的结果
                for result in search_results:
                    if result.get('pdf_url'):
                        success = self.downloader.download_pdf(paper, result['pdf_url'], 'google_scholar')
                        if success:
                            self.stats['successful_downloads'] += 1
                            break
                        else:
                            self.stats['failed_downloads'] += 1
                
                if not any(result.get('pdf_url') for result in search_results):
                    print("未找到PDF链接")
                    self.stats['failed_downloads'] += 1
            else:
                print("搜索失败")
                self.stats['failed_searches'] += 1
            
            # 添加延迟避免被检测
            time.sleep(random.uniform(1, 3))
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict:
        """生成报告"""
        report = {
            'total_papers': self.stats['total_papers'],
            'successful_searches': self.stats['successful_searches'],
            'failed_searches': self.stats['failed_searches'],
            'successful_downloads': self.stats['successful_downloads'],
            'failed_downloads': self.stats['failed_downloads'],
            'search_success_rate': self.stats['successful_searches'] / max(self.stats['total_papers'], 1),
            'download_success_rate': self.stats['successful_downloads'] / max(self.stats['successful_searches'], 1)
        }
        
        print("\n" + "=" * 50)
        print("📊 下载任务完成")
        print(f"总计论文: {report['total_papers']}")
        print(f"搜索成功: {report['successful_searches']} ({report['search_success_rate']:.1%})")
        print(f"下载成功: {report['successful_downloads']} ({report['download_success_rate']:.1%})")
        print("=" * 50)
        
        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='学术论文自动下载器 - 简化版本')
    parser.add_argument('-i', '--input', required=True, help='输入文件路径')
    parser.add_argument('-o', '--output', default='./downloads', help='输出目录')
    parser.add_argument('-n', '--max-results', type=int, default=3, help='最大搜索结果数')
    parser.add_argument('--test', action='store_true', help='测试模式（只处理前3篇）')
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    print("\n" + "=" * 60)
    print("📚 学术论文自动下载器 - 简化版本")
    print("=" * 60)
    
    # 验证输入文件
    if not Path(args.input).exists():
        print(f"❌ 错误: 输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 创建下载器
    downloader = PaperDownloaderSimple(args.output)
    
    try:
        if args.test:
            print("🔧 测试模式：只处理前3篇论文")
            # 创建临时测试文件
            import tempfile
            with open(args.input, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.writelines(lines[:3])
                test_file = f.name
            
            try:
                report = downloader.process_paper_list(test_file, args.max_results)
            finally:
                Path(test_file).unlink()
        else:
            report = downloader.process_paper_list(args.input, args.max_results)
        
        print(f"\n✅ 任务完成！详细报告已保存到: {args.output}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()