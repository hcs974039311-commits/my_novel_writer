"""
风格分析工具模块
用于分析用户修改内容，提取个性化写作风格特征
"""

import difflib
import re
import os
import sys
from collections import defaultdict

# 确保能导入 config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class StyleAnalyzer:
    def __init__(self):
        # 定义场景分类关键词
        self.scene_categories = {
            'combat': ['战斗', '厮杀', '对决', '交手', '搏斗', '激战', '砍杀'],
            'dialogue': ['对话', '交谈', '商议', '谈判', '说话', '聊天'],
            'exploration': ['探索', '寻觅', '调查', '勘察', '搜查', '巡视'],
            'emotional': ['情感', '内心', '思绪', '心境', '心情', '感情'],
            'daily_life': ['日常', '生活', '琐事', '平常', '吃饭', '休息'],
            'narrative': ['叙述', '描述', '介绍', '说明']  # 默认分类
        }
        
        # AI味检测模式
        self.ai_patterns = [
            r'如.*?般',
            r'像.*?一样', 
            r'仿佛.*?',
            r'好似.*?',
            r'犹如.*?',
            r'宛如.*?'
        ]
    
    def classify_scene(self, content):
        """根据内容识别场景类型"""
        content_lower = content.lower()
        
        # 统计各类关键词出现次数
        scores = {}
        for category, keywords in self.scene_categories.items():
            score = sum(content_lower.count(keyword) for keyword in keywords)
            scores[category] = score
        
        # 返回得分最高的类别
        if max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]
        return 'narrative'  # 默认叙事类
    
    def analyze_modifications(self, original_text, modified_text):
        """分析用户修改内容，提取风格特征"""
        if not original_text or not modified_text:
            return {}
        
        features = {
            'ai_metaphor_removed': 0,      # 移除的AI味比喻数量
            'dialogue_added': 0,           # 增加的对话内容
            'action_detail_added': 0,      # 增加的动作细节
            'description_reduced': 0,      # 减少的描述性内容
            'sentence_simplified': 0,      # 简化的句子结构
            'direct_expression_added': 0,  # 增加的直接表达
            'structural_change': 0         # 基础结构变动（兜底）
        }
        
        # 分析差异
        diff_lines = list(difflib.unified_diff(
            original_text.splitlines(),
            modified_text.splitlines(),
            lineterm=''
        ))
        
        if not diff_lines:
            return {}
            
        # 统计各类修改
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):  # 新增内容
                added_content = line[1:].strip()
                if not added_content: continue
                
                features['structural_change'] += len(added_content)
                features['ai_metaphor_removed'] += self._count_ai_patterns_removed(added_content, original_text)
                features['dialogue_added'] += self._count_dialogue_added(added_content)
                features['action_detail_added'] += self._count_action_details(added_content)
                features['direct_expression_added'] += self._count_direct_expressions(added_content)
            
            elif line.startswith('-') and not line.startswith('---'):  # 删除内容
                removed_content = line[1:].strip()
                if not removed_content: continue
                
                features['structural_change'] += len(removed_content)
                features['description_reduced'] += self._count_description_removed(removed_content, modified_text)
                features['sentence_simplified'] += self._count_sentence_simplification(removed_content, modified_text)
        
        # 归一化特征值
        # 我们保留原始计数和归一化值，但在存档时为了后续推荐，归一化是有意义的
        total_score = sum(abs(v) for k, v in features.items() if k != 'structural_change')
        
        if total_score > 0:
            normalized_features = {k: v/total_score for k, v in features.items() if k != 'structural_change'}
            normalized_features['structural_intensity'] = features['structural_change'] / max(len(original_text), 1)
        else:
            # 如果没有匹配到特定模式，但有结构变动
            normalized_features = {k: 0.0 for k in features.keys() if k != 'structural_change'}
            normalized_features['structural_intensity'] = features['structural_change'] / max(len(original_text), 1)
            
        return normalized_features
    
    def _count_ai_patterns_removed(self, new_content, original_content):
        """统计移除的AI味比喻模式"""
        count = 0
        for pattern in self.ai_patterns:
            # 如果新模式中没有这些模式，但在原文中有，则说明被移除了
            if not re.search(pattern, new_content) and re.search(pattern, original_content):
                count += 1
        return count
    
    def _count_dialogue_added(self, content):
        """统计新增的对话内容"""
        # 检测引号、冒号等对话标志
        dialogue_indicators = ['"', '"', '：', '说', '道', '问']
        return sum(content.count(indicator) for indicator in dialogue_indicators)
    
    def _count_action_details(self, content):
        """统计动作细节描述"""
        action_verbs = ['挥', '砍', '刺', '劈', '踢', ' punch', '抓', '握', '拉', '推']
        return sum(content.count(verb) for verb in action_verbs)
    
    def _count_description_removed(self, removed_content, new_content):
        """统计被删除的描述性内容"""
        descriptive_words = ['美丽', '漂亮', '壮观', '宏伟', '精致', '细腻', '柔和']
        return sum(removed_content.count(word) for word in descriptive_words)
    
    def _count_sentence_simplification(self, removed_content, new_content):
        """检测句子简化"""
        # 通过句子长度变化来判断
        old_sentences = len(removed_content.split('。'))
        new_sentences = len(new_content.split('。'))
        return 1 if old_sentences > new_sentences and old_sentences > 0 else 0
    
    def _count_direct_expressions(self, content):
        """统计直接表达方式"""
        direct_patterns = [
            r'[^\s]+了一声',  # "说道"、"喊道"等
            r'[^\s]+道',      # 直接的表述
            r'直接[^\s]+',    # "直接攻击"等
        ]
        count = 0
        for pattern in direct_patterns:
            count += len(re.findall(pattern, content))
        return count
    
    def summarize_changes(self, features):
        """总结风格变化"""
        summaries = []
        
        if features.get('ai_metaphor_removed', 0) > 0.3:
            summaries.append("减少了模板化比喻")
        if features.get('dialogue_added', 0) > 0.3:
            summaries.append("增加了对话比重")
        if features.get('action_detail_added', 0) > 0.3:
            summaries.append("丰富了动作细节")
        if features.get('description_reduced', 0) > 0.3:
            summaries.append("简化了描述内容")
        if features.get('direct_expression_added', 0) > 0.3:
            summaries.append("采用了更直接的表达")
            
        return "，".join(summaries) if summaries else "保持了原有风格"

# 风格管理器
class StyleManager:
    def __init__(self, style_file_path=None):
        import config
        if style_file_path is None:
            self.style_file = os.path.join(config.DIR_SETTINGS, "用户风格档案.json")
        else:
            self.style_file = style_file_path
        self.styles = self._load_styles()
    
    def _load_styles(self):
        """加载现有风格档案"""
        import os
        import json
        if os.path.exists(self.style_file):
            try:
                with open(self.style_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_style_profile(self, scene_type, features):
        """保存风格特征到档案"""
        import json
        import os
        
        if scene_type not in self.styles:
            self.styles[scene_type] = []
        
        # 添加时间戳
        import datetime
        features['timestamp'] = datetime.datetime.now().isoformat()
        self.styles[scene_type].append(features)
        
        # 只保留最近20次记录
        if len(self.styles[scene_type]) > 20:
            self.styles[scene_type] = self.styles[scene_type][-20:]
        
        # 保存到文件
        os.makedirs(os.path.dirname(self.style_file), exist_ok=True)
        try:
            with open(self.style_file, 'w', encoding='utf-8') as f:
                json.dump(self.styles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存风格档案失败: {e}")
    
    def get_style_recommendation(self, scene_type):
        """获取特定场景的风格推荐"""
        if scene_type in self.styles and self.styles[scene_type]:
            # 计算该场景类型的平均风格特征
            recent_styles = self.styles[scene_type][-5:]  # 取最近5次修改
            return self._calculate_average(recent_styles)
        return {}
    
    def _calculate_average(self, style_list):
        """计算风格特征平均值"""
        if not style_list:
            return {}
        
        # 获取所有键
        all_keys = set()
        for style in style_list:
            all_keys.update(k for k in style.keys() if k != 'timestamp')
        
        avg = {}
        for key in all_keys:
            values = [item.get(key, 0) for item in style_list]
            avg[key] = sum(values) / len(values)
        return avg
    
    def get_all_scene_types(self):
        """获取所有已记录的场景类型"""
        return list(self.styles.keys())

if __name__ == "__main__":
    # 测试代码
    analyzer = StyleAnalyzer()
    manager = StyleManager()
    
    # 测试场景分类
    test_content = "沈仪挥刀斩向敌人，刀光如闪电般掠过"
    scene = analyzer.classify_scene(test_content)
    print(f"场景分类: {scene}")
    
    # 测试风格分析
    original = "他如猛虎般扑向对手"
    modified = "他猛地扑向对手"
    features = analyzer.analyze_modifications(original, modified)
    print(f"风格特征: {features}")
    print(f"变化总结: {analyzer.summarize_changes(features)}")