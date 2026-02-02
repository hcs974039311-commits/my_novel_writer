import os

# Project Root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Directory Names
DIR_REF = os.path.join(PROJECT_ROOT, "参考")
DIR_SETTINGS = os.path.join(PROJECT_ROOT, "设定")
DIR_BODY = os.path.join(PROJECT_ROOT, "正文")
DIR_OUTLINES = os.path.join(PROJECT_ROOT, "细纲")
DIR_HISTORY = os.path.join(PROJECT_ROOT, "历史版本") # For conflict detection snapshots
DIR_ASSETS = os.path.join(PROJECT_ROOT, "assets") # 文风素材

# Key Files
FILE_ORIGINAL = os.path.join(DIR_REF, "从斩妖除魔开始长生不死.txt")
FILE_SAMPLE = os.path.join(DIR_REF, "大神素材样本.txt")
FILE_MY_BODY = os.path.join(PROJECT_ROOT, "我的正文.txt")

# State Files (New)
FILE_FORESHADOWING = os.path.join(DIR_SETTINGS, "设定_伏笔.json")
FILE_CHARACTER_STATE = os.path.join(DIR_SETTINGS, "设定_角色状态.json")

# Ensure all directories exist
REQUIRED_DIRS = [DIR_REF, DIR_SETTINGS, DIR_BODY, DIR_OUTLINES, DIR_HISTORY, DIR_ASSETS]
