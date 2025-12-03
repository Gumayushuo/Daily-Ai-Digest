# scripts/generate_digest.py
import os
import json
from datetime import datetime
from openai import OpenAI  # DeepSeek 兼容接口

# -------------------
# 路径设置
DAILY_MD_PATH = "output/daily.md"
SEEN_JSON_PATH = "state/seen.json"

# -------------------
# 读取已有记录
with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    seen = json.load(f)

today = datetime.now().strftime("%Y-%m-%d")

# -------------------
# 筛选今天新增论文
papers_data = []
for paper in seen:
    if isinstance(paper, dict) and paper.get("date") == today:
        papers_data.append(paper)

# -------------------
# 调用 DeepSeek 生成 AI 核心贡献摘要
digest_text = ""
if papers_data:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    # 准备 AI 输入
    papers_brief = "\n".join([f"{p['title']} ({p.get('source','未知期刊')})" for p in papers_data])
    system_prompt = (
        "你是一名地球科学领域的专业科研助手。\n"
        "请根据以下论文列表提炼整体趋势，用学术语言生成摘要，"
        "每篇论文生成一句话核心贡献，并按主题归类。\n"
        "请输出 Markdown 格式，删除原始条目列表。"
    )
    user_prompt = f"今天日期：{today}\n以下是新增论文列表：\n{papers_brief}"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )
        digest_text = resp.choices[0].message.content
    except Exception as e:
        digest_text = f"摘要生成失败: {e}"
else:
    digest_text = "今日没有新增论文。"

# -------------------
# 写入 daily.md
new_content = f"# Daily Paper Digest — {today}\n\n" \
              f"**今日新增论文**：{len(papers_data)}\n\n" \
              f"**摘要整理**：\n{digest_text}\n"

with open(DAILY_MD_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Markdown file updated.")
