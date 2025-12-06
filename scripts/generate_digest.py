import os
import json
import time
from datetime import datetime
from openai import OpenAI

# -------------------
SEEN_JSON_PATH = "state/seen.json"
OUTPUT_PATH = "output/daily.md"  

# 获取今天的日期
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

# 获取所有未发送的论文
papers_unsent = [p for p in seen if not p.get("sent", False)]

# ==========================================
# 【关键修改 1】设置最大显示数量，避免邮件爆炸
# ==========================================
MAX_DISPLAY_COUNT = 30  # 每天最多处理和显示多少篇

# -------------------
if not papers_unsent:
    print("今日没有需要发送的新论文。")
    daily_content = [
        f"Daily Paper Digest — {today}",
        "\n今日没有新增论文。\n",
        f"已累计收录：{len(seen)} 篇"
    ]
    daily_text = "\n".join(daily_content)

else:
    # 准备要处理的论文列表（截断）
    total_new_count = len(papers_unsent)
    
    if total_new_count > MAX_DISPLAY_COUNT:
        print(f"警告：今日新增论文过多 ({total_new_count}篇)，仅选取前 {MAX_DISPLAY_COUNT} 篇进行展示。")
        papers_to_process = papers_unsent[:MAX_DISPLAY_COUNT]
        hidden_count = total_new_count - MAX_DISPLAY_COUNT
    else:
        papers_to_process = papers_unsent
        hidden_count = 0

    # -------------------
    # AI 摘要部分
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        ai_summary = "警告：未设置 DEEPSEEK_API_KEY，无法生成 AI 摘要。"
    else:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

        papers_brief = "\n".join(
            f"{p.get('title','未知标题')} ({p.get('source','未知期刊')})"
            for p in papers_to_process
        )

        system_prompt = """你是一位专业的地球科学领域AI研究助理，负责生成每日论文摘要日报。
请基于提供的论文列表，生成：1.今日概览 2.核心趋势 3.热点主题分类 4.亮点论文深度解读(3-5篇)。
请忽略非地球科学（如纯医学、计算机）的论文。
输出格式清晰，不要使用代码块，适合邮件阅读。"""
        
        user_prompt = f"今天日期：{today}\n新增论文列表（共{len(papers_to_process)}篇）：\n{papers_brief}"

        def retry_api_call(max_retries=3, base_delay=2):
            for attempt in range(max_retries):
                try:
                    resp = client.chat.completions.create(
                        model="deepseek-reasoner",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        stream=False
                    )
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    print(f"AI 调用失败: {e}")
                    time.sleep(base_delay * (2 ** attempt))
            return "AI 摘要生成失败，请检查 API。"

        ai_summary = retry_api_call()

    # -------------------
    # 生成日报内容
    daily_content = []
    daily_content.append(f"Daily Paper Digest — {today}")
    daily_content.append(f"今日新增论文：{total_new_count} 篇")
    if hidden_count > 0:
        daily_content.append(f"（注：由于数量过多，本邮件仅展示前 {MAX_DISPLAY_COUNT} 篇，其余 {hidden_count} 篇已自动归档）")
    
    daily_content.append(f"已累计收录：{len(seen)} 篇")
    daily_content.append("\n---\n")
    daily_content.append("【AI 摘要整理】\n")
    daily_content.append(ai_summary)
    daily_content.append("\n---\n")
    daily_content.append(f"【附录：精选前 {len(papers_to_process)} 篇原始论文】\n")
    daily_content.append("（已排除医学、纯工程、计算机科学等明显不相关领域，但由于AI判定限制，可能仍有少量残留）\n")

    # 【关键修改 2】这里只遍历 papers_to_process，而不是 papers_unsent
    for i, p in enumerate(papers_to_process, 1):
        authors = p.get("authors", [])
        # 处理作者列表可能为 None 的情况
        if authors is None:
            authors = []
        
        authors_str = ", ".join(authors[:3]) + (" 等" if len(authors) > 3 else "") if authors else "未知"
        
        # 修复了这里的 f-string 语法错误
        daily_content.append(f"### {i}. {p.get('title','未知标题')}")
        daily_content.append(f"- **期刊**：{p.get('source','未知')}")
        daily_content.append(f"- **作者**：{authors_str}")
        daily_content.append(f"- **链接**：{p.get('link','')}")
        
        summary = p.get('summary', '')
        # 处理 summary 为 None 的情况
        if summary is None:
            summary = ""
        summary = summary.strip()
            
        if len(summary) > 300:
            summary = summary[:300] + "..."
        if summary:
            daily_content.append(f"- **摘要**：{summary}")
        daily_content.append("") # 空行

    daily_text = "\n".join(daily_content)

# -------------------
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(daily_text)

print(f"日报已生成：{OUTPUT_PATH}")

# ==========================================
# 【关键修改 3】更新状态：把原本所有 unsent 的（包括未展示的）都标记为 sent
# ==========================================
if papers_unsent:
    print(f"正在更新 {len(papers_unsent)} 篇论文的状态为已发送...")
    # 只要出现在 unsent 列表里，无论是否在邮件中显示，都标记为 sent
    # 这样明天就不会重复出现了
    for p in papers_unsent:
        p['sent'] = True
    
    try:
        with open(SEEN_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2, ensure_ascii=False)
        print("成功更新 seen.json，所有积压文章已标记为 sent: true")
    except Exception as e:
        print(f"严重错误：无法保存 seen.json状态: {e}")
