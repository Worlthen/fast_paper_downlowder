# 学术论文自动下载器

一个功能强大的Python工具，用于自动从多个学术平台搜索和下载PDF文件。

## 功能特性

- 🔍 **多平台搜索**: 支持 Google Scholar、Sci-Hub、arXiv
- 📄 **智能解析**: 自动解析各种格式的论文列表
- 💾 **批量下载**: 高效下载PDF文件
- ⚡ **异步处理**: 支持并发处理，提高效率
- 🔄 **智能重试**: 自动重试失败的下载任务
- 📝 **详细日志**: 完整的操作日志和错误记录
- ⚙️ **灵活配置**: 支持配置文件和命令行参数
- 🎨 **友好界面**: 美观的命令行界面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建论文列表

创建一个文本文件 `papers.txt`，每行一篇论文：

```
Aizawa T., & Inohara T. (2019). Pico- and femtosecond laser micromachining for surface texturing. Micromachining.
Alayed A., & Fayez F. (2025). Effects of process parameters on pulsed laser micromachining for glass-based microfluidic devices. Materials.
```

### 3. 运行程序

```bash
python main.py -i papers.txt
```

下载的PDF文件将保存在 `downloads/` 目录中。

## 详细使用说明

### 基本命令

```bash
# 基本使用
python main.py -i papers.txt

# 指定输出目录
python main.py -i papers.txt -o ./my_papers

# 选择搜索平台
python main.py -i papers.txt -p google_scholar,scihub

# 使用详细日志
python main.py -i papers.txt -l DEBUG

# 测试模式（只处理前3篇）
python main.py -i papers.txt --test-mode
```

### 创建示例文件

```bash
# 创建包含10篇论文的示例文件
python main.py create-sample -o sample_papers.txt -c 10
```

### 配置文件

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

## 支持的文件格式

### 输入文件格式

1. **文本文件 (.txt)**
   ```
   作者1, 作者2. (年份). 标题. 期刊.
   ```

2. **CSV文件 (.csv)**
   ```csv
   title,authors,year
   "论文标题","作者1, 作者2",2023
   ```

3. **JSON文件 (.json)**
   ```json
   [
     {
       "title": "论文标题",
       "authors": ["作者1", "作者2"],
       "year": 2023
     }
   ]
   ```

4. **Excel文件 (.xlsx/.xls)**
   包含 title, authors, year 列的Excel文件

### 输出文件

- **PDF文件**: 下载的论文PDF文件
- **元数据文件**: JSON格式的论文信息
- **日志文件**: 详细的操作日志
- **报告文件**: 下载统计报告

## 高级功能

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

### 错误处理和重试

程序具有智能的错误处理机制：

- 自动重试失败的下载任务
- 处理网络连接错误
- 处理PDF文件验证失败
- 记录详细的错误信息

## 故障排除

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

## 性能优化

### 提高下载速度

1. 增加并发数：
   ```bash
   python main.py -i papers.txt -C 5  # 5个并发下载
   ```

2. 使用异步模式（默认启用）

3. 使用代理服务器

### 减少请求延迟

在配置文件中调整延迟参数：

```yaml
SEARCH:
  GOOGLE_SCHOLAR:
    DELAY: 1.0  # 减少延迟
```

## 更新日志

### v1.0.0 (2024-01)
- ✨ 初始版本发布
- 🔍 支持Google Scholar和Sci-Hub搜索
- 📄 支持多种输入文件格式
- 💾 异步PDF下载
- 📝 完整的日志和报告功能

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 免责声明

本工具仅供学术研究和教育用途使用。用户应遵守相关平台的服务条款和版权法规。开发者不对工具的滥用承担责任。

## 支持

如遇到问题，请：

1. 查看本README文档
2. 检查日志文件获取详细信息
3. 在GitHub提交Issue

---

**Happy Downloading! 🎉**