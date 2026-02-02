import json
import os
import config
from utils import llm_client, state_manager, stream_handler

def extract_all_from_text(full_text, model_name=None):
    """
    Uses LLM to extract comprehensive state from full text.
    Returns a dict with keys matching the required optimization rules.
    """
    print(f"🔄 开始全量提取，文本长度: {len(full_text)} 字符")
    if model_name:
        print(f"🤖 使用模型: {model_name}")
    
    prompt = f"""
你是一个专业的网文辅助助手。请阅读以下小说正文内容，并按要求提取关键信息。

### 提取规则：
1. **数值审计：杀戮点 (Killing Points)**
   - 必须扫描文中所有“【系统提示：获得...】”和“【系统提示：消耗...】”字样。
   - 进行精确加减计算：当前杀戮点 = 上章余额（假设初始为0，除非文中另有说明） + 本章获得 - 本章消耗。
   
2. **核心功法：排他性覆盖 (Core Manual)**
   - 识别沈仪（主角）当前修炼的唯一核心内功/心法。
   - 规则：核心功法具有唯一性。若文中出现新功法取代了旧功法，JSON中必须只保留最新的一项，禁止共存。

3. **肉身天赋：独立归类 (Physical Talents)**
   - 识别所有被动增强、永久改变肉身性质的系统奖励（如“XX性”、“XX体”、“XX骨”等）。
   - 规则：将这些被动天赋从 martial_skills（主动武技）中剥离，存入独立的 physical_talents 数组。

4. **物理锁死：装备与坐标 (Inventory & Location)**
   - 记录章节结束时刻的物理状态。
   - 规则：在 status_description 中明确标注当前所处的具体地名或环境；在 inventory 中标注主武器的状态（在手、背负、遗失）。

### 返回格式：
请严格按 JSON 格式返回，不要包含 Markdown 代码块标记，直接返回纯 JSON 字符串。格式如下：
{{
  "shen_yi": {{
    "basic_info": {{
      "name": "沈仪",
      "current_status": "当前状态描述（含坐标/环境）"
    }},
    "realm": "境界层级（如：气血境后期）",
    "assets": {{
      "killing_points": 0,
      "monster_cores": {{ "品阶(如八品)": "数量" }}
    }},
    "equipment": ["装备名1", "装备名2"],
    "cultivation": {{
      "core_manual": {{ "name": "唯一核心功法名", "level": "层级", "features": "功法特性" }},
      "martial_skills": [
        {{ "name": "武技名", "level": "层级/类型" }}
      ],
      "physical_talents": [
        {{ "name": "天赋名", "type": "被动强化", "effect": "具体效果" }}
      ]
    }}
  }},
  "enemy_tracker": {{
    "敌人标识": {{
      "identity": "身份背景",
      "realm": "境界等级",
      "status": "当前动作/状态",
      "threat_level": "威胁等级"
    }}
  }},
  "world_event": {{
    "势力/角色": {{
      "current_action": "当前动向",
      "threat_origin": "威胁来源/实力说明"
    }}
  }},
  "ledger_update": [
    {{ "id": "序号", "desc": "伏笔内容描述", "status": "active/recovered" }}
  ],
  "settings": "总结世界观、势力分布、修炼体系等关键设定（纯文本）",
  "outline": "总结截至目前的剧情大纲（纯文本）"
}}

小说正文内容：
{full_text}
"""
    
    try:
        response = llm_client.generate_content(prompt, model_name=model_name)
        
        # 显示原始响应用于调试
        print(f"🔍 原始AI响应长度: {len(response)} 字符")
        print(f"🔍 原始响应预览: {response[:200]}..." if len(response) > 200 else f"🔍 原始响应: {response}")
        
        # Clean response if it contains markdown code blocks
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        
        # Remove any control characters and clean up the JSON
        import re
        # 更加健壮的JSON清理逻辑
        clean_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_response)
        # 提取可能的JSON对象或数组部分
        json_match = re.search(r'(\{.*\}|\[.*\])', clean_response, re.DOTALL)
        if json_match:
            clean_response = json_match.group(1)
        
        print(f"🧹 清理后响应长度: {len(clean_response)} 字符")
        print(f"🧹 清理后响应预览: {clean_response[:200]}..." if len(clean_response) > 200 else f"🧹 清理后响应: {clean_response}")
        
        data = json.loads(clean_response)
        print(f"✅ JSON解析成功!")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(f"   错误位置: 行 {e.lineno}, 列 {e.colno}")
        print(f"   错误字符附近: {clean_response[max(0, e.pos-20):e.pos+20]}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ 提取过程出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_all_from_text_streaming(full_text, model_name=None, chunk_size=2000):
    """
    使用流式处理提取大文本内容，节省内存
    Args:
        full_text: 完整文本
        model_name: 模型名称
        chunk_size: 分块大小
    Returns:
        合并后的提取结果
    """
    print("🔄 启动流式提取模式...")
    
    # 使用流式处理器分块处理
    chunk_results = stream_handler.streaming_extractor(full_text, model_name, chunk_size)
    
    # 合并结果
    merged_result = merge_chunk_results(chunk_results)
    return merged_result


def merge_chunk_results(chunk_results):
    """
    合并分块提取结果，采用优化的结构。
    """
    merged = {
        "shen_yi": {
            "basic_info": {
                "name": "沈仪",
                "current_status": ""
            },
            "realm": "",
            "assets": {
                "killing_points": 0,
                "monster_cores": {}
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
    
    successful_chunks = 0
    failed_chunks = 0
    
    for result in chunk_results:
        if "error" in result:
            failed_chunks += 1
            continue
        
        successful_chunks += 1
        try:
            extraction_text = result["extraction"].strip()
            if extraction_text.startswith("```json"):
                extraction_text = extraction_text[7:]
            if extraction_text.endswith("```"):
                extraction_text = extraction_text[:-3]
            
            import re
            extraction_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', extraction_text)
            
            data = json.loads(extraction_text)
            
            # 合并沈仪状态
            if "shen_yi" in data:
                sy = data["shen_yi"]
                bi = sy.get("basic_info", {})
                
                # 境界
                merged["shen_yi"]["realm"] = sy.get("realm", merged["shen_yi"]["realm"])
                merged["shen_yi"]["basic_info"]["current_status"] = bi.get("current_status", merged["shen_yi"]["basic_info"]["current_status"])
                
                # 资产 (杀戮点 & 妖丹)
                assets = sy.get("assets", {})
                kp = assets.get("killing_points", 0)
                try:
                    kp = int(kp)
                except:
                    kp = 0
                merged["shen_yi"]["assets"]["killing_points"] += kp
                
                cores = assets.get("monster_cores", {})
                if isinstance(cores, dict):
                    for grade, count in cores.items():
                        merged["shen_yi"]["assets"]["monster_cores"][grade] = merged["shen_yi"]["assets"]["monster_cores"].get(grade, 0) + count
                
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
            if "enemy_tracker" in data:
                merged["enemy_tracker"].update(data["enemy_tracker"])
            
            # 合并世界事件
            if "world_event" in data:
                merged["world_event"].update(data["world_event"])
            
            # 合并伏笔 (ledger_update)
            if "ledger_update" in data:
                for item in data["ledger_update"]:
                    existing_descs = [i.get("desc") for i in merged["ledger_update"]]
                    if item.get("desc") not in existing_descs:
                        merged["ledger_update"].append(item)
            
            # 合并设定
            if "settings" in data:
                if merged["settings"]:
                    merged["settings"] += "\n\n" + data["settings"]
                else:
                    merged["settings"] = data["settings"]
            
            # 合并大纲
            if "outline" in data:
                if merged["outline"]:
                    merged["outline"] += "\n\n" + data["outline"]
                else:
                    merged["outline"] = data["outline"]
            
        except Exception as e:
            print(f"⚠️ 解析第 {result['chunk_index']+1} 块结果时出错: {e}")
            failed_chunks += 1
    
    print(f"📊 处理完成: 成功 {successful_chunks} 块, 失败 {failed_chunks} 块")
    return merged


def save_extracted_data(data):
    """
    Save the extracted data to respective files.
    Adapts to the new detailed JSON structure.
    """
    results = []
    
    # 1. Save Character State & World/Enemy Info
    # Load existing state to preserve other information
    char_state = state_manager.get_character_state()
    
    if "shen_yi" in data:
        char_state["沈仪"] = data["shen_yi"]
        
    if "enemy_tracker" in data and isinstance(data["enemy_tracker"], dict):
        for enemy_name, enemy_info in data["enemy_tracker"].items():
            char_state[f"敌人_{enemy_name}"] = enemy_info
            
    if "world_event" in data and isinstance(data["world_event"], dict):
        for entity_name, entity_info in data["world_event"].items():
            char_state[f"势力_{entity_name}"] = entity_info

    if char_state:
        state_manager.save_character_state(char_state)
        results.append(f"已更新: {os.path.basename(config.FILE_CHARACTER_STATE)}")
        
    # 2. Save Ledger Update (Foreshadowing)
    if "ledger_update" in data:
        import uuid
        import datetime
        new_fs_list = []
        for item in data["ledger_update"]:
            status = "pending" if item.get("status") == "active" else "resolved"
            new_fs_list.append({
                "id": str(uuid.uuid4()) if item.get("id") in ["uuid", "序号"] or not item.get("id") else item["id"],
                "content": item.get("desc", ""),
                "status": status,
                "chapter_created": "全量提取",
                "created_at": datetime.datetime.now().isoformat()
            })
        state_manager.save_foreshadowing(new_fs_list)
        results.append(f"已更新: {os.path.basename(config.FILE_FORESHADOWING)}")
        
    # 3. Save Settings
    if "settings" in data:
        path = os.path.join(config.DIR_SETTINGS, "设定_自动提取.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data["settings"])
        results.append(f"已创建: {os.path.basename(path)}")
        
    # 4. Save Outline
    if "outline" in data:
        path = os.path.join(config.DIR_OUTLINES, "当前细纲.txt") # Or a separate summary file? 
        # User asked for "Outline" extraction. 
        # "Summary of what happened" is useful for "Discuss Outline".
        # Let's append or overwrite "剧情回顾.txt" maybe? 
        # Or just overwrite "当前细纲.txt" if it's treated as "The state of the story".
        # Let's save as "剧情回顾.txt" to distinguish from "Future Outline".
        path = os.path.join(config.DIR_OUTLINES, "剧情回顾.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data["outline"])
        results.append(f"已创建: {os.path.basename(path)}")
        
    return results
