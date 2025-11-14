#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展论文下载系统测试程序
测试新增的10个学术平台支持
"""

import asyncio
import sys
import os
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from coordinator import SearchCoordinator
from utils.logger import get_logger

logger = get_logger(__name__)

# 测试关键词列表
test_keywords = [
    "machine learning",
    "COVID-19",
    "climate change",
    "artificial intelligence",
    "renewable energy"
]

# 测试平台列表
platforms = [
    'arxiv', 'pubmed', 'doaj', 'core', 'semantic_scholar',
    'researchgate', 'academia', 'zenodo', 'hal', 'biorxiv'
]

async def test_platform_search(platform, keyword):
    """测试单个平台搜索功能"""
    try:
        coordinator = SearchCoordinator()
        
        logger.info(f"测试 {platform} 平台，关键词: {keyword}")
        
        # 执行搜索
        results = await coordinator.search(keyword, platforms=[platform], max_results=5)
        
        if results and len(results) > 0:
            logger.info(f"✓ {platform} 搜索成功，找到 {len(results)} 篇论文")
            
            # 显示前几个结果
            for i, paper in enumerate(results[:3]):
                logger.info(f"  {i+1}. {paper.get('title', 'N/A')[:80]}...")
                logger.info(f"     作者: {paper.get('authors', ['N/A'])[0] if paper.get('authors') else 'N/A'}")
                logger.info(f"     年份: {paper.get('year', 'N/A')}")
                logger.info(f"     DOI: {paper.get('doi', 'N/A')}")
                logger.info(f"     PDF链接: {paper.get('pdf_url', 'N/A')}")
                logger.info("")
            
            return True
        else:
            logger.warning(f"⚠ {platform} 未找到相关论文")
            return False
            
    except Exception as e:
        logger.error(f"✗ {platform} 搜索失败: {str(e)}")
        return False

async def test_platform_availability():
    """测试平台可用性检查"""
    try:
        coordinator = SearchCoordinator()
        
        logger.info("测试平台可用性检查...")
        
        # 检查几个平台的可用性
        test_platforms = ['arxiv', 'pubmed', 'doaj']
        
        for platform in test_platforms:
            try:
                available = await coordinator.check_platform_availability(platform)
                status = "✓ 可用" if available else "✗ 不可用"
                logger.info(f"{platform}: {status}")
            except Exception as e:
                logger.warning(f"{platform}: 检查失败 - {str(e)}")
                
        return True
        
    except Exception as e:
        logger.error(f"平台可用性检查失败: {str(e)}")
        return False

async def test_cross_platform_search():
    """测试跨平台搜索"""
    try:
        coordinator = SearchCoordinator()
        
        logger.info("测试跨平台搜索...")
        
        # 使用多个平台搜索
        keyword = "neural networks"
        selected_platforms = ['arxiv', 'semantic_scholar', 'core']
        
        results = await coordinator.search(keyword, platforms=selected_platforms, max_results=10)
        
        if results:
            logger.info(f"✓ 跨平台搜索成功，共找到 {len(results)} 篇论文")
            
            # 按平台分组显示
            platform_stats = {}
            for paper in results:
                platform = paper.get('platform', 'unknown')
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
            
            for platform, count in platform_stats.items():
                logger.info(f"  {platform}: {count} 篇")
                
            return True
        else:
            logger.warning("跨平台搜索未找到结果")
            return False
            
    except Exception as e:
        logger.error(f"跨平台搜索失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("扩展论文下载系统测试开始")
    logger.info("=" * 60)
    
    # 测试统计
    total_tests = 0
    passed_tests = 0
    
    try:
        # 1. 测试平台可用性
        logger.info("\n1. 测试平台可用性检查")
        logger.info("-" * 40)
        total_tests += 1
        if await test_platform_availability():
            passed_tests += 1
        
        # 2. 测试跨平台搜索
        logger.info("\n2. 测试跨平台搜索")
        logger.info("-" * 40)
        total_tests += 1
        if await test_cross_platform_search():
            passed_tests += 1
        
        # 3. 测试各个平台
        logger.info("\n3. 测试各个学术平台")
        logger.info("-" * 40)
        
        for platform in platforms:
            # 为每个平台选择不同的关键词
            keyword = test_keywords[hash(platform) % len(test_keywords)]
            
            total_tests += 1
            if await test_platform_search(platform, keyword):
                passed_tests += 1
            
            # 短暂延迟，避免过于频繁的请求
            await asyncio.sleep(1)
        
        # 4. 测试错误处理
        logger.info("\n4. 测试错误处理")
        logger.info("-" * 40)
        total_tests += 1
        
        try:
            coordinator = SearchCoordinator()
            # 测试无效平台
            results = await coordinator.search("test", platforms=["invalid_platform"])
            if not results:
                logger.info("✓ 无效平台处理正确")
                passed_tests += 1
            else:
                logger.warning("⚠ 无效平台测试未按预期工作")
        except Exception as e:
            logger.info(f"✓ 错误处理正常: {str(e)}")
            passed_tests += 1
        
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
    
    # 测试总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过测试: {passed_tests}")
    logger.info(f"失败测试: {total_tests - passed_tests}")
    logger.info(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        logger.info("✓ 所有测试通过！系统运行正常")
    else:
        logger.warning("⚠ 部分测试未通过，请检查日志")
    
    logger.info("\n扩展论文下载系统测试完成")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())