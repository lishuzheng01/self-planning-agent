# test_phase1.py

import os
import shutil
from src.search_engine import ImageSearcher

def test_workflow():
    # 1. 清理测试目录
    test_dir = "./output/test_assets"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    # 2. 初始化搜图引擎
    searcher = ImageSearcher()

    # 3. 定义几个测试用例
    test_queries = [
        "DeepSeek artificial intelligence architecture", # 纯英文技术词
        "Python logo png",                             # 常见 Logo
        "The Great Wall of China",                     # 风景图
    ]

    print("🚀 开始 Phase 1 图像搜索与下载测试...\n")

    for query in test_queries:
        print(f"➡️  正在搜索: [{query}]")
        result_path = searcher.search_and_download(query, test_dir)
        
        if result_path and os.path.exists(result_path):
            file_size_kb = os.path.getsize(result_path) / 1024
            print(f"   ✅ 成功! 文件保存于: {result_path}")
            print(f"   📄 文件大小: {file_size_kb:.2f} KB\n")
        else:
            print(f"   ❌ 失败! 无法获取图片。\n")

if __name__ == "__main__":
    test_workflow()
