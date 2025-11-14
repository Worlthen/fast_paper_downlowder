#!/usr/bin/env python3
"""
学术论文下载器 - 使用示例
展示如何使用新的学术平台功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from coordinator import PaperDownloaderCoordinator, SearchConfig, DownloadConfig
from paper_parser import PaperInfo, PaperListParser


def create_sample_papers():
    """创建示例论文列表"""
    return [
        PaperInfo(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            year=2017,
            journal="Advances in Neural Information Processing Systems"
        ),
        PaperInfo(
            title="Deep Residual Learning for Image Recognition",
            authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            year=2016,
            journal="IEEE Conference on Computer Vision and Pattern Recognition"
        ),
        PaperInfo(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            year=2019,
            journal="NAACL-HLT"
        ),
        PaperInfo(
            title="Machine learning applications in medical imaging",
            authors=["Topol EJ"],
            year=2019,
            journal="Nature Medicine"
        ),
        PaperInfo(
            title="COVID-19 and artificial intelligence: protecting health-care workers and curbing the spread",
            authors=["Wynants L", "Van Calster B"],
            year=2020,
            journal="The Lancet Digital Health"
        )
    ]


async def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建示例论文列表
    papers = create_sample_papers()
    
    # 保存论文列表到文件
    parser = PaperListParser()
    input_file = "example_papers.txt"
    parser.save_papers_list(papers, input_file)
    
    # 配置搜索（使用所有新平台）
    search_config = SearchConfig(
        platforms=[
            'arxiv',              # arXiv预印本
            'pubmed',             # PubMed Central生物医学
            'doaj',               # DOAJ开放获取期刊
            'core',               # CORE全球开放获取
            'semantic_scholar',   # Semantic Scholar AI搜索
            'zenodo',             # Zenodo研究数据
            'hal',                # HAL法国开放获取
            'biorxiv'             # bioRxiv/medRxiv预印本
        ],
        max_results_per_platform=3,
        use_async=True
    )
    
    # 配置下载
    download_config = DownloadConfig(
        output_dir="./example_downloads",
        max_concurrent_downloads=3,
        overwrite_existing=False,
        save_metadata=True
    )
    
    # 创建协调器
    coordinator = PaperDownloaderCoordinator(search_config, download_config)
    
    try:
        print(f"开始处理 {len(papers)} 篇论文...")
        
        # 执行下载任务
        result = await coordinator.process_paper_list(input_file)
        
        # 显示结果
        print(f"\n处理完成！")
        print(f"总计论文: {result['summary']['total_papers']}")
        print(f"搜索成功: {result['summary']['successful_searches']} "
              f"({result['summary']['search_success_rate']:.1%})")
        print(f"下载成功: {result['summary']['successful_downloads']} "
              f"({result['summary']['download_success_rate']:.1%})")
        
        # 显示平台统计
        print(f"\n各平台搜索统计:")
        for platform, stats in result['platform_stats'].items():
            if stats['searches'] > 0:
                success_rate = (stats['success'] / stats['searches']) * 100
                print(f"  {platform}: {stats['success']}/{stats['searches']} ({success_rate:.1f}%)")
        
        # 显示成功下载的论文
        if result['details']['successful_downloads']:
            print(f"\n成功下载的论文:")
            for paper in result['details']['successful_downloads']:
                print(f"  - {paper['title']} (来自 {paper['platform']})")
        
        return result
        
    finally:
        coordinator.close()
        # 清理输入文件
        import os
        if os.path.exists(input_file):
            os.remove(input_file)


async def example_specific_platforms():
    """特定平台使用示例"""
    print("\n=== 特定平台使用示例 ===")
    
    # 创建生物医学相关论文
    medical_papers = [
        PaperInfo(
            title="Deep learning for medical image analysis",
            authors=["Litjens G", "Kooi T", "Bejnordi BE"],
            year=2017,
            journal="Medical Image Analysis"
        ),
        PaperInfo(
            title="Artificial intelligence in healthcare: past, present and future",
            authors=["Jiang F", "Jiang Y", "Zhi H"],
            year=2017,
            journal="Stroke and Vascular Neurology"
        )
    ]
    
    # 保存论文列表
    parser = PaperListParser()
    input_file = "medical_papers.txt"
    parser.save_papers_list(medical_papers, input_file)
    
    # 配置搜索（重点使用生物医学平台）
    search_config = SearchConfig(
        platforms=[
            'pubmed',             # PubMed Central生物医学文献
            'biorxiv',            # bioRxiv/medRxiv生命科学预印本
            'doaj',               # DOAJ开放获取期刊
            'semantic_scholar'    # Semantic Scholar AI搜索
        ],
        max_results_per_platform=5,
        use_async=True
    )
    
    # 配置下载
    download_config = DownloadConfig(
        output_dir="./medical_downloads",
        max_concurrent_downloads=2,
        overwrite_existing=False
    )
    
    # 创建协调器
    coordinator = PaperDownloaderCoordinator(search_config, download_config)
    
    try:
        print(f"开始搜索生物医学论文...")
        result = await coordinator.process_paper_list(input_file)
        
        print(f"\n生物医学论文搜索完成！")
        print(f"搜索成功: {result['summary']['successful_searches']}/{result['summary']['total_papers']}")
        
        return result
        
    finally:
        coordinator.close()
        # 清理输入文件
        import os
        if os.path.exists(input_file):
            os.remove(input_file)


async def example_open_access_focus():
    """开放获取资源使用示例"""
    print("\n=== 开放获取资源使用示例 ===")
    
    # 创建计算机科学相关论文
    cs_papers = [
        PaperInfo(
            title="Attention Is All You Need",
            authors=["Vaswani A", "Shazeer N", "Parmar N"],
            year=2017
        ),
        PaperInfo(
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin J", "Chang MW", "Lee K"],
            year=2019
        ),
        PaperInfo(
            title="GPT-3: Language Models are Few-Shot Learners",
            authors=["Brown T", "Mann B", "Ryder N"],
            year=2020
        )
    ]
    
    # 保存论文列表
    parser = PaperListParser()
    input_file = "cs_papers.txt"
    parser.save_papers_list(cs_papers, input_file)
    
    # 配置搜索（重点使用开放获取平台）
    search_config = SearchConfig(
        platforms=[
            'arxiv',              # arXiv预印本（完全开放获取）
            'zenodo',             # Zenodo研究数据（开放获取）
            'hal',                # HAL法国开放获取
            'core',               # CORE全球开放获取
            'doaj'                # DOAJ开放获取期刊
        ],
        max_results_per_platform=5,
        use_async=True
    )
    
    # 配置下载
    download_config = DownloadConfig(
        output_dir="./open_access_downloads",
        max_concurrent_downloads=3,
        overwrite_existing=False
    )
    
    # 创建协调器
    coordinator = PaperDownloaderCoordinator(search_config, download_config)
    
    try:
        print(f"开始搜索开放获取论文...")
        result = await coordinator.process_paper_list(input_file)
        
        print(f"\n开放获取论文搜索完成！")
        print(f"搜索成功: {result['summary']['successful_searches']}/{result['summary']['total_papers']}")
        
        return result
        
    finally:
        coordinator.close()
        # 清理输入文件
        import os
        if os.path.exists(input_file):
            os.remove(input_file)


async def main():
    """主函数"""
    
    print("学术论文下载器 - 新平台使用示例")
    print("=" * 60)
    
    try:
        # 示例1: 基本使用
        await example_basic_usage()
        
        # 示例2: 特定领域（生物医学）
        await example_specific_platforms()
        
        # 示例3: 开放获取资源
        await example_open_access_focus()
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"发生错误: {e}")
    
    print("\n" + "=" * 60)
    print("使用示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())