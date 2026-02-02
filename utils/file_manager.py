import os
import re
import shutil
from typing import List, Tuple
import config

def ensure_directories():
    """Create all required directories if they don't exist."""
    created = []
    for d in config.REQUIRED_DIRS:
        if not os.path.exists(d):
            os.makedirs(d)
            created.append(d)
    return created

def parse_chapters(file_path: str) -> List[Tuple[str, str]]:
    """
    Parse the single body file into chapters.
    Returns a list of (filename, content).
    Format: [第x章{ChapterName}]
    """
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to match chapter headers: [第x章...]
    # We look for [第...章...] at the start of line or file
    # Pattern: ^\[第(.*?)章(.*?)\]
    # But user said: [第x章{章节名}]
    
    # Let's try a robust split.
    # We will split by the pattern, but keep the delimiter.
    
    pattern = r'(\[第.*?章.*?\])'
    parts = re.split(pattern, content)
    
    chapters = []
    current_title = ""
    current_body = []
    
    # parts[0] might be pre-text (intro) if file doesn't start with chapter
    if parts[0].strip():
        # Handle intro if needed, or just ignore if it's empty
        pass

    # The split result will be: [pre, title1, body1, title2, body2, ...]
    # So we iterate starting from index 1 usually, but let's check.
    
    for part in parts:
        if not part:
            continue
            
        if re.match(pattern, part):
            # It is a title
            # Save previous chapter if exists
            if current_title:
                chapters.append((current_title, "".join(current_body).strip()))
            
            # Start new chapter
            # Extract chapter number for sorting/filename
            # Example: [第01章 开端] -> 01
            # Clean the title for filename
            clean_title = part.strip().strip("[]") # 第01章 开端
            current_title = clean_title
            current_body = [part + "\n"] # Include the title in the file content? 
            # Usually individual files might not need the [Title] line if filename has it, 
            # but for consistency with "My Body.txt", keeping it is safer.
            # User requirement: "每章单独写入 正文/ 下（如 正文/第01章 xxx.txt）"
        else:
            # It is body
            if current_title:
                current_body.append(part)
    
    # Append the last chapter
    if current_title:
        chapters.append((current_title, "".join(current_body).strip()))
        
    return chapters

def save_chapters_to_files(chapters: List[Tuple[str, str]], target_dir: str) -> List[str]:
    """
    Save parsed chapters to individual files.
    Returns list of saved file paths.
    """
    saved_files = []
    for title, content in chapters:
        # Sanitize filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{safe_title}.txt"
        file_path = os.path.join(target_dir, filename)
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        saved_files.append(filename)
        
    return saved_files

def check_resources_status():
    """Check which resource files are missing."""
    status = {}
    status["original"] = os.path.exists(config.FILE_ORIGINAL)
    status["sample"] = os.path.exists(config.FILE_SAMPLE)
    status["my_body"] = os.path.exists(config.FILE_MY_BODY)
    return status
