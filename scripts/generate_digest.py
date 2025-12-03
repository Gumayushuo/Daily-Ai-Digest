# scripts/generate_digest.py
import os
import json
import requests
from datetime import datetime

# 路径设置
DAILY_MD_PATH = "output/daily.md"
SEEN_JSON_PATH = "state/seen.json"

# 从 seen.json 里读取已有记录
with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    seen = json.load(f)

# 从 daily.md 里读取今天新增条目
today = datetime.now().strftime("%Y-%m-%d")

# 收集当天的新论文
papers = []
for paper_id, paper in seen.items():
    if paper.get("date") == today:
        papers.append(f"- {paper['title']} ({paper['source']})")

if not papers:
    print("No new entries today.")
    digest = "今日没有新增论文。"
else:
    print(f"Generating digest for {len(papers)} papers...")

    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    url = "https://api.deepseek.ai/v1/generate"  # 替换为 DeepSeek 官方 endpoint
    payload = {
        "prompt": (
            "你是一名地球科学领域的专业科研助手。

下面是今天新增的论文列表，请你完成以下任务：

1）提炼今天新增论文的整体趋势  
2）用学术语言生成一个“今日论文晨报”，适合科研工作者快速阅读  
3）按主题自动分类（如构造、地球化学、地球动力学等）  
4）每篇论文总结一句话核心贡献  
5）最后附上原始条目列表

今天日期：{today}

以下是新增论文条目：

{papers_raw}

请严格输出 Markdown 格式。"
            "格式类似早报，每条包括标题和来源：\n\n" +
            "\n".join(papers)
        ),
        "model": "text-summary"
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        digest = resp.json().get("text", "未能生成摘要")
    except Exception as e:
        digest = f"摘要生成失败: {e}"

# 写入 daily.md
with open(DAILY_MD_PATH, "r", encoding="utf-8") as f:
    daily_md = f.read()

# 在 markdown 顶部加摘要
new_content = f"# Daily Paper Digest — {today}\n\n**今日新增论文**：{len(papers)}\n\n**摘要整理**：\n{digest}\n\n---\n\n"

# 保留原有内容
new_content += daily_md

with open(DAILY_MD_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Markdown file updated.")
