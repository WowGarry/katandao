import os
from openai import OpenAI

class LLMService:
    def __init__(self, api_key=None, model="deepseek-chat"):
        """
        简化版 LLM 服务，只支持 DeepSeek
        
        Args:
            api_key: DeepSeek API 密钥，如果为None则从环境变量读取
            model: 使用的模型名称，默认为 deepseek-chat
        """
        if api_key is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("未提供DeepSeek API密钥且环境变量DEEPSEEK_API_KEY未设置")
        
        # 初始化 DeepSeek 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = model
        self.cache = {}
    
    def ask(self, prompt, max_tokens=100):
        """向 DeepSeek 提问

        临时禁用缓存以便调试。
        """

        # 临时禁用缓存进行调试
        # cache_key = f"{prompt}_{max_tokens}"
        # if cache_key in self.cache:
        #     print("[LLMService] 使用缓存响应")
        #     return self.cache[cache_key]

        try:
            print(f"[LLMService] 开始API调用，提示词长度: {len(prompt)}")

            # 系统提示词，要求简短准确
            system_prompt = "请用中文简短回答，避免不必要的解释。"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                stream=False,
            )

            result = response.choices[0].message.content.strip()
            print(f"[LLMService] API调用成功")

            # 临时禁用缓存
            # self.cache[cache_key] = result
            return result

        except Exception as e:
            error_msg = f"DeepSeek API 请求失败: {e}"
            print(f"[LLMService] {error_msg}")
            import traceback
            print(f"[LLMService] API错误详情: {traceback.format_exc()}")
            return error_msg
    
    def generate_trade_dialogue(self, offer, request):
        """
        生成交易对话
        
        Args:
            offer: 提供的物品字典
            request: 请求的物品字典
            
        Returns:
            生成的交易对话文本
        """
        prompt = f"""
        基于以下交易信息生成一段约30字的交易对话：
        提供：{offer}
        请求：{request}
        
        请生成买卖双方自然的讨价还价对话，控制在30字左右，用中文。
        """
        
        return self.ask(prompt, max_tokens=80)


# 单例模式实现
_llm_service = None

def get_llm_service(api_key=None, model="deepseek-chat"):
    """
    获取LLMService单例实例
    
    Args:
        api_key: DeepSeek API密钥
        model: 模型名称
        
    Returns:
        LLMService实例
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(api_key=api_key, model=model)
    return _llm_service