# main.py

import os
import typer
from tqdm import tqdm
from src.writer_agent import WriterAgent
from src.doc_gen import DocumentGenerator

app = typer.Typer(add_completion=False)

@app.command()
def run(
    topic: str = typer.Option(..., "--topic", "-t"),
    files_dir: str = typer.Option("./data", "--files", "-f"),
    output_dir: str = typer.Option("./output", "--out", "-o"),
):
    print(f"\n🚀 启动任务: {topic}")
    os.makedirs(output_dir, exist_ok=True)
    agent = WriterAgent(output_dir=output_dir)
    
    if os.path.exists(files_dir) and os.listdir(files_dir):
        print(f"\n📚 [Step 1] 学习资料...")
        agent.rag.ingest_data(files_dir)

    print(f"\n🧠 [Step 2] 规划大纲...")
    outline = agent.plan_outline(topic)
    
    print(f"\n✍️ [Step 3] 撰写与配图...")
    full_content = f"# {topic}\n\n"
    
    with tqdm(total=len(outline)) as pbar:
        for i, section in enumerate(outline):
            pbar.set_description(f"Writing: {section['title'][:10]}")
            # 适配修改：这里返回的是 dict
            result = agent.write_single_section(topic, section, i+1)
            full_content += result["markdown"] # 只取 markdown 部分拼接
            pbar.update(1)

    # 保存与生成 Word (保持不变)
    md_path = os.path.join(output_dir, "final_article.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    print(f"\n📄 [Step 4] 生成 Word...")
    gen = DocumentGenerator()
    gen.convert_markdown_to_docx(full_content, os.path.join(output_dir, "final_article.docx"))
    print(f"✅ 完成: {output_dir}")

if __name__ == "__main__":
    app()
