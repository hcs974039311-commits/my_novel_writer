import os
import sys
sys.path.append('.')

from utils import smart_extractor
import config

# 设置正确的环境变量
os.environ['LLM_PROVIDER'] = 'openai'
os.environ['OPENAI_BASE_URL'] = 'your_api_endpoint_here'
os.environ['OPENAI_API_KEY'] = 'your_api_key_here'
os.environ['OPENAI_MODEL_NAME'] = 'your_model_name_here'

def debug_smart_extraction():
    """调试智能提取功能"""
    print("🔍 调试智能提取功能...")
    
    # 读取测试文件
    test_file = os.path.join(config.PROJECT_ROOT, "正文", "我的正文1-11章.txt")
    
    if not os.path.exists(test_file):
        print(f"❌ 未找到测试文件: {test_file}")
        return
    
    print(f"📖 读取文件: {test_file}")
    with open(test_file, 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    print(f"📊 文件大小: {len(full_text)} 字符")
    
    # 测试非常小的段落
    test_text = full_text[:500]  # 只测试前500字符
    print(f"📝 测试文本长度: {len(test_text)} 字符")
    
    try:
        print("\n🚀 开始智能提取测试...")
        result = smart_extractor.smart_extract_large_text(
            test_text,
            model_name="deepseek-v3.2-251201-hs",
            window_size=1000,
            overlap=200
        )
        
        print("\n✅ 提取完成！结果预览:")
        print(f"角色状态数量: {len(result.get('character_state', {}))}")
        print(f"伏笔数量: {len(result.get('foreshadowing', []))}")
        print(f"设定长度: {len(result.get('settings', ''))} 字符")
        print(f"大纲长度: {len(result.get('outline', ''))} 字符")
        
        if result.get('character_state'):
            print("\n👥 角色状态:")
            for name, state in list(result['character_state'].items())[:3]:
                print(f"  {name}: {state}")
        
        if result.get('foreshadowing'):
            print("\n🔮 伏笔线索:")
            for foreshadowing in result['foreshadowing'][:2]:
                print(f"  {foreshadowing.get('content', '')}")
                
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_smart_extraction()