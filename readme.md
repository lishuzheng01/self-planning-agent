这是一个基于 **SiliconFlow (硅基流动)** API 和 **DuckDuckGo Search** 的纯 Python 技术实施方案。

**API接口和openAI的接口兼容**

---

# AI 自主规划长文生成系统技术方案 (SiliconFlow + DDGS 版)

## 1. 项目概述

本系统是一个面向工程师内部使用的 **Agentic Workflow（智能体工作流）** 系统。旨在解决长文写作中的“逻辑连贯性”、“事实依据（RAG）”和“素材获取”三大难题。

系统完全基于 Python 开发，提供 **双界面交互**，满足不同场景需求：

1. **CLI（命令行）** - 适合自动化脚本、服务器环境和批量处理场景，通过简洁的命令行参数控制整个工作流
2. **Web UI（Streamlit）** - 提供直观的可视化操作界面，支持文件上传、实时进度查看、历史任务管理和文章预览

它模拟人类编辑团队，利用硅基流动的 DeepSeek/Qwen 等大语言模型进行逻辑规划与写作，并利用 **DuckDuckGo** 搜索引擎进行自动化配图，最终输出格式规范的 Markdown 和排版精美的 Word 文档。

系统具备高度的灵活性和可扩展性，支持自定义配置、多模型切换和任务隔离，确保生成内容的质量和一致性。

---

## 2. 系统核心架构

系统采用 **“RAG 数据层 - 状态机控制层 - 工具执行层”** 三层架构。

### 2.1 技术栈选型

| 模块             | 技术组件                          | 说明                                     |
| :------------- | :---------------------------- | :------------------------------------- |
| **开发语言**       | Python 3.10+                  | 纯后端逻辑                                  |
| **逻辑推理 (LLM)** | **SiliconFlow API**           | 兼容 OpenAI 格式，调度 DeepSeek/Qwen/Yi 模型    |
| **API 客户端**      | `openai`                      | 与 OpenAI 兼容的 API 交互客户端                  |
| **流程编排**       | **LangGraph** (LangChain)     | 管理工作流状态、循环与条件跳转                        |
| **RAG 框架**       | `LangChain` 生态              | 提供文档处理、向量存储和检索能力                      |
| **向量数据库**      | **ChromaDB** (Local)          | 本地存储文档切片，支持语义检索                        |
| **网络搜索 (文本)** | `duckduckgo_search`           | 官方库，无需 API Key，免费且高效                   |
| **网络搜图 (主)**   | `duckduckgo_search`           | 官方库，无需 API Key，免费且高效                   |
| **网络搜图 (备)**   | `requests` + `BeautifulSoup`  | 自建简易爬虫，模拟 User-Agent 抓取 Bing/Google 结果 |
| **HTML 解析**      | `lxml`                        | 高性能 HTML/XML 解析库                        |
| **文档处理**       | `Unstructured`, `python-docx` | 解析输入文件，合成输出文件                          |
| **PDF 处理**       | `pypdf`                       | PDF 文件解析与处理                            |
| **环境配置**       | `python-dotenv`               | 加载环境变量配置                              |
| **CLI 交互**     | `Typer`                       | 封装命令行工具                                |
| **进度显示**       | `tqdm`                        | 命令行进度条显示                              |
| **Web UI**      | `Streamlit`                   | 提供直观的可视化操作界面                           |

---

## 3. 详细功能模块设计

### 3.1 模块一：数据摄取与 RAG (Data Ingestion)

**目标：** 确保 AI 的输出严格围绕提供的资料，通过本地文档增强生成内容的准确性。

1. **文件加载器：**

   * 使用 `DirectoryLoader` 加载指定目录下的所有 `.txt` 文件。
   * 支持动态创建目录并提示用户放入文件。
   * *注：* 当前实现支持 `.txt` 格式，可通过配置扩展支持 PDF 等格式。
2. **语义切片 (Chunking)：**

   * 使用 `RecursiveCharacterTextSplitter` 进行智能文本分割。
   * **Chunk Size:** 800 tokens (适配 Qwen/DeepSeek 的上下文窗口)。
   * **Overlap:** 100 tokens (保证语义连续性和上下文完整性)。
3. **向量化 (Embedding)：**

   * 调用 SiliconFlow 的 Embedding API，使用 `BAAI/bge-m3` 模型将文本向量化。
   * 采用 OpenAI 兼容接口配置，自动加载环境变量中的 API Key。
   * 向量存储使用本地 `ChromaDB`，每个任务拥有独立的向量数据库目录，实现任务隔离。

### 3.2 模块二：基于 SiliconFlow 的模型路由

通过单一的 SiliconFlow API Key，在代码中根据任务需求动态切换模型：

* **Planner (主编):** 使用 **DeepSeek-V3**。

  * *任务:* 理解用户意图，生成标准 JSON 格式的多级大纲，包含章节标题和摘要。
  * *特性:* 具备强大的 JSON 解析和修复能力，确保大纲格式的正确性。
* **Writer (作家):** 使用 **Qwen-2.5-72B-Instruct**。

  * *任务:* 基于 RAG 检索和互联网搜索结果的混合上下文进行长文撰写。
  * *特性:* 优先使用本地资料，结合网络最新信息，确保内容的准确性和时效性。
* **Visualizer (配图策划):** 使用 **Qwen-2.5-72B-Instruct**。

  * *任务:* 分析章节内容，生成 2-3 个搜索引擎友好的关键词，支持宽泛词和精准词组合。
  * *特性:* 智能生成不同维度的搜索关键词，提高图片搜索的准确性。

### 3.3 模块三：自动配图引擎 (Visual Engine)

这是本方案的核心差异点，采用 **多策略搜索 + 质量验证** 机制，确保配图质量和系统稳定性。

#### 高清大图优先策略

1. **策略一：Large + Wide (高清横图)**
   * 优先使用 `duckduckgo_search` 获取 Large 尺寸且 Wide 布局的高清图片
   * 适配长文排版需求，提供最佳阅读体验

2. **策略二：Medium (中等图)**
   * 当策略一失败时，降级为 Medium 尺寸图片
   * 平衡图片质量和下载速度

3. **策略三：备用爬虫**
   * 当 DDGS 库失效或网络超时时，自动切换到备用爬虫（Bing 图片解析）
   * 使用 `requests` 和 `BeautifulSoup` 模拟浏览器访问，提取图片 URL

#### 图片下载与验证管线

```python
def search_and_download(self, keyword: str, save_dir: str) -> str:
    # 高清大图优先策略
    hq_urls = self._fetch_image_urls_ddgs(keyword, size="Large", layout="Wide")
    # 降级为 Medium 尺寸
    if not hq_urls:
        hq_urls = self._fetch_image_urls_ddgs(keyword, size="Medium", layout=None)
    # 启用备用爬虫
    if not hq_urls:
        hq_urls = self._fetch_image_urls_bing_backup(keyword)
    
    # 下载验证流程
    for url in hq_urls:
        filename = f"{int(time.time())}_{random.randint(1000,9999)}.jpg"
        save_path = os.path.join(save_dir, filename)
        if self._download_image(url, save_path, min_size_kb=50):
            return save_path
    return None
```

1. **下载：** 遍历搜索结果 URL，使用 `requests.get` 下载（设置超时机制）
2. **验证：** 
   * 检查文件 Magic Number 确保图片格式真实
   * 验证文件大小 (>50KB) 确保清晰度
   * 自动过滤 WebP 格式（Word 兼容性差）
3. **存储：** 保存至任务专属目录，使用唯一文件名避免冲突

### 3.4 模块四：Agentic Workflow (智能体工作流)

使用 **LangGraph** 定义状态机，实现智能体之间的协作：

1. **State 初始化:** 输入 Topic, Files, Output_Dir。
2. **Node 1: Plan:** 使用 DeepSeek-V3 生成 JSON 格式大纲，包含章节标题和摘要。
3. **Node 2: Loop (循环处理每一章):**

   * **Retrieve:** 从 ChromaDB 检索 Top-5 相关资料，为章节撰写提供依据。
   * **Draft:** 使用 Qwen-2.5-72B-Instruct 基于混合上下文（RAG检索 + 网络搜索）生成章节文本。
   * **Keyword Gen:** 生成 2-3 个搜索引擎友好的关键词，支持宽泛词和精准词组合。
   * **Search & Download:** 调用多策略搜索引擎 -> 下载验证图片 -> 自动插入 Markdown 内容。
4. **Node 3: Assemble:** 将所有章节内容和图片合并为完整的 Markdown 文件。
5. **Node 4: Export:** 转换为 Markdown 和 Word 格式并保存到指定目录。

### 3.5 模块五：双格式输出 (Markdown & Word)

1. **Markdown:** 简单的文本拼接，保留图片相对路径。
2. **Word (.docx):**

   * 使用 `python-docx`。
   * **核心难点解决：** 图片排版。

     * 程序会自动读取 Markdown 中的图片路径。
     * 获取 Word 文档的 `page_width` (页面宽度)。
     * `doc.add_picture(path, width=Inches(6))` —— 自动将图片宽度锁定为页面宽度（减去页边距），高度自适应，防止图片溢出。

---

## 4. 项目结构

本项目采用模块化架构设计，代码组织清晰，便于维护和扩展。主要目录和文件结构如下：

```
self-planning-agent/
├── main.py              # CLI 主入口文件
├── app.py               # Streamlit Web UI 入口文件
├── .env                 # 环境变量配置文件
├── config.yaml          # 系统配置文件
├── requirements.txt     # Python 依赖包列表
├── readme.md            # 项目说明文档
├── src/                 # 核心源代码目录
│   ├── __init__.py
│   ├── writer_agent.py  # 智能写作代理（核心逻辑）
│   ├── rag_engine.py    # RAG 检索引擎
│   ├── search_engine.py # 图片搜索引擎
│   ├── llm_client.py    # LLM API 客户端
│   └── doc_gen.py       # 文档生成工具
├── data/                # 输入数据目录
│   ├── uploads/         # Web UI 上传文件存储
│   └── *.txt            # 示例输入文件
├── output/              # 输出结果目录
│   ├── YYYYMMDD_HHmmss_主题名/  # 按任务时间和主题命名
│   │   ├── assets/      # 图片资源目录
│   │   ├── final_article.md   # 生成的 Markdown 文件
│   │   └── final_article.docx # 生成的 Word 文件
│   └── chroma_db/       # ChromaDB 向量存储
└── test/                # 测试文件目录
    └── test.py          # 单元测试
```

**关键目录说明：**

* **src/**: 包含所有核心业务逻辑模块，实现了智能写作、RAG检索、图片搜索等功能
* **data/**: 用于存放用户提供的输入资料，支持TXT格式
* **output/**: 存储生成的文章和图片资源，按任务时间和主题自动分类
* **test/**: 包含测试用例，用于验证系统功能的正确性

---

## 5. 安装与快速开始

### 5.1 环境要求

* Python 3.10+
* SiliconFlow API Key（用于 LLM 和 Embedding）
* 稳定的网络连接（用于访问 SiliconFlow API 和搜索图片）

### 5.2 安装步骤

1. **克隆项目**

   ```bash
   git clone <项目仓库地址>
   cd self-planning-agent
   ```

2. **创建虚拟环境**

   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**

   创建 `.env` 文件并添加以下内容：

   ```env
   # SiliconFlow API 配置
   SILICONFLOW_API_KEY=your_siliconflow_api_key_here
   
   # OpenAI 兼容接口配置
   OPENAI_API_BASE=https://api.siliconflow.cn/v1
   OPENAI_API_KEY=your_siliconflow_api_key_here
   ```

### 5.3 快速开始

本项目提供两种使用方式：CLI（命令行）和 Web UI（Streamlit）。

#### 5.3.1 CLI 方式

```bash
# 基本用法
python main.py run --topic "你的文章主题" --files ./data --out ./output

# 示例
python main.py run --topic "深度解析 Space X 星舰计划" --files ./data --out ./output
```

**参数说明：**
* `--topic` 或 `-t`: 文章主题（必填）
* `--files` 或 `-f`: 资料文件目录（默认：./data）
* `--out` 或 `-o`: 输出结果目录（默认：./output）

#### 5.3.2 Web UI 方式

```bash
# 启动 Streamlit Web 服务
streamlit run app.py
```

然后在浏览器中访问 `http://localhost:8501` 即可使用 Web UI 界面。

### 5.4 使用说明

1. **准备资料**：将需要参考的 `.txt` 文件放入 `./data` 目录
2. **启动服务**：选择 CLI 或 Web UI 方式启动服务
3. **输入主题**：输入想要撰写的文章主题
4. **等待生成**：系统会自动生成大纲、撰写内容、匹配图片
5. **查看结果**：在输出目录中查看生成的 Markdown 和 Word 文件

---

## 6. 项目实施与完成情况

本项目已完全按照计划实施完成，所有功能模块均已开发并通过测试。以下是各阶段的完成情况：

### Phase 1: 基础设施搭建 ✅ 已完成

* **完成内容：**
  * 搭建了 Python 3.10+ 开发环境
  * 封装了 `LLMClient` 类，成功适配 SiliconFlow API
  * 实现了 `ImageSearcher` 类，集成 DDGS 主搜索引擎和备用爬虫

### Phase 2: RAG 与 规划器开发 ✅ 已完成

* **完成内容：**
  * 实现了文件解析与 ChromaDB 向量存储功能
  * 调试并优化了 Planner Prompt，确保大纲生成的逻辑清晰和字数分配合理
  * 实现了基于 BAAI/bge-m3 模型的文本向量化功能

### Phase 3: 写作与搜图串联 ✅ 已完成

* **完成内容：**
  * 使用 LangGraph 构建了完整的智能体工作流
  * 优化了 LLM 提取搜索关键词的能力，支持宽泛词和精准词组合
  * 实现了完善的图片下载错误处理机制

### Phase 4: 格式化与双界面封装 ✅ 已完成

* **完成内容：**
  * 开发了 Markdown 转 Docx 引擎，支持图片自动排版
  * 使用 Typer 封装了 CLI 入口：`python main.py run --topic "..." --files "./data"`
  * 开发了 Streamlit Web UI，提供可视化操作界面

### Phase 5: Web UI 开发 ✅ 已完成

* **完成内容：**
  * 实现了聊天式交互界面
  * 开发了文件上传和历史任务管理功能
  * 支持实时进度显示和文章预览

所有功能均已通过测试，系统运行稳定，满足设计要求。

---

## 7. Web UI (Streamlit) 功能介绍

### 7.1 界面概览

Streamlit Web UI 提供了直观、友好的可视化操作界面，主要包含以下核心组件：

- **聊天式交互界面**：采用对话式设计，用户可以直接输入文章主题
- **文件上传区**：支持批量上传 RAG 资料文件，自动保存到指定目录
- **任务管理面板**：侧边栏展示历史任务，支持查看和预览旧文章
- **实时进度显示**：动态展示文章生成的各个阶段（学习资料、规划大纲、撰写与配图、生成 Word）

### 7.2 核心功能

#### 7.2.1 任务创建

1. **主题输入**：在聊天框中输入文章主题
2. **资料上传**：（可选）上传相关的参考资料文件
3. **启动任务**：系统自动创建任务目录并开始生成过程

#### 7.2.2 实时进度跟踪

- 清晰的步骤标识：学习资料 → 规划大纲 → 撰写与配图 → 生成 Word
- 实时显示当前处理的章节标题
- 自动处理异常情况并给出友好提示

#### 7.2.3 历史任务管理

- 侧边栏列出所有历史任务
- 支持按时间倒序排列
- 点击任务可查看详细内容

#### 7.2.4 文章预览

- 支持在线阅读生成的文章
- 自动识别并加载文章中的图片
- 提供图片缺失时的友好提示

### 7.3 使用方法

1. 启动 Streamlit 应用：`streamlit run app.py`
2. 在浏览器中访问提示的地址（默认为 `http://localhost:8501`）
3. （可选）上传参考资料文件
4. 在聊天框中输入文章主题并回车
5. 等待系统完成文章生成
6. 点击生成的文章链接查看或下载

## 8. 风险评估与应对

| 风险点               | 应对方案                                                                             |
| :---------------- | :------------------------------------------------------------------------------- |
| **DDGS 接口限流/失效**  | 1. 增加随机 User-Agent 请求头。<br>2. 自动切换至备用爬虫（Bing HTML 解析）。<br>3. 错误时降级为“仅生成文本，图片留空”。 |
| **图片下载防盗链 (403)** | request header 中加入 `Referer` 和常见的浏览器 UA。下载失败自动尝试搜索结果中的下一张图片。                     |
| **长文逻辑割裂**        | 在 Prompt 中引入“全局摘要”和“上一章末尾段落”作为 Context，保持文风连贯。                                   |
| **Word 图片排版混乱**   | 强制使用 `python-docx` 的 `width` 参数锁定图片宽度，不使用原始尺寸。                                   |
| **Web UI 资源占用过高**  | 任务隔离设计，每个任务使用独立的向量数据库和资源，避免相互干扰。                               |

## 9. 最终交付文件清单

本项目提供完整的源代码和配置文件，以下是最终交付文件清单：

### 1. 核心源代码

| 文件/目录 | 功能说明 |
| :-------- | :------ |
| `main.py` | CLI 主入口文件，使用 Typer 封装 |
| `app.py` | Streamlit Web UI 入口文件 |
| `src/` | 核心功能模块目录 |
| `src/writer_agent.py` | 智能写作代理（核心逻辑） |
| `src/rag_engine.py` | RAG 检索引擎 |
| `src/search_engine.py` | 图片搜索引擎 |
| `src/llm_client.py` | LLM API 客户端 |
| `src/doc_gen.py` | 文档生成工具 |
| `test/` | 测试文件目录 |

### 2. 配置文件

| 文件 | 功能说明 |
| :--- | :------ |
| `.env` | 环境变量配置文件（包含 SiliconFlow API Key） |
| `config.yaml` | 系统配置文件 |
| `requirements.txt` | Python 依赖包列表 |

### 3. 输出产物

系统会自动生成以下输出文件：

```
output/YYYYMMDD_HHmmss_主题名/
├── final_article.md     # 生成的 Markdown 文件
├── final_article.docx   # 生成的 Word 文件（含自动排版的图片）
└── assets/              # 图片资源目录
    └── *.jpg            # 下载的配图文件
```

### 4. 文档

| 文件 | 功能说明 |
| :--- | :------ |
| `readme.md` | 项目说明文档（包含安装、使用和架构说明） |

## 10. 总结

本项目实现了一个完整的 AI 自主规划长文本生成系统，具备以下核心优势：

1. **双界面交互**：同时支持 CLI 和 Streamlit Web UI，满足不同使用场景需求
2. **高质量内容生成**：基于 RAG 检索和互联网搜索的混合上下文，确保内容准确性和时效性
3. **智能配图功能**：多策略搜索引擎和质量验证机制，确保配图质量
4. **灵活的架构设计**：模块化设计，便于维护和扩展
5. **完善的错误处理**：具备多重错误处理机制，确保系统稳定性

该系统完全满足**纯 Python 实现**、**使用 SiliconFlow API** 以及 **自动配图** 的所有需求，可直接部署使用。
