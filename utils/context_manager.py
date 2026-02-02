import os
import glob
import config
from utils import state_manager

def get_sorted_chapters():
    """Return list of chapter files sorted by name."""
    files = glob.glob(os.path.join(config.DIR_BODY, "*.txt"))
    # Sort files. Assuming naming format "第xx章" allows alphabetical sort or need custom key
    # Default sort might work if padding is used (第01章), otherwise need regex
    # Let's try to extract numbers for sorting
    def sort_key(f):
        basename = os.path.basename(f)
        import re
        match = re.search(r'第(\d+)章', basename)
        if match:
            return int(match.group(1))
        return 0
    
    return sorted(files, key=sort_key)

def get_recent_chapters_content(n=5):
    """Get content of last n chapters."""
    files = get_sorted_chapters()
    recent = files[-n:] if n > 0 else []
    
    content_parts = []
    for f in recent:
        with open(f, 'r', encoding='utf-8') as file:
            content_parts.append(f"--- File: {os.path.basename(f)} ---\n{file.read()}\n")
            
    return "\n".join(content_parts)

def get_settings_summary():
    """Read all settings files."""
    settings_content = []
    files = glob.glob(os.path.join(config.DIR_SETTINGS, "设定_*.txt"))
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                settings_content.append(f"--- Setting: {os.path.basename(f)} ---\n{file.read()}\n")
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(f, 'r', encoding='gbk') as file:
                    settings_content.append(f"--- Setting: {os.path.basename(f)} ---\n{file.read()}\n")
            except UnicodeDecodeError:
                # 如果都失败，跳过该文件
                print(f"警告：无法读取设定文件 {f}，跳过处理")
                continue
    return "\n".join(settings_content)

def auto_style_loader():
    """
    自动扫描 assets/ 下的所有文档，提取文风指纹。
    """
    assets_path = config.DIR_ASSETS if hasattr(config, 'DIR_ASSETS') else "assets/"
    style_files = glob.glob(os.path.join(assets_path, "*.txt"))
    if not style_files:
        return ""
    
    style_contents = []
    for f in style_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                # 读取内容，作为风格参考
                content = file.read()
                if content.strip():
                    style_contents.append(f"--- 风格参考片段 ({os.path.basename(f)}) ---\n{content[:1500]}")
        except Exception as e:
            print(f"读取文风文件 {f} 失败: {e}")
    
    return "\n\n".join(style_contents)

def build_context_prompt(query, recent_n=5, include_style=True):
    """
    Build the full context for the LLM.
    Includes:
    1. Task Description (Query)
    2. Character State (JSON)
    3. Pending Foreshadowing (JSON)
    4. Relevant Settings (Txts)
    5. Recent Story Context (Last N chapters)
    6. Auto Style Injection
    """
    
    # 1. State
    char_state = state_manager.get_character_state()
    foreshadowing = state_manager.get_foreshadowing()
    # Filter only pending foreshadowing? Or all? User said "check current foreshadowing"
    active_foreshadowing = [f for f in foreshadowing if f.get('status') == 'pending']
    
    state_section = f"""
# 当前状态信息
## 角色状态
{char_state}

## 待回收伏笔
{active_foreshadowing}
"""

    # 2. Settings
    settings_section = f"""
# 世界观与设定
{get_settings_summary()}
"""

    # 3. Recent Context
    story_section = f"""
# 最近剧情回顾 (参考上下文)
{get_recent_chapters_content(n=recent_n)}
"""

    # 4. Style Reference (Auto & Learned)
    style_section = ""
    if include_style:
        # A. 基础素材指纹
        style_fingerprint = auto_style_loader()
        
        # B. 动态学习的用户风格
        learned_style_instruction = ""
        try:
            from utils.style_analyzer import StyleAnalyzer, StyleManager
            analyzer = StyleAnalyzer()
            manager = StyleManager()
            
            # 尝试根据最近正文识别场景
            recent_content = get_recent_chapters_content(n=1)
            scene_type = analyzer.classify_scene(recent_content)
            
            # 获取该场景的风格推荐
            learned_style = manager.get_style_recommendation(scene_type)
            if learned_style:
                recommendations = []
                if learned_style.get('ai_metaphor_removed', 0) > 0.2:
                    recommendations.append("- 严禁使用“如XXX般”等冗余比喻")
                if learned_style.get('dialogue_added', 0) > 0.2:
                    recommendations.append("- 增加人物对话频率，通过台词推动剧情")
                if learned_style.get('action_detail_added', 0) > 0.2:
                    recommendations.append("- 细化动作过程，增加发力、撞击等物理细节")
                if learned_style.get('direct_expression_added', 0) > 0.2:
                    recommendations.append("- 表达需简洁有力，减少修饰性前缀")
                
                if recommendations:
                    learned_style_instruction = "\n## 您的写作偏好参考 (基于历史修改分析)\n" + "\n".join(recommendations)
        except Exception as e:
            print(f"加载学习风格失败: {e}")

        if style_fingerprint or learned_style_instruction:
            style_section = f"""
# 文风指纹与写作偏好
{learned_style_instruction}

## 基础文风参考素材 (极道流元指令)
模仿以下素材的“极道流”文风：
- 动作描述：暴力动词密度高，强调物理撞击感。
- 节奏感：短句比例高，干脆利落。
- 侧重：侧重于主角的横推和路人的震惊反应。

参考素材：
{style_fingerprint}
"""

    # 添加内容质量和风格约束
    quality_constraints = """
# 内容质量要求
- 字数目标：2800-3200字
- 内容密度：保持紧凑叙事，避免冗余描述
- 节奏控制：合理分配各剧情节点的文字比重

# 语言风格约束
- 禁止使用："如XXX般"、"像XXX一样"、"仿佛"、"好似"等模板化比喻
- 推荐使用：直接描述法，如"银光掠过"、"血珠滚落"、"刀刃森寒"
- 动作描述：使用暴力动词，强调物理撞击感
- 环境描写：具体而微，避免抽象形容词堆砌

# 环境逻辑约束
- 地理一致性：平原地形不应出现青石板、石阶等建筑元素
- 季节合理性：根据当前季节调整环境描述
- 物理逻辑：动作与环境匹配（如室内战斗不应有风吹草动）
- 设定遵循：严格遵守已建立的世界观设定
"""
    
    # Combine
    full_prompt = f"""
{state_section}

{settings_section}

{story_section}

{style_section}

{quality_constraints}

# 当前任务
{query}
"""
    return full_prompt

def build_setting_discussion_prompt(query, recent_n=3):
    """
    为“探讨设定”功能构建的专用提示词。
    严格限定只能生成设定相关内容，禁止输出正文。
    """
    # 1. State
    char_state = state_manager.get_character_state()
    foreshadowing = state_manager.get_foreshadowing()
    active_foreshadowing = [f for f in foreshadowing if f.get('status') == 'pending']
    
    # 2. Context sections
    state_section = f"""
# 核心参考数据
## 1. 角色当前状态
{char_state}

## 2. 待回收伏笔
{active_foreshadowing}
"""

    # Limit settings summary length to avoid token overflow
    settings_summary = get_settings_summary()
    if len(settings_summary) > 3000:
        settings_summary = settings_summary[:3000] + "..."

    settings_section = f"""
## 3. 已有设定概览
{settings_summary}
"""

    story_section = f"""
## 4. 前情提要 (参考上下文)
{get_recent_chapters_content(n=recent_n)}
"""

    # 3. Strict Instructions for Setting Discussion
    instruction = f"""
# 任务：智能设定探讨

[身份设定]：你现在是一位专业的网文世界架构师，专注于协助作者完善小说的设定体系。

[核心原则]：
- 严禁生成任何小说正文内容（如故事情节、对话、场景描写等）
- 仅允许输出设定相关的结构化内容
- 回答必须具体、可落地，避免空泛的描述

[用户需求]：
{query}

[输出规范]：
请严格按以下结构组织你的回答：

1. 设定类型识别
   - 明确指出这是哪一类设定（如：世界观、人物、势力、战力体系、物品道具、历史背景、规则机制等）

2. 现状分析
   - 结合已有设定和角色状态，分析当前设定的完整度
   - 指出现有设定中的空白点或矛盾点

3. 设定补充建议
   - 提供具体、详细的设定内容
   - 包含必要的数值、等级、分类等量化信息
   - 确保与现有世界观逻辑一致

4. 实施建议
   - 说明该设定如何在后续剧情中发挥作用
   - 提供1-2个可能的应用场景
"""

    return state_section + settings_section + story_section + "\n" + instruction

def build_outline_discussion_prompt(query, recent_n=5):
    """
    为“探讨细纲”功能构建的专用提示词。
    严格限定只能生成细纲相关内容，禁止输出大篇幅正文。
    """
    # 1. State
    char_state = state_manager.get_character_state()
    foreshadowing = state_manager.get_foreshadowing()
    active_foreshadowing = [f for f in foreshadowing if f.get('status') == 'pending']
    
    # 2. Context sections
    state_section = f"""
# 核心参考数据
## 1. 角色当前状态
{char_state}

## 2. 待回收伏笔
{active_foreshadowing}
"""

    # Limit settings summary length to avoid token overflow
    settings_summary = get_settings_summary()
    if len(settings_summary) > 3000:
        settings_summary = settings_summary[:3000] + "..."

    settings_section = f"""
## 3. 世界观与设定
{settings_summary}
"""

    story_section = f"""
## 4. 前情提要 (最近章节)
{get_recent_chapters_content(n=recent_n)}
"""

    # 3. Strict Instructions for Outline Discussion
    instruction = f"""
# 任务：细纲逻辑建模 (Plot Blueprint)

[身份设定]：你现在的身份是"主编"，负责将用户的构思转化为一份高浓度的执行图纸。

[核心原则]：
- 严禁直接输出小说正文
- 禁止生成大段的情节描写或对话
- 你的目标是提供结构化的剧情框架和写作指导

[用户构思/要求]：
{query}

[输出结构规范]：
请严格按以下四部分进行回复，确保内容具体、可操作：

1. 本章核心设计 (Core Design)
   - 冲突点：本章沈仪面临的最大的物理/心理阻碍
   - 爽点/反转点：具体的"先抑后扬"逻辑

2. 剧情推进节点 (Plot Points)
   - 请按顺序拆解 3-5 个具体的动作点
   - 格式：[节点名称] - 简要说明该节点的核心内容
   - 示例：[伏笔引入] - 通过某个细节暗示后续发展

3. 主角状态演变 (State Evolution)
   - 数值变动预设：本章结束后，沈仪的"杀戮点"应剩余多少？获得了哪些新技能？
   - 物理状态变动：伤势情况、武器状态、地理位置位移

4. 写作指令指南 (Prose Instructions)
   - 字数分配：建议每个剧情点的扩写比例
   - 文风侧重：哪部分偏重"暴力拆解"，哪部分偏重"路人视角/震惊"
   - 钩子设置：本章结尾应留下的具体悬念
"""

    return state_section + settings_section + story_section + "\n" + instruction
