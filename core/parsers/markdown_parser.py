"""Markdown文档解析器"""
import re
from typing import Dict, Optional


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


def extract_page_url(content: str) -> Optional[str]:
    """
    从需求文档中提取页面 URL

    支持以下格式：
    1. ## Page URL 章节中的 URL
    2. ## 页面地址 章节中的 URL
    3. 文档中任意位置的 URL（http:// 或 https://）

    Args:
        content: Markdown内容

    Returns:
        页面 URL 字符串，未找到返回 None
    """
    sections = extract_sections(content)

    # 优先从 Page URL 或 页面地址 章节提取
    for section_name in ['Page URL', '页面地址', 'PageURL', 'URL', 'Test URL']:
        if section_name in sections:
            section_content = sections[section_name]
            url_match = re.search(r'https?://[^\s\n\)\]\}]+', section_content)
            if url_match:
                return url_match.group(0)

    # 降级：从整个文档中提取第一个 URL
    url_match = re.search(r'https?://[^\s\n\)\]\}]+', content)
    if url_match:
        return url_match.group(0)

    return None


def extract_credentials(content: str) -> Dict[str, Optional[str]]:
    """
    从需求文档中提取凭证信息

    支持格式：
    1. ## Credentials 章节
       - identifier: xxx
       - password: xxx
    2. 行内格式：identifier:xxx 或 password:xxx
    3. 中文格式：用户名:xxx 或 密码:xxx

    Args:
        content: Markdown内容

    Returns:
        {'identifier': xxx, 'password': xxx}
    """
    result = {'identifier': None, 'password': None}
    sections = extract_sections(content)

    # 优先从 Credentials 或 凭证 章节提取
    cred_content = None
    for section_name in ['Credentials', '凭证', 'Credentials', 'Login Credentials']:
        if section_name in sections:
            cred_content = sections[section_name]
            break

    search_content = cred_content if cred_content else content

    # 提取 identifier/username/用户名
    id_patterns = [
        r'(?:identifier|username|用户名|账号|账户)\s*[:：]\s*(\S+)',
        r'-\s*(?:identifier|username|用户名|账号|账户)\s*[:：]\s*(\S+)',
    ]
    for pattern in id_patterns:
        id_match = re.search(pattern, search_content, re.IGNORECASE)
        if id_match:
            result['identifier'] = id_match.group(1)
            break

    # 提取 password/密码
    pwd_patterns = [
        r'(?:password|密码)\s*[:：]\s*(\S+)',
        r'-\s*(?:password|密码)\s*[:：]\s*(\S+)',
    ]
    for pattern in pwd_patterns:
        pwd_match = re.search(pattern, search_content, re.IGNORECASE)
        if pwd_match:
            result['password'] = pwd_match.group(1)
            break

    return result


def extract_credential_env_names(content: str) -> Dict[str, Optional[str]]:
    """
    Extract credential environment variable names from a requirement document.

    Supported examples:
    - identifier_env: LOGIN_USERNAME
    - password_env: LOGIN_PASSWORD
    """
    result = {"identifier_env": None, "password_env": None}
    sections = extract_sections(content)

    cred_content = None
    for section_name in ["Credentials", "凭证", "Login Credentials"]:
        if section_name in sections:
            cred_content = sections[section_name]
            break

    search_content = cred_content if cred_content else content
    patterns = {
        "identifier_env": [
            r"(?:identifier_env|username_env|账号环境变量|用户环境变量)\s*[:：]\s*([A-Z0-9_]+)",
            r"-\s*(?:identifier_env|username_env|账号环境变量|用户环境变量)\s*[:：]\s*([A-Z0-9_]+)",
        ],
        "password_env": [
            r"(?:password_env|密码环境变量)\s*[:：]\s*([A-Z0-9_]+)",
            r"-\s*(?:password_env|密码环境变量)\s*[:：]\s*([A-Z0-9_]+)",
        ],
    }

    for key, candidates in patterns.items():
        for pattern in candidates:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
                break

    return result
