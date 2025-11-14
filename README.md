# Fast Paper Downloader

一个精简、高效的Python工具，用于根据论文标题列表自动下载学术论文。

## 功能特性

- 🔍 **多平台搜索**: 自动在 Google Scholar, Sci-Hub, arXiv 等多个平台搜索论文。
- 📄 **智能解析**: 支持从 `.txt`, `.csv`, `.xlsx`, `.xls`, `.json` 文件中解析论文列表。
- 💾 **批量下载**: 高效地批量下载PDF文件。
- ⚡ **异步处理**: 基于 `asyncio` 实现并发处理，显著提高下载效率。
- 📝 **详细日志**: 提供清晰的操作日志和错误记录，便于追踪。

## 快速开始

### 1. 安装依赖

首先，请确保您已安装 Python 3.8+。然后，在项目根目录下运行以下命令安装所需依赖：

```bash
pip install -r requirements.txt
```

### 2. 创建论文列表

创建一个名为 `papers.txt` 的文本文件，每行包含一篇您想下载的论文标题。

```
Aizawa T., \u0026 Inohara T. (2019). Pico- and femtosecond laser micromachining for surface texturing. Micromachining.
Alayed A., \u0026 Fayez F. (2025). Effects of process parameters on pulsed laser micromachining for glass-based microfluidic devices. Materials.
```

### 3. 运行程序

使用以下命令启动下载器：

```bash
python main.py --input papers.txt
```

下载的PDF文件将默认保存在 `downloads/` 目录中。

## 使用说明

程序现在只提供最核心的命令行选项，以实现最大程度的简化。

### 命令格式

```bash
python main.py --input \u003c文件路径\u003e [选项]
```

### 可用选项

| 选项 | 缩写 | 描述 | 默认值 |
|---|---|---|---|
| `--input` | `-i` | **必需**。包含论文标题的输入文件路径。 | 无 |
| `--output` | `-o` | 下载论文的输出目录。 | `./downloads` |
| `--log-level` | `-l` | 设置日志级别 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)。 | `INFO` |
| `--log-file` | | 将日志额外输出到指定文件。 | 无 |
| `--proxy` | | 启用网络代理（需在 `config.yaml` 中配置）。| `False` |

### 使用示例

```bash
# 基本用法
python main.py --input papers.txt

# 指定输出目录和日志级别
python main.py -i papers.txt -o ./my_papers -l DEBUG

# 启用代理并记录日志到文件
python main.py -i papers.txt --proxy --log-file downloader.log
```

## 代理配置

如需使用网络代理，请执行以下两个步骤：

1.  在项目根目录下创建一个名为 `config.yaml` 的文件。
2.  在 `config.yaml` 文件中添加您的代理服务器地址，格式如下：

    ```yaml
    proxy:
      http: "http://127.0.0.1:7890"
      https: "http://127.0.0.1:7890"
    ```

完成配置后，在运行程序时加上 `--proxy` 标志即可启用代理。

## 免责声明

本工具仅供学术研究和教育用途。用户在使用本工具时，应严格遵守相关学术平台的服务条款和版权法规。开发者不对任何因滥用本工具而导致的法律问题负责。

## 许可证

本项目基于 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。