# 学术论文自动下载器

__version__ = "1.0.0"
__author__ = "Academic Paper Downloader"
__description__ = "自动化的学术论文搜索和下载工具"

# 支持的搜索平台
SUPPORTED_PLATFORMS = [
    "arxiv",
    "pubmed",
    "doaj",
    "core",
    "zenodo",
    "hal",
    "biorxiv",
    "semantic_scholar",
    "researchgate",
    "academia",
    "google_scholar",
    "scihub"
]

# 默认配置
DEFAULT_CONFIG = {
    "output_dir": "./downloads",
    "max_concurrent": 3,
    "timeout": 60,
    "retry_attempts": 3,
    "delay": 2.0,
    "max_results": 10
}

# Sci-Hub镜像列表
SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st", 
    "https://sci-hub.ru",
    "https://sci-hub.tw"
]

# 用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

# 文件扩展名
PDF_EXTENSIONS = [".pdf", ".PDF"]
ALLOWED_EXTENSIONS = PDF_EXTENSIONS

# 日志配置
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# 错误消息
ERROR_MESSAGES = {
    "NETWORK_ERROR": "网络连接错误",
    "TIMEOUT_ERROR": "请求超时",
    "NOT_FOUND": "未找到论文",
    "ACCESS_DENIED": "访问被拒绝",
    "PDF_NOT_AVAILABLE": "PDF文件不可用",
    "INVALID_RESPONSE": "无效的响应",
    "PARSER_ERROR": "解析错误",
    "FILESYSTEM_ERROR": "文件系统错误"
}

# 新平台配置
PLATFORM_CONFIGS = {
    "pubmed_central": {
        "base_url": "https://www.ncbi.nlm.nih.gov/pmc",
        "search_path": "/tools/search/",
        "api_base": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        "max_results": 20,
        "delay": 1.0
    },
    "doaj": {
        "base_url": "https://doaj.org",
        "search_path": "/search",
        "api_base": "https://doaj.org/api/v2",
        "max_results": 20,
        "delay": 1.0
    },
    "core": {
        "base_url": "https://core.ac.uk",
        "api_base": "https://api.core.ac.uk/v3",
        "max_results": 20,
        "delay": 1.0
    },
    "semantic_scholar": {
        "base_url": "https://api.semanticscholar.org",
        "api_version": "v1",
        "max_results": 20,
        "delay": 0.5
    },
    "researchgate": {
        "base_url": "https://www.researchgate.net",
        "search_path": "/search",
        "max_results": 10,
        "delay": 2.0
    },
    "academia_edu": {
        "base_url": "https://www.academia.edu",
        "search_path": "/search",
        "max_results": 10,
        "delay": 2.0
    },
    "zenodo": {
        "base_url": "https://zenodo.org",
        "api_base": "https://zenodo.org/api",
        "max_results": 20,
        "delay": 1.0
    },
    "hal": {
        "base_url": "https://hal.archives-ouvertes.fr",
        "api_base": "https://api.archives-ouvertes.fr",
        "max_results": 20,
        "delay": 1.0
    },
    "biorxiv": {
        "base_url": "https://www.biorxiv.org",
        "api_base": "https://api.biorxiv.org",
        "max_results": 20,
        "delay": 1.0
    },
    "medrxiv": {
        "base_url": "https://www.medrxiv.org",
        "api_base": "https://api.medrxiv.org",
        "max_results": 20,
        "delay": 1.0
    }
}

# 平台可用性检查配置
PLATFORM_AVAILABILITY_CHECK = {
    "timeout": 10,
    "retry_attempts": 2,
    "check_interval": 300  # 5分钟
}

# 开放获取优先级配置
OPEN_ACCESS_PRIORITY = [
    "arxiv",
    "pubmed_central", 
    "doaj",
    "core",
    "zenodo",
    "hal",
    "biorxiv",
    "medrxiv",
    "semantic_scholar",
    "researchgate",
    "academia_edu",
    "google_scholar",
    "scihub"
]