import json
import os
import shutil
import datetime
import uuid
import config

def load_json(file_path, default=None):
    if not os.path.exists(file_path):
        return default if default is not None else []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_foreshadowing():
    return load_json(config.FILE_FORESHADOWING, default=[])

def save_foreshadowing(data):
    save_json(config.FILE_FORESHADOWING, data)

def get_character_state():
    return load_json(config.FILE_CHARACTER_STATE, default={})

def save_character_state(data):
    save_json(config.FILE_CHARACTER_STATE, data)

def create_snapshot(chapter_name):
    """
    Create a snapshot of current state files into History folder.
    Naming: state_{chapter_name}_{timestamp}.json
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Snapshot Foreshadowing
    if os.path.exists(config.FILE_FORESHADOWING):
        dest = os.path.join(config.DIR_HISTORY, f"伏笔_{chapter_name}_{timestamp}.json")
        shutil.copy2(config.FILE_FORESHADOWING, dest)
        
    # Snapshot Character State
    if os.path.exists(config.FILE_CHARACTER_STATE):
        dest = os.path.join(config.DIR_HISTORY, f"角色_{chapter_name}_{timestamp}.json")
        shutil.copy2(config.FILE_CHARACTER_STATE, dest)

def add_foreshadowing(content, chapter, snippet=""):
    data = get_foreshadowing()
    new_item = {
        "id": str(uuid.uuid4()),
        "content": content,
        "chapter_created": chapter,
        "status": "pending",
        "chapter_resolved": None,
        "original_text_snippet": snippet,
        "created_at": datetime.datetime.now().isoformat()
    }
    data.append(new_item)
    save_foreshadowing(data)
    return new_item

def update_character(name, updates, chapter):
    data = get_character_state()
    if name not in data:
        data[name] = {}
    
    # Merge updates
    data[name].update(updates)
    data[name]["last_updated_chapter"] = chapter
    data[name]["updated_at"] = datetime.datetime.now().isoformat()
    
    save_character_state(data)
    return data[name]
