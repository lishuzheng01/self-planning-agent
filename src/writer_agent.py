# src/writer_agent.py

import os
import json
import re
import logging
from typing import List, Dict, Any

from src.llm_client import LLMClient
from src.rag_engine import RAGEngine
from src.search_engine import ImageSearcher

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class WriterAgent:
    def __init__(self, output_dir="./output"):
        self.llm = LLMClient()
        self.output_dir = output_dir
        self.assets_dir = os.path.join(self.output_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)

        # 任务隔离：确保 RAG 纯净
        task_db_path = os.path.join(self.output_dir, "chroma_db")
        self.rag = RAGEngine(vector_db_path=task_db_path)
        
        self.searcher = ImageSearcher()
        
        # 模型配置
        self.model_planner = "deepseek-ai/DeepSeek-V3"
        self.model_writer = "Qwen/Qwen2.5-72B-Instruct" 
        self.model_visualizer = "Qwen/Qwen2.5-72B-Instruct"

    def plan_outline(self, topic: str) -> List[Dict]:
        """Step 1: 生成大纲 (增强版 JSON 修复)"""
        prompt = f"""
        你是一名专业的技术主编。请根据主题 "{topic}" 规划一篇文章的大纲。
        
        🔴 **严格格式要求**：
        1. 必须返回一个标准的 **JSON 数组** (Array of Objects)。
        2. **禁止**返回字典或带索引的对象（如 {{"0": {{...}}}}）。
        3. 不要包含 Markdown 标记。
        
        正确格式示例：
        [
            {{"title": "第一章标题", "description": "摘要..."}},
            {{"title": "第二章标题", "description": "摘要..."}}
        ]
        """
        response = self.llm.call_llm(prompt, self.model_planner, json_mode=True)
        
        try:
            # 1. 基础清洗
            clean_json = response.replace("```json", "").replace("```", "").strip()
            
            # 2. 尝试直接解析
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError:
                # 如果解析失败，尝试修复常见错误（如键名未加引号）
                # 这里使用一个简单的正则提取策略作为兜底
                # 提取所有 {"title": ..., "description": ...} 结构
                pattern = r'\{\s*"title":\s*".*?",\s*"description":\s*".*?"\s*\}'
                matches = re.findall(pattern, clean_json, re.DOTALL)
                if matches:
                    data = [json.loads(m) for m in matches]
                else:
                    return []

            # 3. 【核心修复】结构标准化 (Dict 转 List)
            # 解决 0: {...}, 1: {...} 这种字典格式
            outline = []
            if isinstance(data, list):
                outline = data
            elif isinstance(data, dict):
                # 如果是字典，可能是 {"outline": [...]} 或 {"0": {...}, "1": {...}}
                # 策略：优先找 list 类型的 value，找不到则取所有 dict 类型的 value
                
                # 情况 A: {"chapters": [ ... ]}
                for key, val in data.items():
                    if isinstance(val, list):
                        outline = val
                        break
                
                # 情况 B: {"0": {...}, "1": {...}}
                if not outline:
                    # 按 key 排序后取 value
                    sorted_keys = sorted(data.keys(), key=lambda x: int(str(x)) if str(x).isdigit() else x)
                    for k in sorted_keys:
                        if isinstance(data[k], dict):
                            outline.append(data[k])
            
            return outline
            
        except Exception as e:
            logger.error(f"大纲解析严重错误: {e}")
            return []

    def write_single_section(self, topic: str, section: Dict, index: int) -> Dict[str, Any]:
        """
        Step 2: 撰写单章 (先生成搜索词 -> 再搜索 -> 再写作)
        """
        title = section.get('title', f'Section {index}')
        desc = section.get('description', '')
        
        # --- 1. 智能生成搜索关键词 (避免搜不到内容) ---
        # 以前是 f"{topic} {title}"，现在让 LLM 变通一下
        search_queries = self._generate_search_queries(topic, title, desc)
        
        # --- 2. 混合检索 ---
        
        # A. 本地 RAG
        rag_query = f"{topic} {title} {desc}"
        rag_results = self.rag.query_knowledge_base(rag_query, top_k=2)
        
        # B. 互联网搜索 (多词尝试)
        web_results = []
        seen_urls = set()
        
        # 对生成的每个搜索词都试一下
        for query in search_queries:
            results = self.searcher.search_text(query, max_results=2)
            for r in results:
                if r['href'] not in seen_urls:
                    web_results.append(r)
                    seen_urls.add(r['href'])
        
        # 限制数量，防止上下文溢出
        web_results = web_results[:4]
        
        # --- 3. 构造上下文 ---
        context_parts = []
        
        if rag_results:
            context_parts.append("【本地文件资料 (Priority High)】：")
            for idx, txt in enumerate(rag_results):
                context_parts.append(f"[Local-{idx+1}] {txt[:400]}...")

        if web_results:
            context_parts.append("【互联网最新资讯 (Priority Medium)】：")
            for w in web_results:
                context_parts.append(f"来源: [{w['title']}]({w['href']})\n内容摘要: {w['body']}")
        
        if not context_parts:
            context_parts.append("（暂无直接参考资料，请基于您的专业知识撰写。）")
            
        full_context_str = "\n\n".join(context_parts)
        
        # --- 4. 写作 ---
        content = self._generate_text_with_citation(topic, title, desc, full_context_str)
        
        # --- 5. 配图 ---
        img_md, img_path, keyword = self._auto_append_image(content)
        
        full_md = f"## {title}\n\n{content}\n\n{img_md}\n\n---\n\n"

        return {
            "title": title,
            "markdown": full_md,
            "pure_text": content,
            "rag_context": rag_results, 
            "web_context": web_results,
            "search_queries": search_queries, # 返回搜索词供 UI 展示
            "search_keyword": keyword, 
            "image_path": img_path
        }

    def _generate_search_queries(self, topic, title, desc) -> List[str]:
        """让 LLM 将章节意图转化为 2-3 个搜索引擎友好的关键词"""
        prompt = f"""
        请将章节内容转化为 2 个互联网搜索查询词。
        主题：{topic}
        章节：{title} ({desc})
        
        要求：
        1. 一个宽泛词 (例如: "{topic} latest news")
        2. 一个精准词 (例如: "{title} data analysis")
        3. 直接返回关键词，用逗号分隔，不要解释。
        """
        response = self.llm.call_llm(prompt, self.model_planner)
        # 清洗
        queries = [q.strip() for q in response.split(',') if q.strip()]
        # 兜底
        if not queries:
            queries = [f"{topic} {title}"]
        return queries[:2]

    def _generate_text_with_citation(self, topic, title, desc, context) -> str:
        prompt = f"""
        你是一名严谨的技术作家。请根据【参考资料】撰写文章章节。
        【文章主题】：{topic}
        【本章标题】：{title}
        【本章摘要】：{desc}
        【参考资料】：
        {context}
        
        🔴 **关键要求**：
        1. **基于事实**：内容必须优先基于提供的【参考资料】。
        2. **禁止无关引用**：绝对不要引用与本章无关的链接。
        3. **标注引用**：当你引用【互联网最新资讯】中的数据或观点时，必须在句末加上 Markdown 链接引用。
           - 格式：`...观点描述 [来源标题](URL)`
        4. **深度与逻辑**：综合分析，不要罗列。
        5. **字数**：400-600字。
        """
        return self.llm.call_llm(prompt, self.model_writer)

    def _auto_append_image(self, text_content: str):
        prompt = f"""
        阅读以下文本，提取一个最适合做插图的“英文搜索关键词”。
        文本：{text_content[:300]}...
        要求：只返回关键词，不要解释。必须是英文。
        """
        keyword = self.llm.call_llm(prompt, self.model_visualizer).strip()
        keyword = re.sub(r'[^a-zA-Z0-9\s]', '', keyword)
        
        if not keyword:
            return "", None, ""
            
        image_path = self.searcher.search_and_download(keyword, self.assets_dir)
        
        if image_path:
            rel_path = os.path.relpath(image_path, self.output_dir).replace("\\", "/")
            return f"![图：{keyword}]({rel_path})", image_path, keyword
        else:
            return f"> *(配图失败: {keyword})*", None, keyword
