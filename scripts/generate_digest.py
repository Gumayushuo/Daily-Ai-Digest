# scripts/generate_digest.py
import os
import json
from datetime import datetime
from openai import OpenAI

# -------------------
SEEN_JSON_PATH = "state/seen.json"
OUTPUT_PATH = "output/daily.txt"

today = datetime.now().strftime("%Y-%m-%d")

# -------------------
# 读取 seen.json
if not os.path.exists(SEEN_JSON_PATH):
    print("seen.json 不存在，请先运行 RSS 抓取脚本。")
    exit(1)

with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    try:
        seen = json.load(f)
    except Exception as e:
        print(f"读取 seen.json 出错: {e}")
        exit(1)

# 筛选今日新增论文
papers_today = [p for p in seen if isinstance(p, dict) and p.get("date") == today]

if not papers_today:
    print("今日没有新增论文。")
    daily_content = f"Daily Paper Digest — {today}\n\n今日没有新增论文。\n"
else:
    # -------------------
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    # 构建 AI 输入
    papers_brief = "\n".join(
        f"{p.get('title','未知标题')} ({p.get('source','未知期刊')})"
        for p in papers_today
    )

    system_prompt = (
        "你是一名地球科学领域科研助手。\n"
        "请根据以下论文列表生成日报。\n"
        "要求：\n"
        "1. 整体趋势提炼，6-8点。\n"
        "2. 按主题自动分类，表格形式：主题 | 代表论文 | 备注。\n"
        "3. 每篇论文一句话核心贡献。\n"
        "4. 输出纯文本日报格式，适合邮件发送。\n"
        "5. 不要包含原始条目列表。"
    )

    user_prompt = f"今天日期：{today}\n新增论文列表：\n{papers_brief}"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False
        )
        ai_summary = resp.choices[0].message.content.strip()
    except Exception as e:
        ai_summary = f"AI 摘要生成失败: {e}"

    # -------------------
    # 构建日报文本
    daily_content = []
    daily_content.append(f"Daily Paper Digest — {today}")
    daily_content.append(f"今日新增论文：{len(papers_today)}")
    daily_content.append(f"已累计收录：{len(seen)} 篇")
    daily_content.append("\n---\n")
    daily_content.append("【AI 摘要整理】\n")
    daily_content.append(ai_summary)
    daily_content.append("\n---\n")
    daily_content.append("【附录：原始论文信息】\n")

    for i, p in enumerate(papers_today, 1):
        authors = p.get("authors", [])
        authors = [a for a in authors if a]  # 去除 None
        authors_str = ", ".join(authors) if authors else "未知"
        daily_content.append(f"{i}. {p.get('title','未知标题')}")
        daily_content.append(f"   作者：{authors_str}")
        daily_content.append(f"   期刊/来源：{p.get('source','未知')}")
        daily_content.append(f"   链接：{p.get('link','')}")
        if p.get("summary"):
            daily_content.append(f"   摘要：{p['summary']}")
        daily_content.append("")  # 空行分隔

    daily_text = "\n".join(daily_content)

# -------------------
# 写入文件
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(daily_text)

print(f"日报已生成：{OUTPUT_PATH}")
# -------------------
