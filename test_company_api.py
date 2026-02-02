import os
import sys
sys.path.append('.')

from utils import llm_client

# 配置公司测试平台
os.environ["LLM_PROVIDER"] = "openai"
os.environ["OPENAI_BASE_URL"] = "your_api_endpoint_here"
os.environ["OPENAI_API_KEY"] = "your_api_key_here"
os.environ["OPENAI_MODEL_NAME"] = "your_model_name_here"

print("🔍 测试公司内部测试平台连接...")
print(f"Base URL: {os.environ['OPENAI_BASE_URL']}")
print(f"Model: {os.environ['OPENAI_MODEL_NAME']}")

try:
    print("\n🚀 发送测试请求...")
    response = llm_client.generate_content("你好，这是一个连接测试")
    print("✅ 连接成功!")
    print(f"响应内容: {response[:100]}...")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    import traceback
    traceback.print_exc()