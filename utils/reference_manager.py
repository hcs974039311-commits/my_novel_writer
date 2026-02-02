import re
import os
import config

def parse_sample_file():
    """
    Parse '大神素材样本.txt'.
    Format: [出自哪一章]：ChapterName【原文查找指引：搜索关键词"Keyword"及ChapterName】
    Returns list of dicts.
    """
    if not os.path.exists(config.FILE_SAMPLE):
        return []

    with open(config.FILE_SAMPLE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find blocks. The format seems line-based or block-based.
    # Assuming one entry per line or block.
    # Let's iterate lines.
    entries = []
    lines = content.split('\n')
    
    for line in lines:
        if '【原文查找指引：' in line:
            try:
                # Extract Chapter
                # Example: [出自哪一章]：第二百一十二章 战利品...
                # Simple extraction: find string between ： and 【
                start_idx = line.find('：')
                end_idx = line.find('【')
                if start_idx != -1 and end_idx != -1:
                    chapter_part = line[start_idx+1:end_idx].strip()
                    
                    # Extract Keyword
                    # ...搜索关键词"堆积如山的灵石"...
                    # Regex for keyword
                    kw_match = re.search(r'搜索关键词["“](.*?)["”]', line)
                    keyword = kw_match.group(1) if kw_match else ""
                    
                    entries.append({
                        "chapter_hint": chapter_part,
                        "keyword": keyword,
                        "raw_line": line
                    })
            except Exception:
                continue
    return entries

def find_original_segment(chapter_hint, keyword):
    """
    Find the segment in '从斩妖除魔开始长生不死.txt'.
    1. Find the chapter in the file.
    2. Find the keyword in that chapter.
    3. Return surrounding text.
    """
    if not os.path.exists(config.FILE_ORIGINAL):
        return "原著文件不存在"

    # Optimization: If file is huge, caching chapter offsets would be better.
    # For now, read full text.
    with open(config.FILE_ORIGINAL, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 1. Find Chapter
    # chapter_hint might be "第二百一十二章" or "212"
    # Try to find the chapter header.
    # Assuming headers are like "第xxx章" or just Chinese numbers.
    # If hint contains "第二百一十二章", search for that.
    
    chapter_start = full_text.find(chapter_hint)
    if chapter_start == -1:
        # Try fuzzy match or simplified
        return f"未找到章节: {chapter_hint}"

    # Find next chapter to bound the search
    # This is tricky without strict format. 
    # Let's just search forward from chapter_start for the keyword.
    
    # Limit search scope to e.g. 20000 chars after chapter start
    search_window = full_text[chapter_start : chapter_start + 20000]
    
    if not keyword:
        return search_window[:2000] + "..." # Return start of chapter if no keyword

    kw_pos = search_window.find(keyword)
    if kw_pos == -1:
        return f"在章节 {chapter_hint} 中未找到关键词: {keyword}"

    # Return surrounding text (e.g. 500 chars before and after)
    start = max(0, kw_pos - 500)
    end = min(len(search_window), kw_pos + 1000)
    
    return search_window[start:end]
