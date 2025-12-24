# test_phase3.py

import os
from src.writer_agent import WriterAgent

def test_phase3():
    print("🚀 Phase 3 测试：全自动写作 Agent")
    print("=" * 50)
    
    # 1. 准备工作
    topic = "埃隆·马斯克与火星移民计划"
    
    # 确保 data 目录里有相关的背景资料（可选，如果没有 RAG 会用通用知识）
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    with open(f"{data_dir}/mars_context.txt", "w", encoding="utf-8") as f:
        f.write("""
        SpaceX 的星舰 (Starship) 是人类历史上最大的火箭。
        马斯克计划在 2050 年前将 100 万人送上火星。
        火星移民面临的主要挑战是辐射、重力和自给自足的生态系统。
        """)
    
    # 2. 初始化 Agent
    # 注意：初始化时会自动加载 RAG 引擎，可能需要几秒
    agent = WriterAgent()
    
    # 3. 重新构建知识库 (为了让刚刚写入的关于马斯克的数据生效)
    print("\n[1/2] 正在学习资料...")
    agent.rag.ingest_data(data_dir)
    
    # 4. 执行生成
    print(f"\n[2/2] 开始生成文章：{topic}...")
    final_markdown = agent.generate_full_article(topic)
    
    # 5. 保存结果
    output_path = "./output/phase3_result.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_markdown)
        
    print("\n" + "="*50)
    print(f"✅ 任务完成！结果已保存至: {output_path}")
    print("请打开该 Markdown 文件，检查文章逻辑和配图是否成功。")

if __name__ == "__main__":
    test_phase3()
