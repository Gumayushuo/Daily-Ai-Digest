import os
import openai
import json
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

def load_new_entries():
    with open("output/daily.md", "r", encoding="utf-8") as f:
        content = f.read()

    # 从 daily.md 里提取 “今日新增论文”
    if "## New Papers" in content:
        new_part = content.split("## New Papers")[1]
    else:
        new_part = content
    return new_part

def generate_digest(papers_raw):
    today = datetime.utcnow().strftime("%Y-%m-%d")

    prompt = f"""
你是一名地球科学领域的专业科研助手。

下面是今天新增的论文列表，请你完成以下任务：

1）提炼今天新增论文的整体趋势  
2）用学术语言生成一个“今日论文晨报”，适合科研工作者快速阅读  
3）按主题自动分类（如构造、地球化学、地球动力学等）  
4）每篇论文总结一句话核心贡献  
5）最后附上原始条目列表

今天日期：{today}

以下是新增论文条目：

{papers_raw}

请严格输出 Markdown 格式。
"""

    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "你是专业科研助手"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message["content"]


def save_digest(content):
    with open("output/digest.md", "w", encoding="utf-8") as f:
        f.write(content)
    print("digest.md 已生成")


if __name__ == "__main__":
    papers = load_new_entries()
    digest = generate_digest(papers)
    save_digest(digest)
