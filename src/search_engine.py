# src/search_engine.py

import os
import time
import logging
import requests
import random
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from urllib.parse import urljoin, urlparse
from typing import List, Dict

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class ImageSearcher:
    def __init__(self, download_timeout=15): # 增加超时时间以适应大图下载
        self.timeout = download_timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

    def search_text(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """
        联网搜索文本资料 (增强版)
        获取更多结果以供筛选
        """
        logger.info(f"🔍 [Text Search] '{keyword}'")
        results = []
        try:
            with DDGS() as ddgs:
                gen_results = ddgs.text(
                    keywords=keyword, 
                    region="wt-wt", 
                    safesearch="off", 
                    timelimit="y", # 限制一年内，保证时效性
                    max_results=max_results
                )
                results = list(gen_results)
        except Exception as e:
            logger.error(f"DDGS Text Search Error: {e}")
        return results

    def search_and_download(self, keyword: str, save_dir: str) -> str:
        """
        搜图并下载 (高质量优先策略)
        1. 优先尝试 Large + Wide (高清横图)
        2. 失败则降级为 Medium (中等图)
        3. 验证文件大小 (>50KB) 确保清晰度
        """
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 策略 A: 优先寻找高清大图 (WallPaper/Large) + 横构图 (Wide)
        logger.info(f"🎨 [Image Search] '{keyword}' (High Quality Mode)")
        hq_urls = self._fetch_image_urls_ddgs(keyword, size="Large", layout="Wide")
        
        # 策略 B: 如果高清图没结果，尝试中等尺寸
        if not hq_urls:
            logger.info("⚠️ 高清图未找到，降级为普通搜索...")
            hq_urls = self._fetch_image_urls_ddgs(keyword, size="Medium", layout=None)
            
        # 策略 C: 备用爬虫
        if not hq_urls:
            logger.info("⚠️ DDGS 失效，启用备用爬虫...")
            hq_urls = self._fetch_image_urls_bing_backup(keyword)

        if not hq_urls:
            return None

        # 遍历下载，直到找到一张质量合格的图片
        for url in hq_urls:
            # 生成唯一文件名
            filename = f"{int(time.time())}_{random.randint(1000,9999)}.jpg"
            save_path = os.path.join(save_dir, filename)
            
            # 下载并验证质量
            if self._download_image(url, save_path, min_size_kb=50): # 至少50KB
                return save_path
                
        return None

    def _fetch_image_urls_ddgs(self, keyword, size="Large", layout="Wide"):
        urls = []
        try:
            with DDGS() as ddgs:
                # size 参数: Small, Medium, Large, Wallpaper
                # layout 参数: Square, Tall, Wide
                results = ddgs.images(
                    keywords=keyword, 
                    region="wt-wt", 
                    safesearch="off", 
                    size=size, 
                    layout=layout,
                    max_results=10 # 多抓取一些供筛选
                )
                urls = [r.get('image') for r in results if r.get('image')]
        except Exception as e:
            logger.warning(f"DDGS Image Search Error: {e}")
        return urls

    def _fetch_image_urls_bing_backup(self, keyword):
        """备用爬虫 (通常只能获取到中等质量)"""
        urls = []
        try:
            search_url = f"https://www.bing.com/images/search?q={keyword}&first=1"
            response = requests.get(search_url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(response.text, 'lxml')
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    urls.append(src)
        except Exception:
            pass
        return list(set(urls))[:15]

    def _download_image(self, url, save_path, min_size_kb=30):
        """
        下载并执行严格的质量检查
        :param min_size_kb: 最小文件大小 (KB)，低于此值视为缩略图/坏图
        """
        try:
            headers = self.headers.copy()
            parsed_url = urlparse(url)
            headers['Referer'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.content
                file_size_kb = len(content) / 1024
                
                # 1. 大小检查
                if file_size_kb < min_size_kb:
                    logger.warning(f"  -> 跳过过小图片: {file_size_kb:.1f}KB < {min_size_kb}KB")
                    return False
                
                # 2. 格式检查 (Magic Number)
                header = content[:4].hex().upper()
                if header.startswith("FFD8") or header.startswith("89504E47"): # JPG or PNG
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    logger.info(f"  ✅ 图片下载成功 ({file_size_kb:.1f}KB): {save_path}")
                    return True
                else:
                    logger.warning(f"  -> 格式不支持: {header}")
                    
        except Exception as e:
            logger.warning(f"  -> 下载异常: {str(e)[:50]}...")
            pass
        return False
