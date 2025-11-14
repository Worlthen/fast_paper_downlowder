# 安装脚本
# 用于安装必要的依赖和配置环境

import subprocess
import sys
import os
from pathlib import Path

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ 成功安装: {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ 安装失败: {package}")
        return False

def install_requirements():
    """安装requirements.txt中的所有依赖"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt文件不存在")
        return False
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print("✅ 成功安装所有依赖")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装依赖失败: {e}")
        return False

def check_chrome():
    """检查Chrome浏览器"""
    try:
        # 尝试导入selenium
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        # 尝试安装ChromeDriver
        ChromeDriverManager().install()
        print("✅ ChromeDriver配置成功")
        return True
        
    except ImportError:
        print("⚠️  Selenium未安装，跳过Chrome检查")
        return True
    except Exception as e:
        print(f"⚠️  ChromeDriver配置失败: {e}")
        print("ℹ️  程序仍可使用requests模式运行")
        return True

def create_directories():
    """创建必要的目录"""
    directories = [
        "downloads",
        "logs",
        "test_downloads"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ 创建目录: {directory}")

def main():
    """主安装函数"""
    print("🚀 开始安装学术论文自动下载器...")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装依赖
    print("\n📦 安装依赖包...")
    if not install_requirements():
        print("❌ 依赖安装失败")
        sys.exit(1)
    
    # 检查Chrome
    print("\n🔍 检查Chrome配置...")
    check_chrome()
    
    # 创建目录
    print("\n📁 创建目录...")
    create_directories()
    
    print("\n" + "=" * 50)
    print("✅ 安装完成！")
    print("\n📖 使用说明:")
    print("  1. 创建论文列表文件，例如: papers.txt")
    print("  2. 运行程序: python main.py -i papers.txt")
    print("  3. 查看帮助: python main.py --help")
    print("\n🔧 测试安装:")
    print("  python main.py create-sample -o test_papers.txt")
    print("  python main.py -i test_papers.txt --test-mode")

if __name__ == "__main__":
    main()