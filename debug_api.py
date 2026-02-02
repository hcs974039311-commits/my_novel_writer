import os
from utils import llm_client

# 设置环境变量
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['OPENAI_BASE_URL'] = 'your_api_endpoint_here'
os.environ['OPENAI_API_KEY'] = 'your_api_key_here'
os.environ['OPENAI_MODEL_NAME'] = 'your_model_name_here'

try:
    print("🔄 测试API连接...")
    result = llm_client.generate_content('hello world')
    print('✅ Success:', result[:100])
except Exception as e:
    print('❌ Error:', str(e))
    import traceback
    traceback.print_exc()