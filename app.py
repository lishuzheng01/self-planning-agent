# app.py

import streamlit as st
import os
import re
from datetime import datetime
from glob import glob

from src.writer_agent import WriterAgent
from src.doc_gen import DocumentGenerator

st.set_page_config(page_title="AI 深度写作系统", page_icon="📝", layout="wide")

BASE_OUTPUT_DIR = "./output"
BASE_DATA_DIR = "./data/uploads"

def render_article_preview(markdown_text, image_base_dir):
    parts = re.split(r'(\!\[.*?\]\(.*?\))', markdown_text)
    for part in parts:
        img_match = re.match(r'\!\[(.*?)\]\((.*?)\)', part)
        if img_match:
            alt_text = img_match.group(1)
            raw_path = img_match.group(2)
            possible_paths = [
                raw_path,
                os.path.join(image_base_dir, raw_path),
                os.path.join(image_base_dir, "assets", os.path.basename(raw_path))
            ]
            found_img = None
            for p in possible_paths:
                p = p.replace("/", os.sep).replace("\\", os.sep)
                if os.path.exists(p):
                    found_img = p
                    break
            if found_img:
                st.image(found_img, caption=alt_text)
            else:
                st.warning(f"⚠️ 图片丢失: {raw_path}")
        else:
            if part.strip():
                st.markdown(part)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "你好！我是主编。请输入主题，我将先检索全网信息，再为您写作。"}]
if "processing" not in st.session_state:
    st.session_state.processing = False

with st.sidebar:
    st.title("🎛️ 控制台")
    uploaded_files = st.file_uploader("📂 上传 RAG 资料", accept_multiple_files=True)
    current_data_dir = None
    if uploaded_files:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_data_dir = os.path.join(BASE_DATA_DIR, session_id)
        os.makedirs(current_data_dir, exist_ok=True)
        for f in uploaded_files:
            with open(os.path.join(current_data_dir, f.name), "wb") as w:
                w.write(f.getbuffer())
        st.success(f"✅ 已挂载 {len(uploaded_files)} 份资料")
    st.divider()
    if os.path.exists(BASE_OUTPUT_DIR):
        tasks = sorted([d for d in os.listdir(BASE_OUTPUT_DIR) if os.path.isdir(os.path.join(BASE_OUTPUT_DIR, d))], reverse=True)
        selected_task = st.selectbox("查看旧文", ["-- 选择任务 --"] + tasks)
        if selected_task and selected_task != "-- 选择任务 --":
            task_path = os.path.join(BASE_OUTPUT_DIR, selected_task)
            md_files = glob(os.path.join(task_path, "*.md"))
            if md_files:
                with open(md_files[0], "r", encoding="utf-8") as f:
                    content = f.read()
                if st.button("📖 在线阅读"):
                    render_article_preview(content, task_path)

st.title("📝 Agentic Writer Pro")
st.caption("Mixed Retrieval | Auto-Correction | Source Citation")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("输入文章主题...", disabled=st.session_state.processing):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.processing = True
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join([c for c in prompt if c.isalnum()])[:15]
    task_dir = os.path.join(BASE_OUTPUT_DIR, f"{timestamp}_{safe_topic}")
    os.makedirs(task_dir, exist_ok=True)

    with st.chat_message("assistant"):
        st.markdown(f"收到主题 **“{prompt}”**，工作流启动...")
        
        with st.status("🚀 运行中...", expanded=True) as status:
            agent = WriterAgent(output_dir=task_dir)
            
            # Step 1
            if current_data_dir:
                status.write(f"📚 正在向量化 {len(uploaded_files)} 份文档...")
                agent.rag.ingest_data(current_data_dir)
            
            # Step 2
            status.write("🧠 正在规划大纲 ...")
            outline = agent.plan_outline(prompt)
            
            if not outline:
                status.update(label="❌ 大纲生成失败", state="error")
                st.error("无法生成有效大纲，请重试。")
                st.session_state.processing = False
                st.stop()
            
            st.json(outline, expanded=False)
            
            # Step 3
            full_content = f"# {prompt}\n\n"
            prog_bar = st.progress(0)
            
            for i, section in enumerate(outline):
                status.write(f"✍️ 正在撰写: **{section['title']}**")
                result = agent.write_single_section(prompt, section, i+1)
                
                with st.expander(f"👁️ 第 {i+1} 章执行细节", expanded=True):
                    # 显示使用了哪些搜索词
                    st.caption(f"🔍 构造的搜索词: {', '.join(result.get('search_queries', []))}")
                    
                    if result.get('web_context'):
                        st.markdown("#### 🌐 互联网检索结果")
                        for w in result['web_context']:
                            st.markdown(f"- [{w['title']}]({w['href']})")
                    else:
                        st.info("🌐 未检索到高相关性的互联网内容，将基于通用知识生成。")
                        
                    if result.get('rag_context'):
                        st.markdown("#### 📂 本地 RAG 引用")
                        for ctx in result['rag_context']:
                            st.caption(f"- {ctx[:100]}...")
                            
                    st.divider()
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if result['image_path']:
                            st.image(result['image_path'])
                    with col2:
                        if result['image_path']:
                            st.success(f"配图成功: {result['search_keyword']}")
                        else:
                            st.warning("配图失败")

                full_content += result['markdown']
                prog_bar.progress((i + 1) / len(outline))
            
            # Step 4
            status.write("📄 生成文档...")
            md_path = os.path.join(task_dir, "final_article.md")
            docx_path = os.path.join(task_dir, "final_article.docx")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            DocumentGenerator().convert_markdown_to_docx(full_content, docx_path)
            status.update(label="✅ 完成！", state="complete")

        st.divider()
        tab1, tab2 = st.tabs(["📖 阅读", "💾 下载"])
        with tab1:
            render_article_preview(full_content, task_dir)
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                with open(docx_path, "rb") as f:
                    st.download_button("下载 Word", f, file_name=f"{safe_topic}.docx")
            with col2:
                with open(md_path, "rb") as f:
                    st.download_button("下载 Markdown", f, file_name=f"{safe_topic}.md")
        
        st.session_state.processing = False
        st.session_state.messages.append({"role": "assistant", "content": "任务完成！"})
