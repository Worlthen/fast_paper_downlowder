"""
测试模块
用于测试各个组件的功能
"""

import asyncio
import pytest
from pathlib import Path
import tempfile
import shutil

from paper_parser import PaperListParser, PaperInfo
from google_scholar import GoogleScholarSearcher
from scihub import SciHubSearcher
from pdf_downloader import PDFDownloader, DownloadTask
from coordinator import PaperDownloaderCoordinator, SearchConfig, DownloadConfig


class TestPaperParser:
    """测试论文解析器"""
    
    def test_parse_line_standard_format(self):
        """测试标准格式解析"""
        parser = PaperListParser()
        
        line = "Aizawa T., & Inohara T. (2019). Pico- and femtosecond laser micromachining for surface texturing. Micromachining."
        result = parser.parse_line(line)
        
        assert result is not None
        assert "Pico- and femtosecond laser micromachining" in result.title
        assert result.year == 2019
        assert len(result.authors) >= 2
    
    def test_parse_line_simple_format(self):
        """测试简化格式解析"""
        parser = PaperListParser()
        
        line = "Franz D. et al. (2022). Ultrashort pulsed laser drilling of printed circuit board materials. Materials."
        result = parser.parse_line(line)
        
        assert result is not None
        assert "Ultrashort pulsed laser drilling" in result.title
        assert result.year == 2022
    
    def test_parse_line_title_only(self):
        """测试只有标题的格式"""
        parser = PaperListParser()
        
        line = "Laser-induced plasma and its applications"
        result = parser.parse_line(line)
        
        assert result is not None
        assert "Laser-induced plasma" in result.title
        assert result.year is None
    
    def test_parse_authors(self):
        """测试作者解析"""
        parser = PaperListParser()
        
        authors_str = "Aizawa T., & Inohara T."
        authors = parser._parse_authors(authors_str)
        
        assert len(authors) >= 1
        assert "Aizawa T." in authors
    
    def test_save_and_load_papers(self):
        """测试保存和加载论文列表"""
        parser = PaperListParser()
        
        # 创建测试论文
        papers = [
            PaperInfo(
                title="Test Paper 1",
                authors=["Author A", "Author B"],
                year=2023
            ),
            PaperInfo(
                title="Test Paper 2",
                authors=["Author C"],
                year=2024
            )
        ]
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name
        
        try:
            parser.save_papers_list(papers, temp_file)
            
            # 重新加载
            loaded_papers = parser.parse_file(temp_file)
            
            assert len(loaded_papers) == 2
            assert loaded_papers[0].title == "Test Paper 1"
            assert loaded_papers[1].year == 2024
            
        finally:
            Path(temp_file).unlink(missing_ok=True)


class TestGoogleScholarSearcher:
    """测试Google Scholar搜索器"""
    
    def test_initialization(self):
        """测试初始化"""
        config = {
            'max_results': 5,
            'delay': 1.0,
            'use_selenium': False  # 禁用Selenium进行测试
        }
        
        searcher = GoogleScholarSearcher(config)
        assert searcher.max_results == 5
        assert searcher.delay == 1.0
        assert searcher.use_selenium == False
    
    @pytest.mark.asyncio
    async def test_search_basic(self):
        """测试基本搜索功能"""
        config = {
            'max_results': 3,
            'delay': 1.0,
            'use_selenium': False,
            'timeout': 10
        }
        
        searcher = GoogleScholarSearcher(config)
        
        # 使用简单的搜索词
        results = searcher.search("laser micromachining", max_results=2)
        
        # 注意：由于网络环境，这个结果可能为空
        # 我们主要测试函数是否能正常执行
        assert isinstance(results, list)
        
        searcher.close()


class TestSciHubSearcher:
    """测试Sci-Hub搜索器"""
    
    def test_initialization(self):
        """测试初始化"""
        config = {
            'timeout': 30,
            'max_retries': 2
        }
        
        searcher = SciHubSearcher(config)
        assert searcher.timeout == 30
        assert searcher.max_retries == 2
    
    def test_clean_doi(self):
        """测试DOI清理"""
        searcher = SciHubSearcher()
        
        doi = "doi: 10.1016/j.matpr.2019.05.373"
        cleaned = searcher._clean_doi(doi)
        assert cleaned == "10.1016/j.matpr.2019.05.373"
        
        doi = "https://doi.org/10.1016/j.matpr.2019.05.373"
        cleaned = searcher._clean_doi(doi)
        assert cleaned == "10.1016/j.matpr.2019.05.373"


class TestPDFDownloader:
    """测试PDF下载器"""
    
    def test_initialization(self):
        """测试初始化"""
        config = {
            'max_concurrent': 2,
            'timeout': 30,
            'output_dir': './test_downloads'
        }
        
        downloader = PDFDownloader(config)
        assert downloader.max_concurrent == 2
        assert downloader.timeout == 30
    
    def test_filename_generation(self):
        """测试文件名生成"""
        downloader = PDFDownloader()
        
        paper = PaperInfo(
            title="Test Paper: A Study on Laser Technology",
            authors=["John Doe", "Jane Smith"],
            year=2023
        )
        
        filename = downloader.generate_filename(paper, "google_scholar")
        
        assert "John_Doe" in filename
        assert "2023" in filename
        assert "Test_Paper" in filename
        assert filename.endswith("google_scholar.pdf")
    
    def test_format_size(self):
        """测试文件大小格式化"""
        downloader = PDFDownloader()
        
        assert downloader._format_size(0) == "0 B"
        assert downloader._format_size(1024) == "1.0 KB"
        assert downloader._format_size(1048576) == "1.0 MB"
        assert downloader._format_size(1073741824) == "1.0 GB"


class TestCoordinator:
    """测试协调器"""
    
    def test_initialization(self):
        """测试初始化"""
        search_config = SearchConfig(
            platforms=['google_scholar'],
            max_results_per_platform=3
        )
        
        download_config = DownloadConfig(
            output_dir="./test_output",
            max_concurrent_downloads=2
        )
        
        coordinator = PaperDownloaderCoordinator(search_config, download_config)
        
        assert coordinator.search_config.platforms == ['google_scholar']
        assert coordinator.download_config.max_concurrent_downloads == 2
    
    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        """测试处理空列表"""
        coordinator = PaperDownloaderCoordinator()
        
        # 创建空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_file = f.name
        
        try:
            result = await coordinator.process_paper_list(temp_file)
            
            assert result['success'] == False
            assert 'No papers found' in result['error']
            
        finally:
            Path(temp_file).unlink(missing_ok=True)


# 集成测试
@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整工作流程"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建测试论文列表
        parser = PaperListParser()
        test_papers = [
            PaperInfo(
                title="Test Paper for Integration",
                authors=["Integration Test Author"],
                year=2023
            )
        ]
        
        papers_file = Path(temp_dir) / "test_papers.txt"
        parser.save_papers_list(test_papers, str(papers_file))
        
        # 配置搜索和下载
        search_config = SearchConfig(
            platforms=['google_scholar'],  # 只测试Google Scholar
            max_results_per_platform=2,
            use_async=True
        )
        
        download_config = DownloadConfig(
            output_dir=str(Path(temp_dir) / "downloads"),
            max_concurrent_downloads=1,
            overwrite_existing=False
        )
        
        # 创建协调器
        coordinator = PaperDownloaderCoordinator(search_config, download_config)
        
        # 处理论文列表
        result = await coordinator.process_paper_list(str(papers_file))
        
        # 验证结果结构
        assert 'timestamp' in result
        assert 'summary' in result
        assert 'details' in result
        
        coordinator.close()
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])