# 学术论文自动下载器 - 使用指南

## 🎯 项目概述

这是一个功能强大的Python工具，可以自动从多个学术平台（Google Scholar、Sci-Hub、arXiv）搜索和下载学术论文PDF文件。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行安装脚本（可选）
```bash
python setup.py
```

### 3. 创建论文列表文件
创建一个文本文件，例如 `papers.txt`，每行一篇论文：
```
Aizawa T., & Inohara T. (2019). Pico- and femtosecond laser micromachining for surface texturing. Micromachining.
Alayed A., & Fayez F. (2025). Effects of process parameters on pulsed laser micromachining for glass-based microfluidic devices. Materials.
```

### 4. 运行程序
```bash
python main.py -i papers.txt
```

## 📋 支持的输入格式

### 文本文件 (.txt)
```
作者1, 作者2. (年份). 论文标题. 期刊名称.
```

### CSV文件 (.csv)
```csv
title,authors,year
"论文标题","作者1, 作者2",2023
```

### JSON文件 (.json)
```json
[
  {
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "year": 2023
  }
]
```

### Excel文件 (.xlsx/.xls)
包含 title, authors, year 列的Excel表格

## ⚙️ 命令行参数

```bash
python main.py [参数]

主要参数:
  -i, --input          输入文件路径（必需）
  -o, --output         输出目录（默认: ./downloads）
  -p, --platforms      搜索平台（默认: all）
  -n, --max-results    每个平台最大结果数（默认: 5）
  -C, --max-concurrent 并发下载数（默认: 3）
  -l, --log-level      日志级别（默认: INFO）
  --test-mode          测试模式（只处理前3篇）
  --async/--sync       异步/同步模式
  --overwrite          覆盖现有文件
```

## 🎯 使用示例

### 基本使用
```bash
python main.py -i papers.txt
```

### 指定输出目录和平台
```bash
python main.py -i papers.txt -o ./my_papers -p google_scholar,scihub
```

### 测试模式
```bash
python main.py -i papers.txt --test-mode
```

### 创建示例文件
```bash
python main.py create-sample -o sample_papers.txt -c 10
```

### 详细日志模式
```bash
python main.py -i papers.txt -l DEBUG
```

## 📊 输出文件结构

```
downloads/
├── pdfs/                    # 下载的PDF文件
│   ├── Author1_Author2_2023_Title.pdf
│   └── ...
├── metadata/                # 元数据文件
│   ├── Author1_Author2_2023_Title.json
│   └── ...
└── logs/                    # 日志文件
    ├── download_report_20240101_120000.json
    └── paper_downloader.log
```

## 🔧 配置文件

编辑 `config.yaml` 文件来自定义程序行为：

```yaml
# 搜索配置
SEARCH:
  GOOGLE_SCHOLAR:
    MAX_RESULTS: 10
    DELAY: 2.0
  
  SCIHUB:
    MIRRORS:
      - "https://sci-hub.se"
      - "https://sci-hub.st"

# 下载配置
DOWNLOAD:
  MAX_CONCURRENT: 3
  TIMEOUT: 60
  RETRY_ATTEMPTS: 3

# 日志配置
LOGGING:
  LEVEL: "INFO"
  FILE: "paper_downloader.log"
```

## 🛠️ 高级功能

### 异步处理
程序默认使用异步处理，可以显著提高下载效率：
```bash
python main.py -i papers.txt --async  # 启用异步（默认）
python main.py -i papers.txt --sync   # 禁用异步
```

### 代理支持
在配置文件中设置代理：
```yaml
PROXY:
  ENABLED: true
  HTTP_PROXY: "http://proxy.example.com:8080"
  HTTPS_PROXY: "https://proxy.example.com:8080"
```

### 性能优化
1. 增加并发数：
   ```bash
   python main.py -i papers.txt -C 5  # 5个并发下载
   ```

2. 减少请求延迟：
   ```yaml
   SEARCH:
     GOOGLE_SCHOLAR:
       DELAY: 1.0  # 减少延迟
   ```

## 🚨 注意事项

1. **使用频率**: 请合理设置请求延迟，避免对学术平台造成过大负担
2. **版权问题**: 下载的论文仅供个人学术研究使用，请遵守相关版权法规
3. **平台限制**: 某些平台可能有访问限制，建议使用代理或VPN
4. **网络环境**: 确保网络连接稳定，特别是下载大文件时

## 🔍 故障排除

### 常见问题

1. **WebDriver问题**
   ```
   错误: Selenium WebDriver初始化失败
   解决: 确保Chrome浏览器已安装，或禁用Selenium模式
   ```

2. **搜索无结果**
   ```
   错误: 所有平台搜索失败
   解决: 检查网络连接，尝试不同的搜索关键词
   ```

3. **下载失败**
   ```
   错误: PDF下载失败
   解决: 检查网络连接，尝试使用代理
   ```

### 调试模式
使用调试模式获取详细信息：
```bash
python main.py -i papers.txt -l DEBUG
```

## 📈 统计信息

程序会生成详细的统计报告，包括：
- 总论文数量
- 搜索成功率
- 下载成功率
- 文件总大小
- 下载时间统计

## 🧪 测试

运行测试套件：
```bash
python test_downloader.py
```

或安装pytest后运行：
```bash
pytest test_downloader.py -v
```

## 📚 项目结构

```
.
├── main.py                 # 主程序
├── coordinator.py          # 协调器模块
├── paper_parser.py         # 论文解析模块
├── google_scholar.py       # Google Scholar搜索模块
├── scihub.py              # Sci-Hub搜索模块
├── pdf_downloader.py      # PDF下载管理器
├── config.py              # 配置常量
├── config.yaml            # 配置文件
├── requirements.txt       # 依赖列表
├── setup.py               # 安装脚本
├── test_downloader.py     # 测试模块
├── sample_papers.txt      # 示例论文列表
└── README.md              # 项目文档
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

MIT License - 详见 LICENSE 文件

## ⚖️ 免责声明

本工具仅供学术研究和教育用途使用。用户应遵守相关平台的服务条款和版权法规。开发者不对工具的滥用承担责任。

---

**Happy Downloading! 🎉**