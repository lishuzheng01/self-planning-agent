# src/llm_client.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 环境变量
load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 未找到 SILICONFLOW_API_KEY，请检查 .env 文件")
        
        # 初始化 OpenAI 客户端，指向硅基流动的地址
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.siliconflow.cn/v1"
        )

    def call_llm(self, prompt: str, model_name: str, json_mode: bool = False) -> str:
        """
        调用 LLM 生成文本
        :param model_name: 例如 "deepseek-ai/DeepSeek-V3" 或 "Qwen/Qwen2.5-72B-Instruct"
        """
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                # 如果需要 JSON 格式输出 (用于 Planner)，开启此选项
                response_format={"type": "json_object"} if json_mode else {"type": "text"},
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM 调用异常: {e}")
            return ""
