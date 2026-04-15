"""Markdown文档解析器"""
from typing import Dict


def parse_markdown(file_path: str) -> str:
    """
    解析Markdown文件
    
    Args:
        file_path: Markdown文件路径
        
    Returns:
        文档内容字符串
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return content


def extract_sections(content: str) -> Dict[str, str]:
    """
    提取Markdown文档的各个章节
    
    Args:
        content: Markdown内容
        
    Returns:
        章节字典 {标题: 内容}
    """
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('# '):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[2:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections
