def stream_response_handler(response):
    """
    处理流式响应
    Args:
        response: requests.Response对象
    Returns:
        完整的响应内容
    """
    full_content = ""
    
    try:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # 处理SSE格式的数据
                if decoded_line.startswith('data: '):
                    data = decoded_line[6:]  # 移除 'data: ' 前缀
                    if data.strip() == '[DONE]':
                        break
                    
                    try:
                        import json
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                full_content += content
                                # 可以在这里添加实时显示逻辑
                                print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        continue
        
        print()  # 换行
        return full_content
        
    except Exception as e:
        print(f"\n❌ 流式处理错误: {e}")
        raise e


def chunked_text_processor(text, chunk_size=2000):
    """
    将大文本分块处理，节省内存
    Args:
        text: 输入文本
        chunk_size: 每块大小（字符数）
    Returns:
        文本块列表
    """
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
    return chunks


def streaming_extractor(text, model_name=None, chunk_size=2000):
    """
    流式处理大文本提取
    Args:
        text: 输入文本
        model_name: 模型名称
        chunk_size: 分块大小
    Returns:
        提取结果列表
    """
    from . import llm_client
    import json
    
    # 将文本分块
    chunks = chunked_text_processor(text, chunk_size)
    results = []
    
    print(f"📝 开始流式处理 {len(chunks)} 个文本块...")
    
    for i, chunk in enumerate(chunks):
        print(f"\n🔄 处理第 {i+1}/{len(chunks)} 块...")
        
        # 构造针对当前块的提取提示词，采用优化的规则和格式
        prompt = f"""
你是一个专业的网文分析助手。请分析以下小说文本片段，并按要求提取关键信息。

### 提取规则：
1. **数值审计：杀戮点 (Killing Points)**
   - 必须扫描片段中所有“【系统提示：获得...】”和“【系统提示：消耗...】”字样。
   - 记录该片段内发生的获得与消耗，以便后续汇总。
   
2. **核心功法：排他性覆盖 (Core Manual)**
   - 识别沈仪（主角）当前修炼的唯一核心内功/心法。
   - 规则：核心功法具有唯一性。若片段中出现新功法取代了旧功法，JSON中必须只保留最新的一项。

3. **肉身天赋：独立归类 (Physical Talents)**
   - 识别片段中涉及的所有被动增强、永久改变肉身性质的系统奖励（如“XX性”、“XX体”、“XX骨”等）。
   - 规则：将这些被动天赋从 martial_skills（主动武技）中剥离，存入独立的 physical_talents 数组。

4. **物理锁死：装备与坐标 (Inventory & Location)**
   - 记录片段结束时刻的物理状态。
   - 规则：在 basic_info.current_status 中明确标注当前所处的具体地名或环境；在 equipment 中标注主武器的状态（在手、背负、遗失）。

### 返回格式：
请严格按 JSON 格式返回，直接返回纯 JSON 字符串。格式如下：
{{
  "shen_yi": {{
    "basic_info": {{
      "name": "沈仪",
      "realm": "境界层级",
      "killing_points": 0,
      "current_status": "当前生理状态与坐标描述"
    }},
    "equipment": ["装备/道具1", "装备/道具2"],
    "cultivation": {{
      "core_manual": {{ "name": "唯一核心功法名", "level": "层级", "features": "特性" }},
      "martial_skills": [{{ "name": "武技名", "level": "层级" }}],
      "physical_talents": [{{ "name": "天赋名", "type": "被动强化", "effect": "效果" }}]
    }}
  }},
  "enemy_tracker": {{
    "敌人名": {{ "identity": "身份", "realm": "境界", "status": "状态", "threat_level": "等级" }}
  }},
  "world_event": {{
    "势力名": {{ "current_action": "动向", "threat_origin": "威胁来源" }}
  }},
  "ledger_update": [
    {{ "id": "序号", "desc": "伏笔内容描述", "status": "active/recovered" }}
  ],
  "settings": "片段涉及的世界观、势力、规则等设定信息",
  "outline": "片段内的关键情节发展"
}}

文本内容：
{chunk}
"""
        
        try:
            # 使用流式处理调用模型
            result = llm_client.generate_content(prompt, model_name=model_name, stream=True)
            results.append({
                "chunk_index": i,
                "content_length": len(chunk),
                "extraction": result
            })
            print(f"✅ 第 {i+1} 块处理完成")
            
        except Exception as e:
            print(f"❌ 第 {i+1} 块处理失败: {e}")
            results.append({
                "chunk_index": i,
                "content_length": len(chunk),
                "error": str(e)
            })
    
    return results