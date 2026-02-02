import streamlit as st
import os
import glob
import json
from datetime import datetime
import config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils import file_manager, state_manager, context_manager, llm_client, text_analyzer, reference_manager, extractor
from utils import smart_extractor, info_panel

# Page Config
st.set_page_config(
    page_title="镇妖狱创作引擎",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起侧边栏
)

# Custom Global CSS
st.markdown("""
    <style>
    /* 全局背景 */
    .stApp {
        background-color: #0e1117;
    }
    
    /* 统一文字样式 */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 数值高亮 (杀戮点等) */
    .killing-points, .highlight-val {
        color: #2ecc71 !important;
        font-weight: bold;
        text-shadow: 0 0 8px rgba(46, 204, 113, 0.4);
    }
    
    /* 分隔线样式 */
    hr {
        margin: 1rem 0 !important;
        border-color: rgba(139, 0, 0, 0.3) !important;
    }
    
    /* 容器间距优化 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if "messages_settings" not in st.session_state:
    st.session_state.messages_settings = []
if "messages_outline" not in st.session_state:
    st.session_state.messages_outline = []
if "current_chapter_content" not in st.session_state:
    st.session_state.current_chapter_content = ""
if "current_nav_mode" not in st.session_state:
    st.session_state.current_nav_mode = "初始化"

# --- TOP: DASHBOARD ---
info_panel.render_dashboard()

# --- MIDDLE: NAVIGATION ---
nav_options = ["初始化", "探讨设定", "探讨细纲", "续写正文", "改文与冲突提示"]

# 处理外部跳转
if "app_mode_switch" in st.session_state:
    st.session_state.current_nav_mode = st.session_state.pop("app_mode_switch")

# 水平导航
app_mode = st.radio(
    "功能调度导航", 
    nav_options, 
    index=nav_options.index(st.session_state.current_nav_mode), 
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.current_nav_mode = app_mode

st.divider()

# Sidebar (Keep only configuration)
with st.sidebar:
    st.title("⚙️ 系统配置")
    
    # API Configuration Section
    st.subheader("🤖 大模型配置")
    st.info("💡 系统已合并为统一 OpenAI 兼容模式，支持 NewAPI, SiliconFlow, 公司内部平台等。")
    
    # 初始化 session_state 中的配置（如果不存在）
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
    if "model_name" not in st.session_state:
        st.session_state.model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

    # 输入框：Base URL
    base_url = st.text_input(
        "API 接口地址 (Base URL)", 
        value=st.session_state.api_base_url,
        placeholder="https://api.openai.com/v1"
    )
    st.session_state.api_base_url = base_url
    os.environ["OPENAI_BASE_URL"] = base_url
    
    # 输入框：API Key
    api_key = st.text_input(
        "API 密钥 (API Key)", 
        value=st.session_state.api_key,
        type="password"
    )
    st.session_state.api_key = api_key
    os.environ["OPENAI_API_KEY"] = api_key
    
    # 输入框：模型名称
    model_name = st.text_input(
        "使用的模型名称", 
        value=st.session_state.model_name
    )
    st.session_state.model_name = model_name
    st.session_state["DEFAULT_MODEL_NAME"] = model_name
    os.environ["OPENAI_MODEL_NAME"] = model_name

    # Configuration Status
    st.divider()
    if st.session_state.api_key:
        st.success("✅ API 已配置")
        st.caption(f"当前模型: {st.session_state.model_name}")
    else:
        st.warning("⚠️ 请配置 API 密钥")


# ==================== 辅助函数 V2 ====================

def _save_with_style_analysis_v2(chapter_title, final_content, original_content):
    if not chapter_title.endswith(".txt"):
        chapter_title += ".txt"
    save_path = os.path.join(config.DIR_BODY, chapter_title)
    
    # 保存新内容
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    # 执行风格分析
    with st.spinner("正在分析您的写作风格..."):
        try:
            from utils.style_analyzer import StyleAnalyzer, StyleManager
            analyzer = StyleAnalyzer()
            manager = StyleManager()
            scene_type = analyzer.classify_scene(final_content)
            style_features = analyzer.analyze_modifications(original_content, final_content)
            manager.save_style_profile(scene_type, style_features)
            st.success(f"✅ 风格分析完成！已学习您的{scene_type}场景修稿习惯")
        except Exception as e:
            st.warning(f"风格分析失败：{str(e)}")
    
    st.success(f"✅ 章节已保存: {chapter_title}")
    st.session_state.generated_chapter = final_content
    st.session_state.pop("ai_draft", None)
    st.rerun()

def _save_with_full_features_v2(chapter_title, final_content, original_content):
    if not chapter_title.endswith(".txt"):
        chapter_title += ".txt"
    save_path = os.path.join(config.DIR_BODY, chapter_title)
    
    # 保存
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    # 1. 风格分析
    try:
        from utils.style_analyzer import StyleAnalyzer, StyleManager
        analyzer = StyleAnalyzer()
        manager = StyleManager()
        scene_type = analyzer.classify_scene(final_content)
        style_features = analyzer.analyze_modifications(original_content, final_content)
        manager.save_style_profile(scene_type, style_features)
        st.success("✅ 写作风格已更新")
    except: pass
    
    # 2. 状态与设定自动更新
    with st.spinner("正在同步角色状态与世界观设定..."):
        try:
            from utils.setting_updater import analyze_and_update_settings
            analyze_and_update_settings(final_content, chapter_title)
            st.success("✅ 角色状态与设定已同步")
        except Exception as e:
            st.warning(f"自动更新失败: {e}")
            
    st.session_state.generated_chapter = final_content
    st.session_state.pop("ai_draft", None)
    st.rerun()

# --- FUNCTION: INITIALIZATION ---
if app_mode == "初始化":
    st.title("🚀 项目初始化")
    
    col_main, col_chat = st.columns([3, 2])
    
    with col_main:
        st.markdown("### 1. 基础环境与状态文件")
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            if st.button("🛠️ 创建/修复目录结构", use_container_width=True):
                created = file_manager.ensure_directories()
                if created:
                    st.success(f"已创建: {', '.join([os.path.basename(d) for d in created])}")
                else:
                    st.info("目录结构正常。")

        with sub_col2:
            if st.button("📝 初始化空白状态文件", use_container_width=True):
                # Create empty JSONs if not exist
                msg = []
                if not os.path.exists(config.FILE_FORESHADOWING):
                    with open(config.FILE_FORESHADOWING, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    msg.append("设定_伏笔.json")
                if not os.path.exists(config.FILE_CHARACTER_STATE):
                    with open(config.FILE_CHARACTER_STATE, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2) 
                    msg.append("设定_角色状态.json")
                if msg:
                    st.success(f"已创建: {', '.join(msg)}")
                else:
                    st.info("状态文件已存在")
        
        st.divider()
        st.markdown("### 2. 全量状态提取 (AI)")
        st.info("如果您已有正文，点击下方按钮让 AI 阅读全文并自动生成核心状态。")
        
        # 提取模式选择
        extraction_mode = st.radio(
            "选择提取模式：",
            ["标准模式", "智能分段模式（保持上下文）"],
            index=0,
            horizontal=True
        )
        
        # 窗口参数设置
        window_size = 8000
        overlap_size = 1500
        if extraction_mode == "智能分段模式（保持上下文）":
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                window_size = st.slider("窗口大小", 5000, 15000, 8000, 1000)
            with w_col2:
                overlap_size = st.slider("重叠大小", 500, 3000, 1500, 500)
        
        if st.button("🚀 开始全量提取 (消耗 Token)", type="primary", use_container_width=True):
            current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
            full_text = ""
            chapters = context_manager.get_sorted_chapters()
            if chapters:
                for ch_path in chapters:
                    with open(ch_path, 'r', encoding='utf-8') as f:
                        full_text += f.read() + "\n\n"
            elif os.path.exists(config.FILE_MY_BODY):
                with open(config.FILE_MY_BODY, 'r', encoding='utf-8') as f:
                    full_text = f.read()
            else:
                st.error("未找到正文文件！")
                full_text = None
                
            if full_text:
                with st.spinner("AI 正在深度扫描全文..."):
                    try:
                        if extraction_mode == "智能分段模式（保持上下文）":
                            extracted_data = smart_extractor.smart_extract_large_text(
                                full_text, model_name=current_model, 
                                window_size=window_size, overlap=overlap_size
                            )
                        else:
                            extracted_data = extractor.extract_all_from_text(full_text, model_name=current_model)
                        
                        if extracted_data:
                            st.session_state.last_extracted_data = extracted_data
                            extractor.save_extracted_data(extracted_data)
                            st.success("✅ 全量提取并持久化完成！")
                    except Exception as e:
                        st.error(f"提取失败: {e}")

    with col_chat:
        st.markdown("### 📁 资源与导入")
        status = file_manager.check_resources_status()
        def status_tag(exists, name):
            color = "green" if exists else "red"
            icon = "✅" if exists else "❌"
            return f'<span style="color:{color}; font-weight:bold;">{icon} {name}</span>'
            
        st.markdown(f"""
        - {status_tag(status['my_body'], '我的正文.txt')}
        - {status_tag(status['original'], '参考原著')}
        - {status_tag(status['sample'], '大神素材样本')}
        """, unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 📥 章节导入")
        if status['my_body']:
            if st.button("执行单文件正文拆分", use_container_width=True):
                chapters = file_manager.parse_chapters(config.FILE_MY_BODY)
                if chapters:
                    saved_files = file_manager.save_chapters_to_files(chapters, config.DIR_BODY)
                    st.success(f"成功拆分并导入 {len(saved_files)} 章！")
                else:
                    st.warning("解析失败，请检查章节标题格式（如：第x章）。")
        
        if "last_extracted_data" in st.session_state:
            st.markdown("### 📊 最近提取预览")
            st.json(st.session_state.last_extracted_data)

# --- FUNCTION: DISCUSS SETTINGS ---
elif app_mode == "探讨设定":
    st.title("🧠 设定探讨工作台")
    
    # 上方：创作对话
    st.markdown("### 💬 创作对话")
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages_settings:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    if prompt := st.chat_input("输入你的设定想法...", key="setting_chat_input"):
        st.session_state.messages_settings.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    try:
                        full_prompt = context_manager.build_setting_discussion_prompt(f"完善以下设定：{prompt}")
                        current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
                        response = llm_client.generate_content(full_prompt, model_name=current_model)
                        st.markdown(response)
                        st.session_state.messages_settings.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"❌ AI调用失败: {str(e)}")
                        st.info("请检查网络连接或API配置是否正确")
                        print(f"详细错误信息: {str(e)}")
                        import traceback
                        traceback.print_exc()
        st.rerun()
    
    st.divider()
    
    # 下方：设定工作台
    st.info("💡 **工作台**：在此处精修和保存 AI 生成的设定内容。")
    
    # 初始化拆分结果状态
    if "pending_split_results" not in st.session_state:
        st.session_state.pending_split_results = None
    
    # 设定保存区域
    if st.session_state.messages_settings:
        # 检查最后一条消息是否为AI回复
        last_msg = st.session_state.messages_settings[-1]
        if last_msg["role"] != "assistant":
            st.warning("⚠️ 请先与AI进行对话，获得AI生成的设定内容后再进行保存操作")
            st.info("💡 操作流程：1. 在上方对话框输入设定想法 → 2. 等待AI生成回复 → 3. 在下方精修并保存")
        else:
            last_response = last_msg["content"]
            user_input = st.session_state.messages_settings[-2]["content"] if len(st.session_state.messages_settings) >= 2 else "新设定"
            
            st.subheader("📝 设定草稿精修")
            st.info("📄 当前编辑内容来自AI的回复。您可以根据需要修改下方内容，然后点击智能拆分预览。")
            
            # 使用 session_state 保持编辑内容，避免页面刷新丢失
            if "setting_editor_content" not in st.session_state or st.session_state.get("last_ai_resp_id") != id(last_response):
                st.session_state.setting_editor_content = last_response
                st.session_state.last_ai_resp_id = id(last_response)

            edited_setting = st.text_area("内容编辑", value=st.session_state.setting_editor_content, height=300, key="setting_text_area")
            st.session_state.setting_editor_content = edited_setting
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔍 1. 提交AI智能拆分预览", type="primary", use_container_width=True):
                    with st.spinner("AI正在分析并智能拆分内容..."):
                        try:
                            # 强化后的拆分提示词
                            split_prompt = f"""
# 任务：设定内容精确语义拆分

你是一位严谨的小说设定管理专家。请分析以下内容，将其拆分到对应的设定类别中。

[待处理内容（AI生成的建议/精修后的内容）]：
{edited_setting}

[参考背景（用户原始提问）]：
{user_input}

[严格分类规范]：
1. 世界观_地图设定：地理、气候、宏观背景。
2. 人物设定：角色性格、背景、外貌。
3. 势力_组织设定：门派、家族、国家组织。
4. 战力_功法设定：境界划分、功法名称、具体效果。
5. 物品_道具设定：武器、丹药、奇珍异宝。
6. 历史_背景设定：历史事件、古老传说、时代演变。
7. 规则_制度设定：修行逻辑、社会运行法则、硬性限制。
8. 其他特殊设定：无法归入以上类别的其他设定内容。

[禁止事项]：
- 严禁存入用户原始提问的内容。
- 严禁生成小说正文（如：'他拔出刀...'）。
- 严禁修改原文的核心术语。
- 每一段内容只能出现在一个类别中，不要重复。
- 如果某类别无内容，请不要包含该键。

请严格以标准JSON格式返回：
{{
  "类别名": "对应的设定内容"
}}
"""
                            current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
                            ai_response = llm_client.generate_content(split_prompt, model_name=current_model)
                            
                            # 解析 JSON
                            import json
                            json_str = ai_response.strip()
                            if "```json" in json_str:
                                json_str = json_str.split("```json")[1].split("```")[0].strip()
                            elif "```" in json_str:
                                json_str = json_str.split("```")[1].split("```")[0].strip()
                            
                            st.session_state.pending_split_results = json.loads(json_str)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ AI拆分失败：{str(e)}")
                            st.session_state.pending_split_results = None

            with col2:
                if st.button("🗑️ 清空预览/草稿", use_container_width=True):
                    st.session_state.pending_split_results = None
                    st.rerun()

            # 拆分结果预览与最终确认
            if st.session_state.pending_split_results:
                st.markdown("### 📋 拆分预览确认")
                st.info("👇 请核对 AI 的分类是否准确。确认无误后点击下方按钮正式存入设定库。")
                
                for cat, content in st.session_state.pending_split_results.items():
                    with st.expander(f"📁 归类至：{cat}", expanded=True):
                        st.write(content)
                
                if st.button("✅ 2. 确认无误，正式存入设定库", type="primary", use_container_width=True):
                    try:
                        os.makedirs(config.DIR_SETTINGS, exist_ok=True)
                        saved_files = []
                        for category, content in st.session_state.pending_split_results.items():
                            if content and content.strip():
                                filename = f"设定_{category}.txt"
                                filepath = os.path.join(config.DIR_SETTINGS, filename)
                                
                                # 原子化写入逻辑：追加模式
                                with open(filepath, 'a', encoding='utf-8') as f:
                                    f.write(f"\n=== 更新于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                                    f.write(f"{content}\n")
                                saved_files.append(filename)
                        
                        st.success(f"✨ 成功存入以下文件：{', '.join(saved_files)}")
                        st.session_state.pending_split_results = None # 清空状态
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ 最终保存失败：{str(e)}")
    else:
        st.warning("暂无生成内容，请在上方与 AI 探讨。")


# --- FUNCTION: DISCUSS OUTLINE ---
elif app_mode == "探讨细纲":
    st.title("📝 细纲逻辑建模")
    
    # 上方：逻辑建模对话
    st.markdown("### 💬 逻辑建模对话")
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages_outline:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
    if prompt := st.chat_input("输入剧情构思...", key="outline_chat_input"):
        st.session_state.messages_outline.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("主编建模中..."):
                    try:
                        full_prompt = context_manager.build_outline_discussion_prompt(prompt)
                        current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
                        response = llm_client.generate_content(full_prompt, model_name=current_model)
                        st.markdown(response)
                        st.session_state.messages_outline.append({"role": "assistant", "content": response})
                        st.session_state.current_blueprint = response
                    except Exception as e:
                        st.error(f"❌ AI调用失败: {str(e)}")
                        st.info("请检查网络连接或API配置是否正确")
                        print(f"详细错误信息: {str(e)}")
                        import traceback
                        traceback.print_exc()
        st.rerun()
    
    st.divider()
    
    # 下方：细纲精修工作台
    st.info("🎭 **身份：主编** | 任务：将构思转化为高浓度执行图纸。")
    
    # 细纲编辑区
    if "current_blueprint" not in st.session_state:
        st.session_state.current_blueprint = ""
        
    st.subheader("🛠️ 细纲精修")
    edited_blueprint = st.text_area("执行图纸编辑器", value=st.session_state.current_blueprint, height=300)
    st.session_state.current_blueprint = edited_blueprint
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 仅保存细纲", use_container_width=True):
            os.makedirs(config.DIR_OUTLINES, exist_ok=True)
            with open(os.path.join(config.DIR_OUTLINES, "当前细纲.txt"), 'w', encoding='utf-8') as f:
                f.write(edited_blueprint)
            st.success("细纲已保存")
    with c2:
        if st.button("🚀 确认并前往续写", type="primary", use_container_width=True):
            os.makedirs(config.DIR_OUTLINES, exist_ok=True)
            with open(os.path.join(config.DIR_OUTLINES, "当前细纲.txt"), 'w', encoding='utf-8') as f:
                f.write(edited_blueprint)
            st.session_state["app_mode_switch"] = "续写正文"
            st.rerun()

# --- FUNCTION: WRITE BODY ---
elif app_mode == "续写正文":
    st.title("✍️ 续写正文工作台")
    col_main, col_chat = st.columns([3, 2])
    
    with col_main:
        # 加载细纲
        outline_path = os.path.join(config.DIR_OUTLINES, "当前细纲.txt")
        outline_content = ""
        if os.path.exists(outline_path):
            with open(outline_path, 'r', encoding='utf-8') as f:
                outline_content = f.read()
        
        st.subheader("📜 当前参考细纲")
        user_outline = st.text_area("细纲内容 (可实时调整)", outline_content, height=200)
        
        if st.button("🚀 开始生成正文", type="primary", use_container_width=True):
            with st.spinner("极道流文风注入中，正在撰写..."):
                # 自动加载文风
                full_prompt = context_manager.build_context_prompt(
                    f"请根据以下细纲续写小说正文，严格模仿文风素材：\n\n{user_outline}",
                    include_style=True
                )
                current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
                generated_text = llm_client.generate_content(full_prompt, model_name=current_model)
                st.session_state.generated_chapter = generated_text
                st.session_state.ai_draft = generated_text  # 新增：锁定原始草稿作为风格对比基准
                st.rerun()

        if 'generated_chapter' in st.session_state:
            st.subheader("🖋️ 正文精修")
            # 注意：此处不直接同步回 generated_chapter，直到点击保存
            final_content = st.text_area("正文编辑器", st.session_state.generated_chapter, height=500)
            
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                chapter_title = st.text_input("章节文件名", placeholder="第x章 激战.txt")
            with c2:
                if st.button("💾 仅保存章节", use_container_width=True):
                    if chapter_title:
                        if not chapter_title.endswith(".txt"): chapter_title += ".txt"
                        save_path = os.path.join(config.DIR_BODY, chapter_title)
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        st.session_state.generated_chapter = final_content # 保存时更新状态
                        st.success(f"✅ 章节已保存: {chapter_title}")
                    else:
                        st.error("请输入文件名")
            with c3:
                if st.button("💾 保存并分析风格", use_container_width=True):
                    if chapter_title:
                        # 使用 ai_draft 进行对比
                        original = st.session_state.get("ai_draft", final_content)
                        _save_with_style_analysis_v2(chapter_title, final_content, original)
                    else:
                        st.error("请输入文件名")
            with c4:
                if st.button("💾 全部功能", type="primary", use_container_width=True):
                    if chapter_title:
                        original = st.session_state.get("ai_draft", final_content)
                        _save_with_full_features_v2(chapter_title, final_content, original)
                    else:
                        st.error("请输入文件名")

    with col_chat:
        st.markdown("### 🧠 写作辅助")
        with st.expander("📝 细纲要点回顾", expanded=True):
            st.markdown(user_outline)
        
        with st.expander("🎨 文风自动指纹", expanded=False):
            style_info = context_manager.auto_style_loader()
            if style_info:
                st.markdown(style_info)
            else:
                st.info("assets/ 文件夹下未检测到文风素材。")

# --- FUNCTION: MODIFY & CONFLICT ---
elif app_mode == "改文与冲突提示":
    st.title("🔍 改文与冲突审计")
    col_main, col_chat = st.columns([3, 2])
    
    with col_main:
        files = context_manager.get_sorted_chapters()
        file_names = [os.path.basename(f) for f in files]
        
        if not file_names:
            st.warning("暂无正文章节。")
        else:
            selected_file = st.selectbox("选择要审计的章节", file_names)
            file_path = os.path.join(config.DIR_BODY, selected_file)
            
            if 'current_editing_file' not in st.session_state or st.session_state.current_editing_file != selected_file:
                with open(file_path, 'r', encoding='utf-8') as f:
                    st.session_state.current_content = f.read()
                st.session_state.original_content = st.session_state.current_content
                st.session_state.current_editing_file = selected_file
            
            new_content = st.text_area("正文审计编辑器", st.session_state.current_content, height=600)
            
            if st.button("💾 保存并执行冲突扫描", type="primary", use_container_width=True):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                removed_terms = text_analyzer.get_text_diff(st.session_state.original_content, new_content)
                removed_terms = [t.strip() for t in removed_terms if len(t.strip()) > 1]
                
                st.session_state.audit_results = {
                    "removed": removed_terms,
                    "conflicts": text_analyzer.scan_chapters_for_conflict(removed_terms, file_names.index(selected_file), files) if removed_terms else {}
                }
                st.session_state.current_content = new_content
                st.session_state.original_content = new_content
                st.rerun()

    with col_chat:
        st.markdown("### ⚠️ 冲突审计报告")
        if "audit_results" in st.session_state:
            res = st.session_state.audit_results
            if res["removed"]:
                st.warning(f"检测到关键删改: {', '.join(res['removed'])}")
                if res["conflicts"]:
                    st.error("发现潜在因果冲突：")
                    for fname, terms in res["conflicts"].items():
                        st.markdown(f"- **{fname}**: 涉及 `{', '.join(terms)}`")
                else:
                    st.success("后续章节未发现文本层面的直接冲突。")
            else:
                st.info("未检测到显著的关键词删除。")
        else:
            st.info("请在左侧点击保存并执行审计。")
        
        st.divider()
        if st.button("🤖 AI 深度分析本章伏笔变动", use_container_width=True):
            if 'current_content' in st.session_state:
                with st.spinner("正在分析因果链..."):
                    # 简化分析逻辑
                    prompt = f"分析此章节对伏笔和状态的影响：\n\n{st.session_state.current_content[:5000]}"
                    current_model = st.session_state.get("DEFAULT_MODEL_NAME", None)
                    analysis = llm_client.generate_content(prompt, model_name=current_model)
                    st.markdown(analysis)