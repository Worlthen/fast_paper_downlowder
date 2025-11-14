#!/usr/bin/env python3
"""
学术论文下载器 - 新平台测试脚本
测试所有新添加的学术平台模块
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from paper_parser import PaperInfo
from platforms.arxiv import ArxivPlatform
from platforms.pubmed import PubMedPlatform
from platforms.doaj import DOAJPlatform
from platforms.core import COREPlatform
from platforms.semantic_scholar import SemanticScholarPlatform
from platforms.zenodo import ZenodoPlatform
from platforms.hal import HALPlatform
from platforms.biorxiv import BioRxivPlatform


async def test_platform_search(platform, test_papers):
    """测试单个平台的搜索功能"""
    print(f"\n--- 测试 {platform.__class__.__name__} ---")
    
    try:
        all_results = []
        
        for paper in test_papers:
            print(f"搜索: {paper.title[:50]}...")
            
            # 搜索论文
            results = await platform.search_paper(paper)
            
            if results:
                print(f"  找到 {len(results)} 个结果")
                for i, result in enumerate(results[:2]):  # 只显示前2个结果
                    print(f"    {i+1}. {result.title[:60]}...")
                    print(f"       作者: {', '.join(result.authors[:3])}")
                    print(f"       年份: {result.year}")
                    if result.doi:
                        print(f"       DOI: {result.doi}")
                    if result.pdf_url:
                        print(f"       PDF: {result.pdf_url[:60]}...")
                    print(f"       开放获取: {'是' if result.is_open_access else '否'}")
                    print()
                
                all_results.extend(results)
            else:
                print("  未找到结果")
        
        print(f"总计找到 {len(all_results)} 个结果")
        return all_results
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_platform_download(platform, search_results):
    """测试平台的下载功能"""
    print(f"\n--- 测试 {platform.__class__.__name__} 下载 ---")
    
    if not search_results:
        print("没有搜索结果可供下载")
        return
    
    # 选择前3个有PDF链接的结果进行下载测试
    test_results = [r for r in search_results if r.pdf_url][:3]
    
    if not test_results:
        print("没有找到可下载的PDF文件")
        return
    
    print(f"测试下载 {len(test_results)} 个文件...")
    
    for i, result in enumerate(test_results):
        try:
            print(f"\n下载 {i+1}: {result.title[:50]}...")
            
            # 下载PDF
            pdf_content = await platform.download_pdf(result)
            
            if pdf_content and len(pdf_content) > 0:
                print(f"  成功下载！文件大小: {len(pdf_content)} 字节")
                
                # 验证PDF内容
                if pdf_content.startswith(b'%PDF'):
                    print("  验证: 有效的PDF文件")
                else:
                    print("  警告: 可能不是有效的PDF文件")
                    
            else:
                print("  下载失败")
                
        except Exception as e:
            print(f"  下载错误: {e}")


async def test_platform_availability(platform):
    """测试平台可用性"""
    print(f"\n--- 测试 {platform.__class__.__name__} 可用性 ---")
    
    try:
        is_available = await platform.check_availability()
        print(f"平台可用性: {'可用' if is_available else '不可用'}")
        return is_available
        
    except Exception as e:
        print(f"可用性测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("学术论文下载器 - 新平台测试")
    print("=" * 60)
    
    # 测试论文
    test_papers = [
        PaperInfo(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            year=2017
        ),
        PaperInfo(
            title="Deep Residual Learning for Image Recognition",
            authors=["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            year=2016
        ),
        PaperInfo(
            title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
            year=2019
        ),
        PaperInfo(
            title="Machine learning applications in medical imaging",
            authors=["Topol EJ"],
            year=2019
        ),
        PaperInfo(
            title="COVID-19 and artificial intelligence: protecting health-care workers and curbing the spread",
            authors=["Wynants L", "Van Calster B"],
            year=2020
        )
    ]
    
    # 生物医学测试论文
    medical_test_papers = [
        PaperInfo(
            title="Deep learning for medical image analysis",
            authors=["Litjens G", "Kooi T", "Bejnordi BE"],
            year=2017
        ),
        PaperInfo(
            title="Artificial intelligence in healthcare: past, present and future",
            authors=["Jiang F", "Jiang Y", "Zhi H"],
            year=2017
        ),
        PaperInfo(
            title="Machine learning in medicine: a practical introduction",
            authors=["Obermeyer Z", "Emanuel EJ"],
            year=2016
        )
    ]
    
    # 所有平台列表
    platforms = [
        ArxivPlatform(),
        PubMedPlatform(),
        DOAJPlatform(),
        COREPlatform(),
        SemanticScholarPlatform(),
        ZenodoPlatform(),
        HALPlatform(),
        BioRxivPlatform()
    ]
    
    # 测试结果统计
    test_results = {}
    
    try:
        # 测试每个平台
        for platform in platforms:
            platform_name = platform.__class__.__name__
            test_results[platform_name] = {
                'available': False,
                'search_results': [],
                'search_success': False,
                'download_success': False
            }
            
            try:
                # 1. 测试平台可用性
                available = await test_platform_availability(platform)
                test_results[platform_name]['available'] = available
                
                if not available:
                    print(f"{platform_name} 不可用，跳过后续测试")
                    continue
                
                # 2. 测试搜索功能
                # 根据平台类型选择测试论文
                if platform_name in ['PubMedPlatform', 'BioRxivPlatform']:
                    current_test_papers = medical_test_papers
                else:
                    current_test_papers = test_papers
                
                search_results = await test_platform_search(platform, current_test_papers)
                test_results[platform_name]['search_results'] = search_results
                test_results[platform_name]['search_success'] = len(search_results) > 0
                
                # 3. 测试下载功能（可选，避免过多下载）
                if search_results and len(search_results) > 0:
                    await test_platform_download(platform, search_results)
                    test_results[platform_name]['download_success'] = True
                
            except Exception as e:
                print(f"测试 {platform_name} 时发生错误: {e}")
                import traceback
                traceback.print_exc()
        
        # 显示测试总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        print("\n平台可用性:")
        for platform_name, results in test_results.items():
            status = "✓ 可用" if results['available'] else "✗ 不可用"
            print(f"  {platform_name}: {status}")
        
        print("\n搜索功能:")
        for platform_name, results in test_results.items():
            if results['available']:
                search_count = len(results['search_results'])
                status = f"✓ 成功 ({search_count} 结果)" if results['search_success'] else "✗ 失败"
                print(f"  {platform_name}: {status}")
        
        print("\n下载功能:")
        for platform_name, results in test_results.items():
            if results['available'] and results['search_success']:
                status = "✓ 已测试" if results['download_success'] else "✗ 未测试"
                print(f"  {platform_name}: {status}")
        
        # 统计信息
        total_platforms = len(platforms)
        available_platforms = sum(1 for r in test_results.values() if r['available'])
        search_successful = sum(1 for r in test_results.values() if r['search_success'])
        
        print(f"\n统计信息:")
        print(f"  总平台数: {total_platforms}")
        print(f"  可用平台: {available_platforms} ({available_platforms/total_platforms*100:.1f}%)")
        print(f"  搜索成功: {search_successful} ({search_successful/total_platforms*100:.1f}%)")
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(main())