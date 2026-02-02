import difflib
import re
import os
import glob
from typing import List, Dict, Tuple

def get_text_diff(old_text, new_text):
    """
    Compare old and new text.
    Return a list of changed terms/sentences?
    For simple "A->B" replacement detection, we might need a more semantic approach or just simple diff.
    
    If we use standard difflib, we get line-by-line diff.
    User example: "Protagonist name A -> B".
    """
    # Simple approach: Find unique words present in Old but missing in New (with frequency change)
    # This is hard to do perfectly with simple code.
    # Let's stick to what the user asked: "Capture difference (Name A->B, Deleted sentence)".
    
    # For the MVP, let's return the diff object and let the UI/LLM handle analysis,
    # OR we implement a simple "Keywords lost" detector.
    
    # Actually, the user says: "Use the difference... to scan subsequent chapters."
    # If I just delete a sentence, I should scan if that sentence was referenced? No, that's hard.
    # "If name A -> B, scan for A".
    
    # Let's assume the user TELLS us what changed, OR we use LLM to extract "Changes".
    # "User selects 'Modify', edits. System compares."
    
    # Let's implement a helper to find removed strings.
    s = difflib.SequenceMatcher(None, old_text, new_text)
    removed_chunks = []
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace' or tag == 'delete':
            removed_chunks.append(old_text[i1:i2])
            
    return removed_chunks

def scan_chapters_for_conflict(search_terms: List[str], start_chapter_index: int, all_chapters: List[str]) -> Dict[str, List[str]]:
    """
    Scan subsequent chapters for presence of removed terms.
    all_chapters: list of file paths.
    """
    conflicts = {}
    
    for i in range(start_chapter_index + 1, len(all_chapters)):
        filepath = all_chapters[i]
        filename = os.path.basename(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        found_terms = []
        for term in search_terms:
            if len(term) < 2: continue # Ignore single chars
            if term in content:
                found_terms.append(term)
                
        if found_terms:
            conflicts[filename] = found_terms
            
    return conflicts
