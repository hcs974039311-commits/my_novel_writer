import json
import os
from utils import llm_client

def smart_extract_large_text(full_text, model_name=None, window_size=5000, overlap=1000):
    """
    智能提取大文本内容 - 保持上下文完整性
    Args:
        full_text: 完整文本
        model_name: 模型名称
        window_size: 窗口大小（字符数）
        overlap: 重叠大小（字符数）
    Returns:
        合并后的提取结果
    """
    print(f"🧠 启动智能提取模式...")
    print(f"   文本总长度: {len(full_text)} 字符")
    print(f"   窗口大小: {window_size} 字符")
    print(f"   重叠大小: {overlap} 字符")
    
    # 计算需要处理的窗口数量
    if len(full_text) <= window_size:
        # 文本较短，直接处理
        print("📄 文本较短，直接处理...")
        return extract_from_window(full_text, model_name, is_single_window=True)
    
    # 分窗处理
    windows = create_sliding_windows(full_text, window_size, overlap)
    print(f"📊 需要处理 {len(windows)} 个窗口...")
    
    # 处理每个窗口
    window_results = []
    for i, (window_text, context_info) in enumerate(windows):
        print(f"\n🔄 处理窗口 {i+1}/{len(windows)} ({context_info})")
        
        try:
            result = extract_from_window(window_text, model_name, window_info=context_info)
            window_results.append({
                "window_index": i,
                "context_info": context_info,
                "result": result,
                "success": True
            })
            print(f"✅ 窗口 {i+1} 处理完成")
        except Exception as e:
            print(f"❌ 窗口 {i+1} 处理失败: {e}")
            window_results.append({
                "window_index": i,
                "context_info": context_info,
                "error": str(e),
                "success": False
            })
    
    # 合并结果
    print("\n🔄 合并所有窗口结果...")
    merged_result = merge_window_results(window_results)
    return merged_result

def create_sliding_windows(text, window_size, overlap):
    """
    创建滑动窗口
    Args:
        text: 输入文本
        window_size: 窗口大小
        overlap: 重叠大小
    Returns:
        窗口列表 [(文本, 上下文信息), ...]
    """
    windows = []
    text_length = len(text)
    
    start = 0
    window_index = 0
    
    while start < text_length:
        end = min(start + window_size, text_length)
        window_text = text[start:end]
        
        # 确定上下文信息
        if start == 0 and end == text_length:
            context_info = "完整文本"
        elif start == 0:
            context_info = f"开头部分(1-{end}字符)"
        elif end == text_length:
            context_info = f"结尾部分({start+1}-{text_length}字符)"
        else:
            context_info = f"中间部分({start+1}-{end}字符)"
        
        windows.append((window_text, context_info))
        
        # 移动到下一个窗口
        start += (window_size - overlap)
        window_index += 1
        
        # 避免无限循环
        if window_index > 100:  # 最多处理100个窗口
            break
    
    return windows

def extract_from_window(window_text, model_name=None, is_single_window=False, window_info=""):
    """
    从单个窗口提取信息，采用优化的规则和格式。
    """
    # 构造通用规则说明
    rules_instruction = """
### 提取规则：
1. **数值审计：杀戮点 (Killing Points)**
   - 必须扫描片段中所有“【系统提示：获得...】”和“【系统提示：消耗...】”字样。
   - 记录该片段内发生的获得与消耗，以便后续汇总。
   
2. **核心功法：排他性覆盖 (Core Manual)**
   - 识别沈仪（主角）当前修炼的唯一核心内功/心法。
   - 规则：核心功法具有唯一性。若片段中出现新功法取代了旧功法，JSON中必须只保留最新的一项。

3. **肉身天赋：独立归类 (Physical Talents)**
   - 识别片段中涉及的所有被动增强、永久改变肉身性质的系统奖励（如“XX性”、“XX体”、“XX骨”等）。
   - 规则：将这些被动天赋从 martial_skills 中剥离，存入独立的 physical_talents 数组。

4. **物理锁死：装备与坐标 (Inventory & Location)**
   - 记录片段结束时刻的物理状态。
   - 规则：在 basic_info.current_status 中明确标注当前所处的具体地名或环境；在 equipment 中标注主武器的状态（在手、背负、遗失）。

### 返回格式：
请严格按 JSON 格式返回，直接返回纯 JSON 字符串。格式如下：
{
  "shen_yi": {
    "basic_info": {
      "name": "沈仪",
      "realm": "境界层级",
      "killing_points": 0,
      "current_status": "当前生理状态与坐标描述"
    },
    "equipment": ["装备/道具1", "装备/道具2"],
    "cultivation": {
      "core_manual": { "name": "唯一核心功法名", "level": "层级", "features": "特性" },
      "martial_skills": [{ "name": "武技名", "level": "层级" }],
      "physical_talents": [{ "name": "天赋名", "type": "被动强化", "effect": "效果" }]
    }
  },
  "enemy_tracker": {
    "敌人名": { "identity": "身份", "realm": "境界", "status": "状态", "threat_level": "等级" }
  },
  "world_event": {
    "势力名": { "current_action": "动向", "threat_origin": "威胁来源" }
  },
  "ledger_update": [
    { "id": "序号", "desc": "伏笔内容描述", "status": "active/recovered" }
  ],
  "settings": "片段涉及的世界观、势力、规则等设定信息",
  "outline": "片段内的关键情节发展"
}
"""

    if is_single_window:
        prompt = f"""
你是一个专业的网文分析助手。请仔细阅读以下小说全文，并按要求提取关键信息。
{rules_instruction}
小说正文内容：
{window_text}
"""
    else:
        prompt = f"""
你是一个专业的网文分析助手。请仔细阅读以下小说文本片段（这是小说的{window_info}部分），并按要求提取关键信息。
{rules_instruction}
小说片段内容：
{window_text}
"""

    # 调用模型
    response = llm_client.generate_content(prompt, model_name=model_name)
    
    # 清理和解析响应
    clean_response = response.strip()
    
    # 移除可能的markdown代码块标记
    if clean_response.startswith("```json"):
        clean_response = clean_response[7:]
    if clean_response.endswith("```"):
        clean_response = clean_response[:-3]
    
    # 移除控制字符和非法Unicode字符
    import re
    # 更加健壮的JSON清理逻辑
    clean_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_response)
    # 提取可能的JSON对象或数组部分
    json_match = re.search(r'(\{.*\}|\[.*\])', clean_response, re.DOTALL)
    if json_match:
        clean_response = json_match.group(1)
    
    # 修复不完整的JSON字符串
    # 处理未闭合的引号
    quote_count = clean_response.count('"')
    if quote_count % 2 != 0:
        # 如果引号数量为奇数，尝试修复
        last_quote_pos = clean_response.rfind('"')
        if last_quote_pos != -1:
            # 在最后一个引号后添加闭合引号
            clean_response = clean_response[:last_quote_pos+1] + '"' + clean_response[last_quote_pos+1:]
    
    # 处理未闭合的大括号
    open_braces = clean_response.count('{')
    close_braces = clean_response.count('}')
    if open_braces > close_braces:
        clean_response += '}' * (open_braces - close_braces)
    
    open_brackets = clean_response.count('[')
    close_brackets = clean_response.count(']')
    if open_brackets > close_brackets:
        clean_response += ']' * (open_brackets - close_brackets)
    
    # 解析JSON
    try:
        data = json.loads(clean_response)
        return data
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON解析失败: {e}")
        print(f"响应长度: {len(clean_response)} 字符")
        print(f"响应预览: {clean_response[:300]}...")
        
        # 尝试更宽松的解析方法
        try:
            # 尝试找到JSON对象的开始和结束
            start_pos = clean_response.find('{')
            if start_pos != -1:
                # 从第一个{开始解析
                remaining_text = clean_response[start_pos:]
                # 尝试逐步缩短文本直到能解析为止
                for i in range(len(remaining_text), 0, -1):
                    try:
                        partial_json = remaining_text[:i]
                        data = json.loads(partial_json)
                        print(f"✅ 部分解析成功，使用前{i}个字符")
                        return data
                    except:
                        continue
        except:
            pass
        
        # 返回空的结果结构
        return {
            "shen_yi": {
                "basic_info": {
                    "name": "沈仪",
                    "realm": "",
                    "killing_points": 0,
                    "current_status": ""
                },
                "equipment": [],
                "cultivation": {
                    "core_manual": {"name": "", "level": "", "features": ""},
                    "martial_skills": [],
                    "physical_talents": []
                }
            },
            "enemy_tracker": {},
            "world_event": {},
            "ledger_update": [],
            "settings": "",
            "outline": ""
        }

def merge_window_results(window_results):
    """
    合并窗口结果，采用优化的结构。
    """
    merged = {
        "shen_yi": {
            "basic_info": {
                "name": "沈仪",
                "realm": "",
                "killing_points": 0,
                "current_status": ""
            },
            "equipment": [],
            "cultivation": {
                "core_manual": {"name": "", "level": "", "features": ""},
                "martial_skills": [],
                "physical_talents": []
            }
        },
        "enemy_tracker": {},
        "world_event": {},
        "ledger_update": [],
        "settings": "",
        "outline": ""
    }
    
    successful_windows = 0
    failed_windows = 0
    
    # 按顺序处理，以保证状态更新正确
    for result in window_results:
        if not result["success"]:
            failed_windows += 1
            continue
        
        successful_windows += 1
        window_data = result["result"]
        
        try:
            # 合并沈仪状态
            if "shen_yi" in window_data:
                sy = window_data["shen_yi"]
                bi = sy.get("basic_info", {})
                # 鲁棒性处理：确保杀戮点为数值
                kp = bi.get("killing_points", 0)
                try:
                    kp = int(kp)
                except (ValueError, TypeError):
                    kp = 0
                merged["shen_yi"]["basic_info"]["killing_points"] += kp
                merged["shen_yi"]["basic_info"]["realm"] = bi.get("realm", merged["shen_yi"]["basic_info"]["realm"])
                merged["shen_yi"]["basic_info"]["current_status"] = bi.get("current_status", merged["shen_yi"]["basic_info"]["current_status"])
                
                # 装备去重：确保为列表
                equipment = sy.get("equipment", [])
                if isinstance(equipment, list):
                    for i in equipment:
                        if i and i not in merged["shen_yi"]["equipment"]:
                            merged["shen_yi"]["equipment"].append(i)
                
                if "cultivation" in sy:
                    cult = sy["cultivation"]
                    if not isinstance(cult, dict): cult = {}
                    
                    if cult.get("core_manual", {}).get("name"):
                        merged["shen_yi"]["cultivation"]["core_manual"] = cult["core_manual"]
                    
                    martial_skills = cult.get("martial_skills", [])
                    if isinstance(martial_skills, list):
                        for s in martial_skills:
                            s_name = s.get("name") if isinstance(s, dict) else s
                            if not s_name: continue
                            existing_names = [sk.get("name") if isinstance(sk, dict) else sk for sk in merged["shen_yi"]["cultivation"]["martial_skills"]]
                            if s_name not in existing_names:
                                merged["shen_yi"]["cultivation"]["martial_skills"].append(s)
                                
                    physical_talents = cult.get("physical_talents", [])
                    if isinstance(physical_talents, list):
                        for t in physical_talents:
                            t_name = t.get("name") if isinstance(t, dict) else t
                            if not t_name: continue
                            existing_names = [tk.get("name") if isinstance(tk, dict) else tk for tk in merged["shen_yi"]["cultivation"]["physical_talents"]]
                            if t_name not in existing_names:
                                merged["shen_yi"]["cultivation"]["physical_talents"].append(t)
            
            # 合并敌人
            if "enemy_tracker" in window_data:
                merged["enemy_tracker"].update(window_data["enemy_tracker"])
            
            # 合并世界事件
            if "world_event" in window_data:
                merged["world_event"].update(window_data["world_event"])
            
            # 合并伏笔（ledger_update）
            if "ledger_update" in window_data:
                for item in window_data["ledger_update"]:
                    # 简单去重：基于desc
                    existing_descs = [i.get("desc") for i in merged["ledger_update"]]
                    if item.get("desc") not in existing_descs:
                        merged["ledger_update"].append(item)
            
            # 合并设定
            if "settings" in window_data and window_data["settings"]:
                if merged["settings"]:
                    merged["settings"] += "\n" + window_data["settings"]
                else:
                    merged["settings"] = window_data["settings"]
            
            # 合并大纲
            if "outline" in window_data and window_data["outline"]:
                if merged["outline"]:
                    merged["outline"] += "\n" + window_data["outline"]
                else:
                    merged["outline"] = window_data["outline"]
                    
        except Exception as e:
            print(f"⚠️ 合并窗口 {result['window_index']} 出错: {e}")
    
    return merged

def get_optimal_window_params(text_length):
    """
    根据文本长度获取最优的窗口参数
    Args:
        text_length: 文本长度
    Returns:
        (window_size, overlap) 元组
    """
    if text_length < 5000:
        return 5000, 1000  # 小文本
    elif text_length < 20000:
        return 8000, 1500  # 中等文本
    elif text_length < 50000:
        return 10000, 2000  # 大文本
    else:
        return 12000, 2500  # 超大文本