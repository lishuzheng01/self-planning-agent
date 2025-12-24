# test_phase2.py
import os
from src.llm_client import LLMClient
from src.rag_engine import RAGEngine

def test_phase2():
    print("="*60)
    print("🚀 Phase 2 测试：全云端 SiliconFlow 集成")
    print("="*60)

    # --- 1. 测试 LLM 对话 ---
    print("\n[1/3] 测试 DeepSeek/Qwen 聊天接口...")
    llm = LLMClient()
    try:
        # 使用 Qwen-7B 或 DeepSeek-V3 进行快速测试
        answer = llm.call_llm("请回复：'API 连接成功'", "Qwen/Qwen2.5-72B-Instruct")
        print(f"🤖 模型回复: {answer}")
    except Exception as e:
        print(f"❌ LLM 测试失败: {e}")
        return

    # --- 2. 准备测试数据 ---
    print("\n[2/3] 准备 RAG 测试数据...")
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    with open(f"{data_dir}/test_rag.txt", "w", encoding="utf-8") as f:
        f.write("Project Omega 是一个绝密计划。它的核心目标是利用 AI 实现全自动代码生成。启动日期是2025年。")
    print(f"   已写入测试文件: {data_dir}/test_rag.txt")

    # --- 3. 测试 RAG 流程 (Embedding API) ---
    print("\n[3/3] 测试 RAG 向量化与检索...")
    rag = RAGEngine()
    
    # 构建库 (会调用 Embedding API)
    rag.ingest_data(data_dir)
    
    # 检索
    query = "Project Omega 的目标是什么？"
    print(f"❓ 提问: {query}")
    results = rag.query_knowledge_base(query, top_k=1)
    
    if results:
        print(f"📄 检索到的上下文: {results[0]}")
    else:
        print("❌ 未检索到任何内容。")

if __name__ == "__main__":
    test_phase2()
