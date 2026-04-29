"""将 GitHub Issues 分割成独立文件"""
import json
import urllib.request
import os
from datetime import datetime

# GitHub Token
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "LittleParis/AgentTestingHelper"

# 获取 issues
url = f"https://api.github.com/repos/{REPO}/issues?state=all&per_page=100"
req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}"})
response = urllib.request.urlopen(req)
issues = json.loads(response.read().decode())

# 按 number 排序
issues.sort(key=lambda x: x['number'])

# 创建输出目录
output_dir = "docs/issues"
os.makedirs(output_dir, exist_ok=True)

# 为每个 issue 生成独立文件
for issue in issues:
    number = issue['number']
    title = issue['title']
    state = issue['state']
    body = issue.get('body', '') or '无描述'
    created = issue['created_at'][:10]
    updated = issue.get('updated_at', '')[:10] if issue.get('updated_at') else created
    closed = issue.get('closed_at', '')
    labels = [l['name'] for l in issue.get('labels', [])]
    issue_url = issue['html_url']
    comments_count = issue.get('comments', 0)

    state_emoji = '🟢' if state == 'open' else '🔴'
    labels_str = ', '.join([f'`{l}`' for l in labels]) if labels else '无标签'

    md_content = f"""# Issue #{number}: {title}

| 属性 | 值 |
|------|-----|
| 状态 | {state_emoji} {state} |
| 标签 | {labels_str} |
| 创建时间 | {created} |
| 更新时间 | {updated} |
| 关闭时间 | {closed[:10] if closed else '未关闭'} |
| 评论数 | {comments_count} |
| 链接 | [{issue_url}]({issue_url}) |

---

## 内容

{body}
"""

    # 保存文件
    filename = f"{output_dir}/issue-{number:02d}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"已保存: {filename}")

print(f"\n完成！共分割 {len(issues)} 个 issues 到 {output_dir}/")
