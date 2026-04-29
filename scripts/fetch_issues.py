"""拉取 GitHub Issues 并保存为 Markdown"""
import json
import urllib.request
from datetime import datetime

# GitHub Token
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "LittleParis/AgentTestingHelper"

# 获取 issues
url = f"https://api.github.com/repos/{REPO}/issues?state=all&per_page=100"
req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}"})
response = urllib.request.urlopen(req)
issues = json.loads(response.read().decode())

# 生成 Markdown
md_content = f"""# GitHub Issues 列表

**仓库**: {REPO}
**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总数**: {len(issues)}

---

"""

for issue in issues:
    number = issue['number']
    title = issue['title']
    state = issue['state']
    body = issue.get('body', '') or '无描述'
    created = issue['created_at'][:10]
    labels = [l['name'] for l in issue.get('labels', [])]
    issue_url = issue['html_url']

    state_emoji = '🟢' if state == 'open' else '🔴'
    labels_str = ', '.join([f'`{l}`' for l in labels]) if labels else '无标签'

    md_content += f"""## {state_emoji} #{number}: {title}

- **状态**: {state}
- **标签**: {labels_str}
- **创建时间**: {created}
- **链接**: [{issue_url}]({issue_url})

### 描述

{body}

---

"""

# 保存文件
with open("docs/github_issues.md", "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"已保存 {len(issues)} 个 issues 到 docs/github_issues.md")
