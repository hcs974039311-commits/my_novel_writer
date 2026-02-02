import os
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed
from openai import OpenAI

# Global clients configuration
CURRENT_PROVIDER = "openai" # 统一使用 OpenAI 兼容模式

def configure():
    """
    确保从环境变量或 session_state 获取最新的配置。
    """
    global CURRENT_PROVIDER
    CURRENT_PROVIDER = "openai" # 强制锁定
    
    # 这里不需要抛出异常，因为有些配置可能在运行时通过 UI 输入
    pass

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
def generate_content(prompt, model_name=None, stream=False):
    """
    统一内容生成函数。
    """
    # 优先使用环境变量（.env），如果为空则由 app.py 通过会话状态动态设置
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    target_model = model_name if model_name else os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    
    if not api_key:
        raise ValueError("❌ 错误：未检测到 API 密钥。请在侧边栏配置或检查 .env 文件。")

    # 逻辑适配：针对公司测试平台或标准 OpenAI 平台
    # 自动识别内网 IP 或特定端口作为公司平台
    is_company_platform = base_url and (":9005" in base_url or "45.78" in base_url)
    
    # 提取 Host (处理 http://... 或 https://... 情况)
    from urllib.parse import urlparse
    parsed_url = urlparse(base_url) if base_url else None
    host_header = parsed_url.netloc if parsed_url else None

    if is_company_platform:
        import requests
        import json
        
        full_url = f"{base_url}/chat/completions" if not base_url.endswith('/chat/completions') else base_url
        headers = {
            "Authorization": api_key if api_key.startswith("Bearer ") else f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StreamlitApp/2.0"
        }
        if host_header: headers["Host"] = host_header
        
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": stream
        }
        
        response = requests.post(full_url, headers=headers, json=payload, timeout=300)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
    else:
        # 标准 OpenAI 兼容 API
        client = OpenAI(
            api_key=api_key if not api_key.startswith("Bearer ") else api_key.replace("Bearer ", ""),
            base_url=base_url if base_url else None,
            timeout=300
        )
        
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        return response.choices[0].message.content

def chat_with_model(history, new_message, model_name=None):
    """
    统一聊天接口。
    """
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    target_model = model_name if model_name else os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

    client = OpenAI(
        api_key=api_key if not api_key.startswith("Bearer ") else api_key.replace("Bearer ", ""),
        base_url=base_url if base_url else None,
        timeout=300
    )
    
    messages = history + [{"role": "user", "content": new_message}]
    response = client.chat.completions.create(
        model=target_model,
        messages=messages,
        max_tokens=4096
    )
    return response.choices[0].message.content
