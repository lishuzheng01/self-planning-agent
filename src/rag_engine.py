# src/rag_engine.py
import os
import shutil
from typing import List
from dotenv import load_dotenv

# LangChain 组件
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings 

load_dotenv()

class RAGEngine:
    def __init__(self, vector_db_path="./output/chroma_db"):
        self.vector_db_path = vector_db_path
        self.vector_store = None
        
        api_key = os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            raise ValueError("❌ 未找到 SILICONFLOW_API_KEY")

        print("⚙️ 初始化 RAG 引擎 (Cloud Embedding)...")
        
        # 配置 Embedding API
        # SiliconFlow 兼容 OpenAI 接口规范
        self.embedding_model = OpenAIEmbeddings(
            model="BAAI/bge-m3",                # 指定硅基流动支持的 Embedding 模型
            openai_api_key=api_key,
            openai_api_base="https://api.siliconflow.cn/v1",
            check_embedding_ctx_length=False    # 关闭本地 Token 检查
        )

    def ingest_data(self, data_dir: str):
        """
        读取 ./data 目录 -> 切片 -> API 向量化 -> 存入 ChromaDB
        """
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"⚠️ 目录 {data_dir} 不存在，已自动创建。请放入 txt/pdf 文件。")
            return

        print(f"📂 扫描文档目录: {data_dir}")
        
        # 1. 加载所有 txt 文件 (根据需要可加 "*.pdf")
        loader = DirectoryLoader(data_dir, glob="**/*.txt", show_progress=True)
        try:
            docs = loader.load()
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return

        if not docs:
            print("⚠️ 目录下没有找到文档。")
            return

        print(f"   -> 找到 {len(docs)} 个文件")

        # 2. 文本切片 (Chunking)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100
        )
        splits = text_splitter.split_documents(docs)
        print(f"   -> 切分为 {len(splits)} 个文本块")

        # 3. 向量化并存储 (这一步会消耗 API Token)
        print("   -> 正在调用 API 生成向量 (请稍候)...")
        
        # 清理旧数据 (可选)
        if os.path.exists(self.vector_db_path):
            try:
                shutil.rmtree(self.vector_db_path)
            except:
                pass 

        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embedding_model,
            persist_directory=self.vector_db_path
        )
        print(f"✅ 知识库构建完成！")

    def query_knowledge_base(self, query: str, top_k: int = 5) -> List[str]:
        """
        根据问题检索相关资料
        """
        if not self.vector_store:
            if os.path.exists(self.vector_db_path):
                self.vector_store = Chroma(
                    persist_directory=self.vector_db_path, 
                    embedding_function=self.embedding_model
                )
            else:
                return []

        # 检索时也会自动调用 API 将 query 向量化
        results = self.vector_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]
