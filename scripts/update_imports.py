#!/usr/bin/env python3
"""
批量更新导入路径的脚本

用于将旧的导入路径更新为新的 core/ 结构
"""
import os
import re
from pathlib import Path


def update_imports_in_file(file_path: Path):
    """更新单个文件中的导入路径"""
    if not file_path.suffix == '.py':
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 定义导入路径映射
        import_mappings = {
            r'from agents\.': 'from core.agents.',
            r'from models\.': 'from core.models.',
            r'from parsers\.': 'from core.parsers.',
            r'from automation\.': 'from core.automation.',
            r'from utils\.': 'from core.utils.',
            r'import agents\.': 'import core.agents.',
            r'import models\.': 'import core.models.',
            r'import parsers\.': 'import core.parsers.',
            r'import automation\.': 'import core.automation.',
            r'import utils\.': 'import core.utils.',
        }
        
        # 应用映射
        updated = False
        for old_pattern, new_pattern in import_mappings.items():
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_pattern, content)
                updated = True
        
        # 如果有更新，写回文件
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
    
    except Exception as e:
        print(f"Error updating {file_path}: {e}")


def main():
    """主函数"""
    # 需要更新的目录
    directories = [
        Path('core'),
        Path('tests'),
        Path('.'),  # 根目录的 .py 文件
    ]
    
    for directory in directories:
        if directory.exists():
            # 递归查找所有 .py 文件
            for py_file in directory.rglob('*.py'):
                update_imports_in_file(py_file)


if __name__ == "__main__":
    main()