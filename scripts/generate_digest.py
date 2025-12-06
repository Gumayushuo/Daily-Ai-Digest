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
    daily_content = [f"Daily Paper Digest — {today}", "\n错误：seen.json 文件不存在，请检查 RSS 抓取步骤。\n"]
    daily_text = "\n".join(daily_content)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(daily_text)
    print(f"错误日报已生成：{OUTPUT_PATH}")
    exit(1)

with open(SEEN_JSON_PATH, "r", encoding="utf-8") as f:
    try:
        seen = json.load(f)
    except Exception as e:
        print(f"读取 seen.json 出错: {e}")
        daily_content = [f"Daily Paper Digest — {today}", f"\n错误：读取 seen.json 文件出错: {e}\n"]
        daily_text = "\n".join(daily_content)
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(daily_text)
        print(f"错误日报已生成：{OUTPUT_PATH}")
        exit(1)

# 获取所有未发送的论文
papers_unsent = [p for p in seen if not p.get("sent", False)]

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
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not DEEPSEEK_API_KEY:
        ai_summary = "警告：未设置 DEEPSEEK_API_KEY，无法生成 AI 摘要。"
    else:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

        if len(papers_unsent) > 50:
            print(f"警告：今日新增论文过多 ({len(papers_unsent)}篇)，仅选取前 30 篇进行摘要。")
            papers_for_ai = papers_unsent[:30]
        else:
            papers_for_ai = papers_unsent

        papers_brief = "\n".join(
            f"{p.get('title','未知标题')} ({p.get('source','未知期刊')})"
            for p in papers_for_ai
        )

        system_prompt = """你是一位专业的地球科学领域AI研究助理，负责生成每日论文摘要日报。

核心任务  
基于今日新增论文列表，生成专业、精炼、有洞察力的日报内容。

重要过滤规则  
- 仅处理与地球科学相关的论文（地质学、地球化学、地球物理、大气科学、海洋学、环境地球科学等）。  
- 完全忽略其他领域的论文（医学、纯工程、计算机科学、纯数学等）。  
- 在日报正文和附录中都不要显示这些被过滤掉的论文。  

输出要求  
请按以下结构组织内容，用正常书报风格，不要使用 Markdown 符号或表格。不要加粗使用加粗字体，因为我邮箱里是看不到格式的改变的，所以只能看到**xx**,导致排版很难看：

1. 今日概览  
简要说明今日新增的地球科学论文数量，以及主要来源期刊的分布情况。  

2. 核心趋势  
总结今日最显著的研究趋势，写成三到五个要点。每个要点包括趋势描述、代表性论文（用简短标题或编号引用，不要全文复制）、潜在意义或影响。  

3. 热点主题分类  
用自然语言描述今日的研究主题分类，不要用表格。比如可以写成段落或列表，说明每个主题的论文数量、代表论文和关键进展。  

4. 亮点论文深度解读  
挑选三到五篇最重要的论文，逐篇进行分析。每篇包括：核心贡献、创新方法、潜在应用价值、局限性或未来方向。  


写作风格指南  
- 专业但易懂，适合科研人员快速浏览  
- 使用适当的表情符号增加可读性  
- 避免过度技术术语，必要时简单解释  
- 突出“为什么重要”而不仅仅是“是什么”  
- 保持客观，标注不确定性。

筛选标准  
- 保留：地球科学相关（地质学、地球化学、地球物理、大气科学、海洋学、环境地球科学等）  
- 排除：纯工程、计算机科学、医学、纯数学等无关领域  
- 在附录中只显示过滤后的论文，不要显示被排除的论文  

请基于以上框架生成日报，确保信息准确、结构清晰、洞察深刻。
"""    
        user_prompt = f"今天日期：{today}\n新增论文列表：\n{papers_brief}"

        # -------------------
        # 新增：重试机制
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
                    wait_time = base_delay * (2 ** attempt)
                    print(f"[警告] AI 调用失败 (尝试 {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        print(f"[重试] 等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        return f"AI 摘要生成失败: {e}。请检查 API Key 或网络连接。"

        ai_summary = retry_api_call()

    # -------------------
    daily_content = []
    daily_content.append(f"Daily Paper Digest — {today}")
    daily_content.append(f"今日新增论文：{len(papers_unsent)}")
    daily_content.append(f"已累计收录：{len(seen)} 篇")
    daily_content.append("\n---\n")
    daily_content.append("【AI 摘要整理】\n")
    daily_content.append(ai_summary)
    daily_content.append("\n---\n")
    daily_content.append("【附录：原始论文信息】\n")

    for i, p in enumerate(papers_unsent, 1):
        authors = p.get("authors", [])
        authors = [a for a in authors if a]
        authors_str = ", ".join(authors) if authors else "未知"
        daily_content.append(f"{i}. {p.get('title','未知标题')}")
        daily_content.append(f"    作者：{authors_str}")
        daily_content.append(f"    期刊/来源：{p.get('source','未知')}")
        daily_content.append(f"    链接：{p.get('link','')}")
        if p.get("summary"):
            daily_content.append(f"    摘要：{p['summary']}")
        daily_content.append("")

    daily_text = "\n".join(daily_content)

# -------------------
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(daily_text)

print(f"日报已生成：{OUTPUT_PATH}")
