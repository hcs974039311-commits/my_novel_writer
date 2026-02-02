import json
import os
import glob
import re
import config
from utils import state_manager, context_manager

def load_character_state():
    """加载并格式化角色状态信息"""
    try:
        char_state = state_manager.get_character_state()
        return char_state if char_state else {}
    except Exception as e:
        print(f"加载角色状态失败: {e}")
        return {}

def load_active_foreshadowing():
    """加载活跃伏笔信息（状态为pending的伏笔）"""
    try:
        all_foreshadowing = state_manager.get_foreshadowing()
        active_foreshadowing = [f for f in all_foreshadowing if f.get('status') == 'pending']
        return active_foreshadowing if active_foreshadowing else []
    except Exception as e:
        print(f"加载活跃伏笔失败: {e}")
        return []

def load_setting_files():
    """加载所有设定文件内容"""
    try:
        settings_content = {}
        setting_files = glob.glob(os.path.join(config.DIR_SETTINGS, "设定_*.txt"))
        
        for file_path in setting_files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # 只添加非空内容
                        settings_content[filename] = content
            except Exception as e:
                print(f"读取设定文件 {filename} 失败: {e}")
                
        return settings_content
    except Exception as e:
        print(f"加载设定文件失败: {e}")
        return {}

def get_recent_chapters_summary(n=5):
    """获取最近章节的简要内容"""
    try:
        files = context_manager.get_sorted_chapters()
        recent_files = files[-n:] if len(files) >= n else files
        
        summary = []
        for file_path in recent_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取章节标题和简要内容
                    filename = os.path.basename(file_path)
                    # 获取前200字符作为概要
                    preview = content[:200] + "..." if len(content) > 200 else content
                    summary.append({
                        "title": filename,
                        "preview": preview
                    })
            except Exception as e:
                print(f"读取章节 {file_path} 失败: {e}")
                
        return summary
    except Exception as e:
        print(f"获取章节回顾失败: {e}")
        return []

def highlight_important_text(text, highlight_keywords=None):
    """根据关键词高亮显示重要文本"""
    if not text:
        return text
    
    # 默认高亮关键词
    if highlight_keywords is None:
        highlight_keywords = [
            # 角色状态相关
            '伤', '血', '重伤', '虚弱', '昏迷', '濒死',
            # 伏笔相关
            '紧急', '重要', '必须', '关键', '危机',
            # 数值相关
            r'\d+(?:品|级|层)',  # 品级数字
            r'[一二三四五六七八九十]+品',  # 中文品级
        ]
    
    highlighted_text = str(text)
    
    # 应用高亮
    for keyword in highlight_keywords:
        if isinstance(keyword, str):
            # 普通字符串匹配
            pattern = re.escape(keyword)
        else:
            # 正则表达式
            pattern = keyword
            
        highlighted_text = re.sub(
            pattern, 
            r'**\g<0>**',  # 使用markdown粗体标记
            highlighted_text,
            flags=re.IGNORECASE
        )
    
    return highlighted_text

def format_character_state_for_display(char_state):
    """格式化角色状态用于显示，兼容新旧结构"""
    if not char_state:
        return "暂无角色状态信息"
    
    formatted_lines = []
    for char_name, char_info in char_state.items():
        # 沈仪的特殊处理
        if char_name == "沈仪":
            formatted_lines.append(f"### {char_name}")
            
            # 基础信息
            if "realm" in char_info:
                formatted_lines.append(f"- **境界**: {char_info['realm']}")
            
            if "assets" in char_info:
                assets = char_info["assets"]
                if "killing_points" in assets:
                    formatted_lines.append(f"- **杀戮点**: `{assets['killing_points']}`")
                if "monster_cores" in assets:
                    formatted_lines.append(f"- **妖丹**: `{assets['monster_cores']}`")
            
            if "basic_info" in char_info:
                bi = char_info["basic_info"]
                if "current_status" in bi:
                    status_text = highlight_important_text(bi['current_status'])
                    formatted_lines.append(f"- **状态**: {status_text}")
            
            # 装备
            equipment = char_info.get("equipment", [])
            if equipment:
                formatted_lines.append(f"- **装备**: {highlight_important_text(', '.join(equipment))}")
            
            # 修炼
            if "cultivation" in char_info:
                cult = char_info["cultivation"]
                core = cult.get("core_manual", {})
                if core.get("name"):
                    formatted_lines.append(f"- **核心功法**: {core.get('name')} ({core.get('level', '初学')})")
                    if core.get("features"):
                        formatted_lines.append(f"  - *特性*: {core.get('features')}")
                
                skills = cult.get("martial_skills", [])
                if skills:
                    skill_list = []
                    for s in skills:
                        if isinstance(s, dict):
                            name = s.get('name', '未知')
                            level = s.get('level', '')
                            skill_list.append(f"{name}({level})" if level else name)
                        else:
                            skill_list.append(str(s))
                    formatted_lines.append(f"- **主动武技**: {', '.join(skill_list)}")
                
                talents = cult.get("physical_talents", [])
                if talents:
                    talent_list = []
                    for t in talents:
                        if isinstance(t, dict):
                            name = t.get('name', '未知')
                            effect = t.get('effect', '')
                            talent_list.append(f"{name}（{effect}）" if effect else name)
                        else:
                            talent_list.append(str(t))
                    formatted_lines.append(f"- **肉身天赋**: {highlight_important_text(', '.join(talent_list))}")
        
        # 敌人追踪
        elif char_name.startswith("敌人_"):
            enemy_name = char_name.replace("敌人_", "")
            formatted_lines.append(f"### 👾 敌人: {enemy_name}")
            formatted_lines.append(f"- **身份**: {char_info.get('identity', '未知')}")
            formatted_lines.append(f"- **境界**: {char_info.get('realm', '未知')}")
            formatted_lines.append(f"- **状态**: {char_info.get('status', '未知')}")
            formatted_lines.append(f"- **威胁**: **{char_info.get('threat_level', '未知')}**")
            
        # 世界/势力事件
        elif char_name.startswith("势力_"):
            entity_name = char_name.replace("势力_", "")
            formatted_lines.append(f"### 🌍 势力: {entity_name}")
            formatted_lines.append(f"- **动向**: {char_info.get('current_action', '未知')}")
            formatted_lines.append(f"- **实力**: {char_info.get('threat_origin', '未知')}")
            
        else:
            # 旧版或其他角色通用结构
            formatted_lines.append(f"### {char_name}")
            if 'status' in char_info:
                status_text = highlight_important_text(char_info['status'])
                formatted_lines.append(f"- **状态**: {status_text}")
            
            if 'equipment' in char_info:
                equipment_text = highlight_important_text(char_info['equipment'])
                formatted_lines.append(f"- **装备**: {equipment_text}")
            
            if 'abilities' in char_info:
                abilities_text = highlight_important_text(char_info['abilities'])
                formatted_lines.append(f"- **能力**: {abilities_text}")
        
        formatted_lines.append("")  # 空行分隔
    
    return "\n".join(formatted_lines)

def format_foreshadowing_for_display(foreshadowing_list):
    """格式化伏笔信息用于显示"""
    if not foreshadowing_list:
        return "暂无活跃伏笔"
    
    formatted_lines = []
    for i, foreshadowing in enumerate(foreshadowing_list, 1):
        content = highlight_important_text(foreshadowing.get('content', ''))
        chapter = foreshadowing.get('chapter_created', '未知章节')
        created_at = foreshadowing.get('created_at', '')[:10] if foreshadowing.get('created_at') else '未知时间'
        
        formatted_lines.append(f"**{i}. {content}**")
        formatted_lines.append(f"   - 章节: {chapter}")
        formatted_lines.append(f"   - 创建时间: {created_at}")
        formatted_lines.append("")
    
    return "\n".join(formatted_lines)

def format_settings_summary_for_display(settings_content):
    """格式化设定摘要用于显示"""
    if not settings_content:
        return "暂无设定信息"
    
    formatted_lines = []
    for filename, content in settings_content.items():
        # 提取文件名中的类型信息
        setting_type = filename.replace('设定_', '').replace('.txt', '')
        formatted_lines.append(f"### {setting_type}")
        
        # 如果内容很长，只显示前300字符
        preview_content = content[:300] + "..." if len(content) > 300 else content
        highlighted_content = highlight_important_text(preview_content)
        formatted_lines.append(highlighted_content)
        formatted_lines.append("")
    
    return "\n".join(formatted_lines)

def format_chapter_summary_for_display(chapter_summary):
    """格式化章节回顾用于显示"""
    if not chapter_summary:
        return "暂无章节回顾"
    
    formatted_lines = []
    for chapter in chapter_summary:
        title = chapter.get('title', '未知章节')
        preview = chapter.get('preview', '')
        
        formatted_lines.append(f"### {title}")
        formatted_lines.append(preview)
        formatted_lines.append("")
    
    return "\n".join(formatted_lines)

def render_info_panel(panel_type="setting"):
    """渲染信息面板的主要函数"""
    import streamlit as st
    
    # 创建左侧信息面板
    with st.container():
        st.markdown("### 📋 创作信息面板")
        
        # 角色状态面板
        with st.expander("👤 当前人物状态", expanded=True):
            char_state = load_character_state()
            formatted_state = format_character_state_for_display(char_state)
            st.markdown(formatted_state)
        
        # 活跃伏笔面板
        with st.expander("📝 活跃伏笔", expanded=True):
            active_foreshadowing = load_active_foreshadowing()
            formatted_foreshadowing = format_foreshadowing_for_display(active_foreshadowing)
            st.markdown(formatted_foreshadowing)
        
        # 根据面板类型显示不同内容
        if panel_type == "setting":
            # 设定探讨面板 - 已确定设定
            with st.expander("📚 已确定设定", expanded=False):
                settings_content = load_setting_files()
                formatted_settings = format_settings_summary_for_display(settings_content)
                st.markdown(formatted_settings)
        elif panel_type == "outline":
            # 细纲探讨面板 - 剧情回顾和设定摘要
            with st.expander("📖 最近剧情回顾", expanded=False):
                chapter_summary = get_recent_chapters_summary(n=5)
                formatted_chapters = format_chapter_summary_for_display(chapter_summary)
                st.markdown(formatted_chapters)
            
            with st.expander("📚 相关设定摘要", expanded=False):
                settings_content = load_setting_files()
                formatted_settings = format_settings_summary_for_display(settings_content)
                st.markdown(formatted_settings)
        
        # 刷新按钮
        if st.button("🔄 刷新信息", key=f"refresh_{panel_type}"):
            st.rerun()

def render_dashboard():
    """
    顶部信息看板渲染 (卡片式布局)
    """
    import streamlit as st
    char_state = load_character_state()
    foreshadowing = load_active_foreshadowing()
    
    # 沈仪核心数据
    shen_yi = char_state.get("沈仪", {})
    realm = shen_yi.get("realm", "未知")
    
    assets = shen_yi.get("assets", {})
    killing_points = assets.get("killing_points", 0)
    monster_cores = assets.get("monster_cores", 0)
    
    bi = shen_yi.get("basic_info", {})
    current_status = bi.get("current_status", "正常")
    
    # 武学装备
    cultivation = shen_yi.get("cultivation", {})
    core = cultivation.get("core_manual", {}).get("name", "无")
    martial_skills = cultivation.get("martial_skills", [])
    skills_list = [s.get("name") if isinstance(s, dict) else str(s) for s in martial_skills[:2]]
    skills_str = ", ".join(skills_list) if skills_list else "无"
    
    equipment = shen_yi.get("equipment", [])
    weapon = equipment[0] if equipment else "赤手空拳"
    
    # 伏笔
    fs_list = [f.get('content', '')[:15] + "..." for f in foreshadowing[:3]]
    fs_display = "<br>".join([f"· {s}" for s in fs_list]) if fs_list else "暂无活跃伏笔"
    
    # 强敌
    enemies = [name.replace("敌人_", "") for name in char_state.keys() if name.startswith("敌人_")]
    enemy_str = ", ".join(enemies) if enemies else "暂无已知威胁"

    # CSS 样式
    st.markdown("""
        <style>
        .dashboard-card {
            background-color: rgba(30, 30, 30, 0.8) !important;
            border: 1px solid rgba(150, 0, 0, 0.4) !important;
            border-radius: 8px;
            padding: 12px;
            min-height: 120px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, border-color 0.2s;
        }
        .dashboard-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 0, 0, 0.8) !important;
            box-shadow: 0 0 15px rgba(200, 0, 0, 0.4) !important;
        }
        .card-title {
            color: #cc0000;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid rgba(150, 0, 0, 0.2);
            padding-bottom: 4px;
        }
        .card-content {
            font-size: 0.95rem;
            line-height: 1.4;
            color: #e0e0e0;
        }
        .highlight-val {
            color: #2ecc71;
            font-weight: 700;
            font-family: 'Courier New', Courier, monospace;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'''
            <div class="dashboard-card">
                <div class="card-title">👤 沈仪状态</div>
                <div class="card-content">
                    <b>境界:</b> {realm}<br>
                    <b>资产:</b> <span class="highlight-val">{killing_points}</span> 点 / <span class="highlight-val">{monster_cores}</span> 丹<br>
                    <b>状态:</b> {current_status}
                </div>
            </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
            <div class="dashboard-card">
                <div class="card-title">⚔️ 武学装备</div>
                <div class="card-content">
                    <b>功法:</b> {core}<br>
                    <b>武技:</b> {skills_str}<br>
                    <b>武器:</b> {weapon}
                </div>
            </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
            <div class="dashboard-card">
                <div class="card-title">📝 伏笔账本</div>
                <div class="card-content" style="font-size: 0.85rem;">
                    {fs_display}
                </div>
            </div>
        ''', unsafe_allow_html=True)

    with col4:
        st.markdown(f'''
            <div class="dashboard-card">
                <div class="card-title">👾 强敌追踪</div>
                <div class="card-content">
                    <b>已知威胁:</b> {enemy_str}
                </div>
            </div>
        ''', unsafe_allow_html=True)

# 便捷函数
def render_setting_info_panel():
    """渲染设定探讨信息面板"""
    render_info_panel("setting")

def render_outline_info_panel():
    """渲染细纲探讨信息面板"""
    render_info_panel("outline")