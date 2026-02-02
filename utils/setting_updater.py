"""
设定自动更新工具
用于在正文生成后自动分析内容并更新设定文件夹
"""

import os
import json
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import llm_client
import config

def analyze_and_update_settings(chapter_content, chapter_title=""):
    """
    分析章节内容并自动更新设定文件
    
    Args:
        chapter_content (str): 章节正文内容
        chapter_title (str): 章节标题
    
    Returns:
        dict: 更新结果报告
    """
    results = {
        "updated_files": [],
        "new_settings": [],
        "character_updates": [],
        "world_updates": []
    }
    
    try:
        analysis_prompt = f"""
请分析以下小说章节内容，提取其中的新设定信息、主角状态变动及剧情梗概。
特别注意：文中提到的“系统提示”中的杀戮点变动和物品消耗必须精确提取。
黑獒在这一章中展现了其真实境界（七品大妖），请务必更新敌人境界。

章节标题: {chapter_title}
章节内容:
{chapter_content[:4000]}

请严格按照以下JSON格式返回分析结果：

{{
    "new_characters": [
        {{
            "name": "角色姓名",
            "description": "角色描述",
            "type": "主要角色/次要角色/临时角色",
            "first_appearance": "{chapter_title}"
        }}
    ],
    "world_elements": [
        {{
            "element": "设定元素名称",
            "type": "世界观/地图/势力/规则/物品",
            "description": "详细描述",
            "first_mention": "{chapter_title}"
        }}
    ],
    "setting_updates": [
        {{
            "type": "设定分类",
            "name": "设定项名称",
            "description": "新增或修改的设定内容"
        }}
    ],
    "character_state_updates": {{
        "killing_points": "变动说明（如：消耗1000点，剩余500点）",
        "items_consumed": ["物品1(等级/品阶)", "物品2"],
        "items_gained": ["物品3(等级/品阶)"],
        "new_skills": ["技能1"],
        "new_realm": "最新达到的境界名称（如：气血境后期）",
        "enemy_updates": [
            {{"name": "黑獒", "status": "已死亡/重伤逃走/实力提升", "new_realm": "七品"}}
        ]
    }},
    "plot_summary": "用100字以内的简练语言总结本章核心剧情"
}}
"""
        
        # 调用LLM进行分析
        current_model = os.environ.get("DEFAULT_MODEL_NAME", "deepseek-v3.2-251201-hs")
        analysis_result = llm_client.generate_content(analysis_prompt, model_name=current_model)
        
        # 解析分析结果
        try:
            # 兼容 Markdown 代码块
            json_str = analysis_result.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            parsed_analysis = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return results
        
        # 2. 更新各类文件
        setting_dir = config.DIR_SETTINGS if hasattr(config, 'DIR_SETTINGS') else "设定"
        os.makedirs(setting_dir, exist_ok=True)
        
        # 更新角色设定
        if parsed_analysis.get("new_characters"):
            character_file = os.path.join(setting_dir, "设定_角色.txt")
            update_setting_file(character_file, "角色设定", parsed_analysis["new_characters"], chapter_title)
            results["updated_files"].append("设定_角色.txt")
        
        # 更新世界观设定
        if parsed_analysis.get("world_elements"):
            world_file = os.path.join(setting_dir, "设定_世界观.txt")
            update_setting_file(world_file, "世界观设定", parsed_analysis["world_elements"], chapter_title)
            results["updated_files"].append("设定_世界观.txt")
        
        # 更新通用设定
        if parsed_analysis.get("setting_updates"):
            general_file = os.path.join(setting_dir, "设定_通用.txt")
            update_setting_file(general_file, "通用设定", parsed_analysis["setting_updates"], chapter_title)
            results["updated_files"].append("设定_通用.txt")
            
        # 3. 更新主角状态 (JSON)
        if parsed_analysis.get("character_state_updates"):
            update_character_state(parsed_analysis["character_state_updates"])
            results["updated_files"].append("设定_角色状态.json")
            
        # 4. 更新剧情回顾 (Txt)
        if parsed_analysis.get("plot_summary"):
            append_to_plot_review(parsed_analysis["plot_summary"], chapter_title)
            results["updated_files"].append("剧情回顾.txt")
        
        # 5. 更新自动提取汇总
        update_auto_extract_summary(setting_dir, parsed_analysis, chapter_title)
        
        print(f"✅ 设定与状态更新完成: {len(results['updated_files'])} 个文件已处理")
        return results
        
    except Exception as e:
        print(f"❌ 设定更新失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return results

def update_setting_file(file_path, category, new_items, chapter_title):
    """
    更新单个设定文件
    """
    # 读取现有内容
    existing_content = ""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # 添加时间戳和章节信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n\n=== {chapter_title} 更新 ({timestamp}) ===\n"
    
    # 格式化新内容
    new_content_parts = []
    for item in new_items:
        if isinstance(item, dict):
            # 兼容多种可能的 key 名
            item_type = item.get('type') or item.get('category') or '未知类型'
            item_name = item.get('name') or item.get('element') or item.get('point') or ''
            item_desc = item.get('description') or item.get('content') or item.get('significance') or ''
            
            line = f"[{item_type}] {item_name}".strip()
            item_lines = [line]
            if item_desc:
                item_lines.append(f"  描述: {item_desc}")
            if 'first_appearance' in item:
                item_lines.append(f"  首次出现: {item['first_appearance']}")
            elif 'first_mention' in item:
                item_lines.append(f"  首次提到: {item['first_mention']}")
                
            new_content_parts.append("\n".join(item_lines))
        else:
            new_content_parts.append(str(item))
    
    new_content = "\n".join(new_content_parts)
    
    # 写入文件
    with open(file_path, 'a', encoding='utf-8') as f:
        if existing_content and not existing_content.strip():
            # 文件非空但只有空白字符，直接覆盖或追加
            pass
        elif existing_content and not existing_content.endswith('\n'):
            f.write('\n')
        f.write(header)
        f.write(new_content)
        f.write('\n')

def update_character_state(state_updates):
    """更新角色状态 JSON 文件 - 深度分级管理版本"""
    from utils import state_manager
    state = state_manager.get_character_state()
    
    main_char = "沈仪"
    if main_char in state:
        # 1. 境界更新
        new_realm = state_updates.get('new_realm')
        if new_realm:
            state[main_char]["realm"] = new_realm
            
        # 2. 资产更新 (杀戮点 & 妖丹分级)
        if "assets" not in state[main_char]:
            state[main_char]["assets"] = {"killing_points": 0, "monster_cores": {}}
        
        # 确保 monster_cores 是字典结构
        if not isinstance(state[main_char]["assets"].get("monster_cores"), dict):
            state[main_char]["assets"]["monster_cores"] = {}

        # 杀戮点
        kp_str = state_updates.get('killing_points', '')
        nums = re.findall(r'(\d+)', kp_str)
        if nums:
            new_val = int(nums[-1])
            if new_val > 10 or "剩余0" in kp_str:
                state[main_char]["assets"]["killing_points"] = new_val
        
        # 物品/妖丹分级处理函数
        def _parse_item_with_grade(item_str):
            # 提取品级 (如 八品, 8品, 七品)
            grade_match = re.search(r'([一二三四五六七八九十\d]+品)', item_str)
            grade = grade_match.group(1) if grade_match else "未知品阶"
            
            # 提取数量
            count = 1
            num_match = re.search(r'([一二三四五六七八九十\d]+)(?:枚|颗|个)', item_str)
            if num_match:
                num_str = num_match.group(1)
                cn_num_map = {"一":1, "二":2, "三":3, "四":4, "五":5, "六":6, "七":7, "八":8, "九":9, "十":10}
                count = cn_num_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
            return grade, count

        # 妖丹扣减 (分品阶)
        consumed = state_updates.get('items_consumed', [])
        for item_name in consumed:
            if "妖丹" in item_name:
                grade, count = _parse_item_with_grade(item_name)
                current_cores = state[main_char]["assets"]["monster_cores"]
                
                # 强化：自动处理字符串类型的数值
                existing_val = current_cores.get(grade, 0)
                try:
                    existing_val = int(existing_val)
                except:
                    existing_val = 0
                
                current_cores[grade] = max(0, existing_val - count)
                if current_cores[grade] <= 0:
                    del current_cores[grade]
                print(f"DEBUG: 扣减 {grade} 妖丹 {count} 枚，剩余 {current_cores.get(grade, 0)}")

        # 妖丹获得 (分品阶)
        gained = state_updates.get('items_gained', [])
        for item_name in gained:
            if "妖丹" in item_name:
                grade, count = _parse_item_with_grade(item_name)
                current_cores = state[main_char]["assets"]["monster_cores"]
                current_cores[grade] = current_cores.get(grade, 0) + count
                print(f"DEBUG: 获得 {grade} 妖丹 {count} 枚")

        # 3. 装备更新 (排除掉已处理的资产)
        if "equipment" in state[main_char]:
            for item_name in consumed:
                if "妖丹" in item_name: continue
                core_item = re.sub(r'(\d+|枚|颗|个|把|位|（.*?）|\(.*?\)|\s+|八品|九品|七品|珍贵|珍稀)', '', item_name)
                if len(core_item) < 2: continue
                for i, existing in enumerate(state[main_char]["equipment"]):
                    if core_item in existing or existing in core_item:
                        state[main_char]["equipment"].pop(i)
                        break
            
            for item in gained:
                if "妖丹" in item: continue
                if item not in state[main_char]["equipment"]:
                    state[main_char]["equipment"].append(item)
                    
        # 4. 更新强敌/势力状态 (Enemy Updates)
        enemy_updates = state_updates.get('enemy_updates', [])
        for update in enemy_updates:
            enemy_name = update.get('name')
            if not enemy_name: continue
            
            # 查找匹配的敌人字段 (敌人_XXX)
            key = f"敌人_{enemy_name}"
            if key in state:
                if 'status' in update: state[key]['status'] = update['status']
                if 'new_realm' in update: 
                    state[key]['realm'] = update['new_realm']
                    print(f"DEBUG: 敌人 {enemy_name} 境界更新为: {update['new_realm']}")
                # 兜底：如果 status 里提到了品阶但 new_realm 为空，尝试二次提取
                if not update.get('new_realm') and '品' in update.get('status', ''):
                    realm_match = re.search(r'([一二三四五六七八九十\d]+品)', update['status'])
                    if realm_match:
                        state[key]['realm'] = realm_match.group(1)

        # 5. 更新沈仪当前位置/剧情状态
        if 'plot_summary' in state_updates:
             state[main_char]["basic_info"]["current_status"] = state_updates['plot_summary']
    
    # 记录历史
    if 'history' not in state: state['history'] = []
    state['history'].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "updates": state_updates})
    
    state_manager.save_character_state(state)

def append_to_plot_review(summary, chapter_title):
    """追加到剧情回顾.txt"""
    review_file = os.path.join(config.DIR_OUTLINES, "剧情回顾.txt")
    os.makedirs(os.path.dirname(review_file), exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n\n--- {chapter_title} ({timestamp}) ---\n{summary}\n"
    
    with open(review_file, 'a', encoding='utf-8') as f:
        f.write(entry)

def update_auto_extract_summary(setting_dir, analysis_data, chapter_title):
    """
    更新自动提取的设定摘要文件
    
    Args:
        setting_dir (str): 设定目录路径
        analysis_data (dict): 分析数据
        chapter_title (str): 章节标题
    """
    summary_file = os.path.join(setting_dir, "设定_自动提取.txt")
    
    # 读取现有摘要
    existing_summary = ""
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            existing_summary = f.read().strip()
    
    # 生成新的摘要内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_summary_parts = [existing_summary] if existing_summary else []
    
    new_summary_parts.append(f"\n\n=== {chapter_title} 设定摘要 ({timestamp}) ===")
    
    # 添加角色信息
    if "new_characters" in analysis_data and analysis_data["new_characters"]:
        new_summary_parts.append("\n【新增角色】")
        for char in analysis_data["new_characters"]:
            new_summary_parts.append(f"- {char.get('name', '未知')} ({char.get('type', '角色')})")
    
    # 添加世界观元素
    if "world_elements" in analysis_data and analysis_data["world_elements"]:
        new_summary_parts.append("\n【世界观更新】")
        for element in analysis_data["world_elements"]:
            elem_type = element.get('type', '未知')
            elem_name = element.get('element', '未知元素')
            new_summary_parts.append(f"- {elem_name} [{elem_type}]")
    
    # 添加重要情节点
    if "plot_points" in analysis_data and analysis_data["plot_points"]:
        new_summary_parts.append("\n【关键情节点】")
        for point in analysis_data["plot_points"]:
            point_type = point.get('type', '一般')
            point_desc = point.get('point', '无描述')
            new_summary_parts.append(f"- {point_desc} ({point_type})")
    
    # 写入摘要文件
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_summary_parts).strip())

def get_setting_summary():
    """
    获取设定文件夹的概要信息
    
    Returns:
        dict: 各设定文件的内容摘要
    """
    setting_dir = config.DIR_SETTINGS if hasattr(config, 'DIR_SETTINGS') else "设定"
    
    if not os.path.exists(setting_dir):
        return {}
    
    summary = {}
    for filename in os.listdir(setting_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(setting_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 只取前500字符作为摘要
                    summary[filename] = content[:500] + ("..." if len(content) > 500 else "")
            except Exception as e:
                print(f"读取设定文件 {filename} 失败: {e}")
                summary[filename] = "读取失败"
    
    return summary