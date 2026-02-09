# Spider
一个功能强大的微信公众号文章爬虫工具，支持图形化界面操作，自动保存为 Markdown 格式

## 一、安装依赖

### 方式一：使用 requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

### 方式二：手动安装

```bash
pip install requests beautifulsoup4 fake-useragent lxml
```

## 二、 使用方法

### 1. 图形界面模式（默认）

直接运行脚本或 EXE 文件：

```bash
python wechat_article_spider.py
```

或双击运行打包好的 `wechat_article_spider.exe`

# 三、输出结构

```
articles/
├── INDEX.json              # 文章索引文件
├── images/                 # 图片存储目录
│   ├── abc123def456.png
│   └── ...
├── 文章标题1.md
├── 文章标题2.md
└── ...
```

## ⚠️ 注意事项

1. **仅用于学习交流**：请遵守相关法律法规，不得用于商业用途
2. **尊重版权**：爬取的文章仅供个人学习使用，请勿二次传播
3. **合理使用频率**：建议开启随机延迟，避免频繁请求导致 IP 被封
4. **代理 IP 有效性**：如果启用代理，请确保代理 IP 可用且支持 HTTPS


