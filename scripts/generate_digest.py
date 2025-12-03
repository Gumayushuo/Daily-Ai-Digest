# scripts/generate_digest.py
import os
import json
from datetime import datetime
from openai import OpenAI

# -------------------
SEEN_JSON_PATH = "state/seen.json"
OUTPUT_PATH = "output/daily.md"  

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
# ⚠️ 【临时修复代码】如果今天新增文章过多，我们认为这是冷启动或重复运行导致的错误。
#    我们将所有文章的日期字段清除，并重新提交 seen.json，强制让 generate_digest 在下次运行只看到真正新增的文章。
if len(papers_today) > 100 and len(seen) > 100:
    print(f"检测到 {len(papers_today)} 篇新增论文，数量异常，正在重置 seen.json 中的日期标签。")
    # 重置 seen 列表中所有文章的日期
    for p in seen:
        if isinstance(p, dict) and p.get("date"):
            p["date"] = "1970-01-01" # 设为一个过去时间
            
    # 将重置后的 seen 列表写回文件 (覆盖原来的文件)
    with open(SEEN_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, ensure_ascii=False)
        
    print("日期标签重置完毕。本次运行将跳过 AI 摘要。请再次触发 Workflow。")
    # 强制退出，让 GitHub Action 提交重置后的 seen.json
    exit(0) 

if not papers_today:
    print("今日没有新增论文。")
    # 如果没有新增论文，直接设置 daily_content
    daily_content = [f"Daily Paper Digest — {today}", "\n今日没有新增论文。\n"] 
    daily_text = "\n".join(daily_content)
else:
    # -------------------
    # 【开始 else 块】所有 AI 摘要生成和日报构建都在这里
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    # 论文数量限制（防止 Context Window 溢出）
    if len(papers_today) > 50:
        print(f"警告：今日新增论文过多 ({len(papers_today)}篇)，为防止 AI 崩溃，仅选取前 30 篇进行摘要。")
        papers_for_ai = papers_today[:30]
    else:
        papers_for_ai = papers_today
        
    # 构建 AI 输入
    papers_brief = "\n".join(
        f"{p.get('title','未知标题')} ({p.get('source','未知期刊')})"
        for p in papers_for_ai
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
        daily_content.append(f"   作者：{authors_str}") # 修正缩进，统一使用 4 个空格
        daily_content.append(f"   期刊/来源：{p.get('source','未知')}") # 修正缩进
        daily_content.append(f"   链接：{p.get('link','')}") # 修正缩进
        if p.get("summary"):
            daily_content.append(f"   摘要：{p['summary']}") # 修正缩进
        daily_content.append("")  # 空行分隔

    daily_text = "\n".join(daily_content) # 最终的日报文本

# -------------------
# 写入文件
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(daily_text)

print(f"日报已生成：{OUTPUT_PATH}")
