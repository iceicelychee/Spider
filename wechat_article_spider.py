#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信公众号文章爬虫 - 简化版
功能：爬取微信公众号文章，保存为 Markdown 格式，使用标签分类
"""

import os
import re
import hashlib
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime


import time
import random
try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False

class WechatArticleSpider:
    def __init__(self, output_dir="articles"):
        """
        初始化爬虫
        :param output_dir: 输出目录
        """
        # UA 轮换相关（必须最先设置）
        self.use_random_ua = True
        
        # 初始化 UserAgent 生成器
        if HAS_FAKE_UA:
            try:
                self.ua = UserAgent()
            except:
                self.ua = None
        else:
            self.ua = None
        
        # 默认请求头
        self.default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.headers = self._generate_headers()
        
        # 用于下载图片的 headers
        self.img_headers = {
            "User-Agent": self.default_ua,
            "Referer": "https://mp.weixin.qq.com/",
        }
        
        # 代理相关
        self.proxies_list = []
        self.use_proxy = False
        self.current_proxy = None
        
        # 延迟相关
        self.base_delay = 1.0
        self.use_random_delay = True
        
        # 设置输出目录
        self.set_output_dir(output_dir)
    
    def _generate_headers(self, referer=None):
        """生成请求头，模拟真实浏览器"""
        # 获取 User-Agent
        if self.use_random_ua and self.ua:
            try:
                user_agent = self.ua.random
            except:
                user_agent = self.default_ua
        else:
            user_agent = self.default_ua
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        if referer:
            headers["Referer"] = referer
        
        return headers
    
    def set_output_dir(self, output_dir):
        """设置并创建输出目录"""
        self.output_dir = output_dir
        self.index_file = os.path.join(output_dir, "INDEX.json")
        
        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 确保图片目录存在
        img_dir = os.path.join(self.output_dir, "images")
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        
        print(f"下载位置已设置为: {os.path.abspath(self.output_dir)}")
    
    def set_proxies(self, proxies_str):
        """设置代理列表，格式：ip:port, 每行一个或逗号分隔"""
        if not proxies_str:
            self.proxies_list = []
            return
        
        # 分割并清理
        raw_list = proxies_str.replace('\n', ',').split(',')
        self.proxies_list = [p.strip() for p in raw_list if p.strip()]
        if self.proxies_list:
            print(f"成功加载 {len(self.proxies_list)} 个代理")
    
    def _get_random_proxy(self):
        """从代理池随机获取一个代理"""
        if not self.proxies_list:
            return None
        proxy_addr = random.choice(self.proxies_list)
        return {
            "http": f"http://{proxy_addr}",
            "https": f"http://{proxy_addr}"
        }

    def fetch_article(self, url):
        """获取文章页面内容"""
        # 随机延迟
        if self.use_random_delay:
            delay = self.base_delay + random.uniform(0.5, 2.0)
            print(f"等待 {delay:.2f} 秒...")
            time.sleep(delay)
        
        # 每次请求重新生成 headers（如果启用了随机 UA）
        if self.use_random_ua:
            self.headers = self._generate_headers()
            print(f"使用 User-Agent: {self.headers['User-Agent'][:50]}...")
            
        max_retries = 3
        for i in range(max_retries):
            try:
                proxies = None
                if self.use_proxy and self.proxies_list:
                    proxies = self._get_random_proxy()
                    if proxies:
                        print(f"正在使用代理: {proxies['http']}")
                else:
                    if self.use_proxy:
                        print("警告: 已启用代理但代理列表为空，使用直连")
                
                response = requests.get(url, headers=self.headers, proxies=proxies, timeout=15)
                response.encoding = 'utf-8'
                
                if response.status_code == 200:
                    print("请求成功！")
                    return response.text
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"请求失败 (尝试 {i+1}/{max_retries}): {error_msg}")
                
                # 如果是代理问题，尝试切换代理或建议
                if self.use_proxy and ('ProxyError' in error_msg or 'ConnectionError' in error_msg or 'timeout' in error_msg.lower()):
                    print("提示: 当前代理可能无效，正在尝试切换...")
                
                if i == max_retries - 1:
                    print("\n爬取失败！所有重试均已失败。")
                    if self.use_proxy:
                        print("建议: 请检查代理IP是否有效，或尝试关闭代理后直连。")
                    return None
                    
                # 失败后等待一会再重试
                time.sleep(1)
                
        return None
    
    def parse_article(self, html, url):
        """解析文章内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        article = {
            "url": url,
            "title": "",
            "author": "",
            "account": "",
            "publish_time": "",
            "content": "",
            "images": []
        }
        
        # 提取标题
        title_elem = soup.find('h1', class_='rich_media_title') or soup.find('h1', id='activity-name')
        if title_elem:
            article["title"] = title_elem.get_text(strip=True)
        
        # 提取公众号名称
        account_elem = soup.find('a', class_='weui-wa-hotarea') or soup.find('strong', class_='profile_nickname')
        if account_elem:
            article["account"] = account_elem.get_text(strip=True)
        
        # 提取作者
        author_elem = soup.find('span', class_='rich_media_meta_text')
        if author_elem:
            article["author"] = author_elem.get_text(strip=True)
        
        # 提取发布时间
        time_elem = soup.find('em', id='publish_time')
        if time_elem:
            article["publish_time"] = time_elem.get_text(strip=True)
        
        # 提取正文内容
        content_elem = soup.find('div', class_='rich_media_content') or soup.find('div', id='js_content')
        if content_elem:
            article["content"], article["images"] = self._parse_content(content_elem)
        
        return article
    
    def _parse_content(self, content_elem):
        """解析正文内容，转换为 Markdown 格式"""
        images = []
        markdown_lines = []
        
        for elem in content_elem.find_all(['p', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li', 'span', 'section']):
            if elem.name == 'p' or elem.name == 'span' or elem.name == 'section':
                # 如果是 section 或 span，只处理没有子标签的或者是直接包含文本的
                if elem.name in ['section', 'span']:
                    if elem.find(['p', 'section', 'span']):
                        continue
                
                text = elem.get_text(strip=True)
                if text:
                    markdown_lines.append(text + "\n")
            
            elif elem.name == 'img':
                img_url = elem.get('data-src') or elem.get('src')
                if img_url and 'mmbiz.qpic.cn' in img_url:
                    images.append(img_url)
                    markdown_lines.append(f"![图片](images/{self._get_img_filename(img_url)})\n")
            
            elif elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(elem.name[1])
                text = elem.get_text(strip=True)
                if text:
                    markdown_lines.append(f"{'#' * level} {text}\n")
            
            elif elem.name == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    markdown_lines.append(f"> {text}\n")
            
            elif elem.name == 'li':
                text = elem.get_text(strip=True)
                if text:
                    markdown_lines.append(f"- {text}\n")
        
        # 去重
        seen = set()
        cleaned_lines = []
        for line in markdown_lines:
            if line.strip() and line not in seen:
                seen.add(line)
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines), images
    
    def _get_img_filename(self, url):
        """根据图片URL生成文件名"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        if 'wx_fmt=' in url:
            fmt = re.search(r'wx_fmt=(\w+)', url)
            ext = fmt.group(1) if fmt else 'png'
        else:
            ext = 'png'
        return f"{url_hash}.{ext}"
    
    def download_image(self, img_url, save_dir):
        """下载图片"""
        try:
            filename = self._get_img_filename(img_url)
            filepath = os.path.join(save_dir, filename)
            
            if os.path.exists(filepath):
                print(f"图片已存在: {filename}")
                return True
            
            # 图片下载也使用代理（如果启用）
            proxies = None
            if self.use_proxy and self.proxies_list:
                proxies = self._get_random_proxy()
            
            response = requests.get(img_url, headers=self.img_headers, proxies=proxies, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"下载成功: {filename}")
                return True
            else:
                print(f"下载失败: {img_url}, 状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"下载图片出错: {e}")
            return False
    
    def save_as_markdown(self, article, tags=""):
        """将文章保存为 Markdown 文件"""
        # 创建图片目录
        img_dir = os.path.join(self.output_dir, "images")
        
        # 下载图片
        for img_url in article["images"]:
            self.download_image(img_url, img_dir)
        
        # 生成安全的文件名
        safe_title = re.sub(r'[\\/*?:"<>|]', '', article["title"])[:50]
        if not safe_title:
            safe_title = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 格式化标签
        tag_line = ""
        if tags:
            tag_list = [f"#{tag.strip()}" for tag in tags.split(',') if tag.strip()]
            tag_line = " ".join(tag_list)
        
        # 生成 Markdown 内容
        md_content = f"""# {article["title"]}

{tag_line}

> **公众号**: {article["account"]}  
> **作者**: {article["author"]}  
> **发布时间**: {article["publish_time"]}  
> **原文链接**: {article["url"]}

---

{article["content"]}

---

收藏时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        # 保存 Markdown 文件
        md_filename = f"{safe_title}.md"
        md_path = os.path.join(self.output_dir, md_filename)
        
        # 如果文件名冲突，添加时间戳
        if os.path.exists(md_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_filename = f"{safe_title}_{timestamp}.md"
            md_path = os.path.join(self.output_dir, md_filename)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return md_path, md_filename
    
    def update_index(self, article, filename, tags=""):
        """更新索引文件"""
        # 读取现有索引
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"articles": [], "tags": {}}
        
        # 添加文章信息
        article_info = {
            "filename": filename,
            "title": article["title"],
            "account": article["account"],
            "author": article["author"],
            "publish_time": article["publish_time"],
            "url": article["url"],
            "tags": tags,
            "image_count": len(article["images"]),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 检查是否已存在（根据URL）
        existing = False
        for i, item in enumerate(index["articles"]):
            if item["url"] == article["url"]:
                index["articles"][i] = article_info
                existing = True
                break
        
        if not existing:
            index["articles"].append(article_info)
        
        # 更新标签统计
        if tags:
            for tag in tags.split(','):
                tag = tag.strip()
                if tag:
                    index["tags"][tag] = index["tags"].get(tag, 0) + 1
        
        # 保存索引
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"索引更新成功")
    
    def crawl(self, url, tags=""):
        """
        爬取文章
        :param url: 文章URL
        :param tags: 标签（多个用逗号分隔，如：技术,Python,爬虫）
        :return: 保存路径
        """
        print(f"开始爬取: {url}")
        
        # 获取页面内容
        html = self.fetch_article(url)
        if not html:
            return None
        
        # 解析文章
        article = self.parse_article(html, url)
        if not article["title"]:
            print("解析失败：未找到文章标题")
            return None
        
        print(f"标题: {article['title']}")
        print(f"公众号: {article['account']}")
        print(f"标签: {tags if tags else '无'}")
        print(f"图片数量: {len(article['images'])}")
        
        # 保存为 Markdown
        md_path, filename = self.save_as_markdown(article, tags)
        print(f"Markdown 保存成功: {md_path}")
        
        # 更新索引
        self.update_index(article, filename, tags)
        
        return md_path
    
    def list_all(self):
        """列出所有文章"""
        if not os.path.exists(self.index_file):
            print("暂无文章")
            return
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        articles = index.get("articles", [])
        if not articles:
            print("暂无文章")
            return
        
        print(f"\n共有 {len(articles)} 篇文章：")
        print("=" * 80)
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   公众号: {article['account']}")
            print(f"   标签: {article['tags'] if article['tags'] else '无'}")
            print(f"   文件: {article['filename']}")
            print("-" * 80)
    
    def list_tags(self):
        """列出所有标签"""
        if not os.path.exists(self.index_file):
            print("暂无标签")
            return
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        tags = index.get("tags", {})
        if not tags:
            print("暂无标签")
            return
        
        print("\n所有标签：")
        for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
            print(f"  #{tag}: {count} 篇")
    
    def search_by_tag(self, tag):
        """按标签搜索文章"""
        if not os.path.exists(self.index_file):
            print("暂无文章")
            return
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        articles = index.get("articles", [])
        results = [a for a in articles if tag.lower() in a['tags'].lower()]
        
        if not results:
            print(f"未找到标签为 '{tag}' 的文章")
            return
        
        print(f"\n找到 {len(results)} 篇文章：")
        print("=" * 80)
        for i, article in enumerate(results, 1):
            print(f"{i}. {article['title']}")
            print(f"   公众号: {article['account']}")
            print(f"   标签: {article['tags']}")
            print(f"   文件: {article['filename']}")
            print("-" * 80)


import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

class WechatSpiderGUI:
    def __init__(self, spider):
        self.spider = spider
        self.root = tk.Tk()
        self.root.title("微信公众号文章爬虫")
        self.root.geometry("600x500")
        
        self.setup_ui()
    
    def setup_ui(self):
        # 路径选择
        path_frame = ttk.LabelFrame(self.root, text="设置", padding=10)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(path_frame, text="保存位置:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar(value=os.path.abspath(self.spider.output_dir))
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_path).grid(row=0, column=2)
        
        # 代理与频率设置
        config_frame = ttk.LabelFrame(self.root, text="防封设置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self.proxy_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="启用代理", variable=self.proxy_enable_var).grid(row=0, column=0, sticky="w")
        
        ttk.Label(config_frame, text="代理列表(ip:port, 逗号分隔):").grid(row=0, column=1, sticky="w", padx=5)
        self.proxy_list_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.proxy_list_var, width=35).grid(row=0, column=2)
        
        self.delay_enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="随机延迟", variable=self.delay_enable_var).grid(row=1, column=0, sticky="w")
        
        ttk.Label(config_frame, text="基础延迟(秒):").grid(row=1, column=1, sticky="w", padx=5)
        self.delay_val_var = tk.StringVar(value="1.0")
        ttk.Entry(config_frame, textvariable=self.delay_val_var, width=10).grid(row=1, column=2, sticky="w")
        
        self.ua_enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="随机 UA", variable=self.ua_enable_var).grid(row=2, column=0, sticky="w")
        ttk.Label(config_frame, text="模拟真实浏览器，随机轮换 User-Agent", font=('Arial', 8)).grid(row=2, column=1, columnspan=2, sticky="w", padx=5)

        # 爬取输入
        crawl_frame = ttk.LabelFrame(self.root, text="爬取新文章", padding=10)
        crawl_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(crawl_frame, text="文章链接:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(crawl_frame, textvariable=self.url_var, width=60).grid(row=0, column=1, columnspan=2, pady=5)
        
        ttk.Label(crawl_frame, text="文章标签:").grid(row=1, column=0, sticky="w")
        self.tags_var = tk.StringVar()
        ttk.Entry(crawl_frame, textvariable=self.tags_var, width=60).grid(row=1, column=1, columnspan=2, pady=5)
        
        self.crawl_btn = ttk.Button(crawl_frame, text="开始爬取", command=self.start_crawl)
        self.crawl_btn.grid(row=2, column=1, pady=10)
        
        # 日志输出
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True)
        
        # 简单的重定向 print
        self.original_print = print
        import builtins
        builtins.print = self.gui_print
    
    def gui_print(self, *args, **kwargs):
        msg = " ".join(map(str, args)) + "\n"
        self.log_text.insert("end", msg)
        self.log_text.see("end")
        self.original_print(*args, **kwargs)
    
    def browse_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
            self.spider.set_output_dir(directory)
    
    def start_crawl(self):
        url = self.url_var.get().strip()
        tags = self.tags_var.get().strip()
        
        if not url or 'mp.weixin.qq.com' not in url:
            messagebox.showerror("错误", "请输入有效的微信公众号文章链接")
            return
        
        # 同步 GUI 配置到 spider
        self.spider.use_proxy = self.proxy_enable_var.get()
        self.spider.set_proxies(self.proxy_list_var.get())
        self.spider.use_random_delay = self.delay_enable_var.get()
        self.spider.use_random_ua = self.ua_enable_var.get()
        try:
            self.spider.base_delay = float(self.delay_val_var.get())
        except:
            self.spider.base_delay = 1.0
        
        self.crawl_btn.config(state="disabled")
        threading.Thread(target=self.crawl_thread, args=(url, tags), daemon=True).start()
    
    def crawl_thread(self, url, tags):
        try:
            result = self.spider.crawl(url, tags)
            if result:
                messagebox.showinfo("成功", "文章爬取完成！")
            else:
                messagebox.showerror("失败", "爬取失败！\n\n可能原因：\n1. 网络连接问题\n2. 代理IP无效（如已启用）\n3. 文章链接失效或被删除\n\n建议：\n- 检查网络连接\n- 尝试关闭代理后直连\n- 确认文章链接是否有效")
        except Exception as e:
            messagebox.showerror("失败", f"爬取过程中出错:\n{str(e)}\n\n建议检查日志获取详细信息")
        finally:
            self.root.after(0, lambda: self.crawl_btn.config(state="normal"))
            self.root.after(0, lambda: self.url_var.set(""))

    def run(self):
        self.root.mainloop()

def main():
    """主函数"""
    spider = WechatArticleSpider(output_dir="articles")
    
    # 询问用户使用哪种模式
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli(spider)
    else:
        gui = WechatSpiderGUI(spider)
        gui.run()

def run_cli(spider):
    print("=" * 50)
    print("微信公众号文章爬虫 (命令行模式)")
    print("=" * 50)
    
    while True:
        print(f"\n当前下载位置: {os.path.abspath(spider.output_dir)}")
        print("请选择操作：")
        print("1. 爬取文章")
        print("2. 查看所有文章")
        print("3. 查看所有标签")
        print("4. 按标签搜索")
        print("5. 设置下载位置")
        print("6. 退出")
        
        choice = input("\n请输入选项 (1-6): ").strip()
        
        if choice == '1':
            url = input("\n请输入微信公众号文章链接: ").strip()
            
            if not url:
                print("链接不能为空")
                continue
            
            if 'mp.weixin.qq.com' not in url:
                print("请输入有效的微信公众号文章链接")
                continue
            
            tags = input("请输入标签（多个用逗号分隔，如：技术,Python）: ").strip()
            
            spider.crawl(url, tags=tags)
        
        elif choice == '2':
            spider.list_all()
        
        elif choice == '3':
            spider.list_tags()
        
        elif choice == '4':
            tag = input("\n请输入标签: ").strip()
            if tag:
                spider.search_by_tag(tag)
        
        elif choice == '5':
            new_dir = input(f"\n请输入新的下载目录 (当前: {spider.output_dir}): ").strip()
            if new_dir:
                spider.set_output_dir(new_dir)
        
        elif choice == '6':
            print("退出程序")
            break
        
        else:
            print("无效的选项，请重新输入")


if __name__ == "__main__":
    main()
