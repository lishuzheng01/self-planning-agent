# test_phase4.py

import os
from src.doc_gen import DocumentGenerator

def test_phase4():
    print("🚀 Phase 4 测试：Markdown 转 Word")
    print("=" * 50)

    # 1. 寻找输入文件 (优先使用 Phase 3 生成的结果)
    input_md = "./output/phase3_result.md"
    
    if not os.path.exists(input_md):
        print(f"⚠️ 找不到 {input_md}，将使用内置测试文本。")
        # 创建一个临时的测试 Markdown
        os.makedirs("./output/assets", exist_ok=True)
        input_md = "./output/test_manual.md"
        with open(input_md, "w", encoding="utf-8") as f:
            f.write("# Hello World\n这是测试文档。\n\n## 章节一\n内容...")

    # 2. 读取 Markdown
    with open(input_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 3. 执行转换
    output_docx = input_md.replace(".md", ".docx")
    print(f"📄 正在转换: {input_md} -> {output_docx}")
    
    generator = DocumentGenerator()
    try:
        generator.convert_markdown_to_docx(md_content, output_docx)
        print("\n✅ 转换成功！")
        print(f"请打开文件查看效果: {os.path.abspath(output_docx)}")
    except Exception as e:
        print(f"\n❌ 转换失败: {e}")

if __name__ == "__main__":
    test_phase4()
