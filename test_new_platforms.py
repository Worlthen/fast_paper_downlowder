#!/usr/bin/env python3
"""
测试新的学术平台模块
验证所有新添加的平台是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from coordinator import PaperDownloaderCoordinator, SearchConfig, DownloadConfig
from paper_parser import PaperInfo


async def test_all_platforms():
    """测试所有新平台"""
    
    # 创建测试论文
    test_papers = [
        PaperInfo(
            title="Machine learning applications in medical imaging",
            authors=["Smith J.", "Johnson A."],
            year=2023
        ),
        PaperInfo(
            title="Deep learning for computer vision",
            authors=["Chen L.", "Wang M."],
            year=2024
        ),
        PaperInfo(
            title="Natural language processing techniques",
            authors=["Brown K.", "Davis R."],
            year=2023
        )
    ]
    
    # 保存测试文件
    from paper_parser import PaperListParser
    parser = PaperListParser()
    test_file = "test_platforms.txt"
    parser.save_papers_list(test_papers, test_file)
    
    # 测试配置 - 包含所有新平台
    search_config = SearchConfig(
        platforms=[
            'arxiv',           # arXiv预印本
            'pubmed',          # PubMed Central生物医学
            'doaj',            # DOAJ开放获取期刊
            'core',            # CORE全球开放获取
            'semantic_scholar', # Semantic Scholar AI搜索
            'zenodo',          # Zenodo研究数据
            'hal',             # HAL法国开放获取
            'biorxiv'          # bioRxiv/medRxiv预印本
        ],
        max_results_per_platform=2,
        use_async=True
    )
    
    download_config = DownloadConfig(
        output_dir="./test_platforms_downloads",
        max_concurrent_downloads=2,
        overwrite_existing=False
    )
    
    # 创建协调器
    coordinator = PaperDownloaderCoordinator(search_config, download_config)
    
    try:
        print("开始测试新的学术平台...")
        print("=" * 60)
        
        # 运行测试
        result = await coordinator.process_paper_list(test_file)
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print(f"总计论文: {result['summary']['total_papers']}")
        print(f"搜索成功: {result['summary']['successful_searches']}")
        print(f"下载成功: {result['summary']['successful_downloads']}")
        print("\n平台统计:")
        
        for platform, stats in result['platform_stats'].items():
            if stats['searches'] > 0:
                success_rate = (stats['success'] / stats['searches']) * 100
                print(f"  {platform}: {stats['success']}/{stats['searches']} ({success_rate:.1f}%)")
        
        print("\n成功的下载:")
        for download in result['details']['successful_downloads']:
            print(f"  - {download['title']} (来自 {download['platform']})")
        
        if result['details']['failed_searches']:
            print("\n搜索失败的论文:")
            for failed in result['details']['failed_searches']:
                print(f"  - {failed['title']}: {failed['error']}")
        
        return result
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return None
        
    finally:
        coordinator.close()
        # 清理测试文件
        import os
        if os.path.exists(test_file):
            os.remove(test_file)


async def test_individual_platforms():
    """单独测试每个平台"""
    
    test_paper = PaperInfo(
        title="Machine learning in healthcare",
        authors=["Test Author"],
        year=2023
    )
    
    from paper_parser import PaperListParser
    parser = PaperListParser()
    test_file = "test_single.txt"
    parser.save_papers_list([test_paper], test_file)
    
    platforms = [
        ('arxiv', 'arXiv预印本'),
        ('pubmed', 'PubMed Central生物医学'),
        ('doaj', 'DOAJ开放获取期刊'),
        ('core', 'CORE全球开放获取'),
        ('semantic_scholar', 'Semantic Scholar AI搜索'),
        ('zenodo', 'Zenodo研究数据'),
        ('hal', 'HAL法国开放获取'),
        ('biorxiv', 'bioRxiv/medRxiv预印本')
    ]
    
    print("单独测试每个平台...")
    print("=" * 60)
    
    for platform_id, platform_name in platforms:
        print(f"\n测试 {platform_name} ({platform_id})...")
        
        search_config = SearchConfig(
            platforms=[platform_id],
            max_results_per_platform=1,
            use_async=True
        )
        
        download_config = DownloadConfig(
            output_dir=f"./test_{platform_id}",
            max_concurrent_downloads=1
        )
        
        coordinator = PaperDownloaderCoordinator(search_config, download_config)
        
        try:
            result = await coordinator.process_paper_list(test_file)
            
            if result['summary']['successful_searches'] > 0:
                print(f"  ✓ {platform_name} 搜索成功")
                if result['summary']['successful_downloads'] > 0:
                    print(f"  ✓ {platform_name} 下载成功")
                else:
                    print(f"  ⚠ {platform_name} 搜索成功但下载失败")
            else:
                print(f"  ✗ {platform_name} 搜索失败")
                
        except Exception as e:
            print(f"  ✗ {platform_name} 测试出错: {e}")
        
        finally:
            coordinator.close()
    
    # 清理测试文件
    import os
    if os.path.exists(test_file):
        os.remove(test_file)


async def main():
    """主测试函数"""
    
    print("学术论文下载器 - 新平台测试")
    print("=" * 60)
    
    # 测试所有平台
    await test_all_platforms()
    
    print("\n" + "=" * 60)
    print("单独平台测试")
    print("=" * 60)
    
    # 单独测试每个平台
    await test_individual_platforms()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())