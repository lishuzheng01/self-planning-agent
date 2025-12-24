# 测试duckduckgo_search库

from duckduckgo_search import DDGS
with DDGS() as ddgs:
    images = [r for r in ddgs.images("cat", region="wt-wt", max_results=5)]
print(images)  # 返回含image(原图链接)、thumbnail(缩略图)等字段的字典列表