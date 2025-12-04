# Geoscience-Morning-Digest 地质晨报

## 🛠️ 使用说明

在使用本项目之前，需要在 GitHub 仓库中配置 **Secrets**。

### 配置路径
进入仓库：
- `Settings` → `Security` → `Secrets and variables` → `Actions`
- 点击 **New repository secret** 创建新的条目

### 必须创建的 Secrets
请创建以下条目：

- **DEEPSEEK_API_KEY**  
  - 用于调用 AI 摘要生成  
  - 可以使用你自己的 API Key  
  - 推荐使用 **OpenAI** 或 **DeepSeek**  
  - 如果使用其他 AI，需要修改 `scripts/generate_digest.py` 中的相关代码，把代码中的 `"DEEPSEEK_API_KEY"` 改成你设置的 Secrets 名称

- **EMAIL_USER**  
  - 邮箱账号（发件人）

- **TO_EMAIL**  
  - 收件人邮箱  
  - 可选，不填则默认发给自己

- **EMAIL_PASS**  
  - 邮箱授权码（发件人）  ，一般邮箱授权码不是密码 
  - 其他邮箱可能需要使用授权码（可自行搜索获取方法）

- **SMTP_SERVER**  
  - 邮件服务器地址  
  - 例如：`www.email.cugb.edu.cn`

- **SMTP_PORT**  
  - 邮件服务器端口  
  - 常见值：`465` (SSL) 或 `587` (TLS)

---

### 📑 代码配置说明
- **提示词修改**：在 `scripts/generate_digest.py` 中修改  
- **RSS 订阅服务**：在 `scripts/rss_reader.py` 中配置，如需加入其他期刊，请自行添加

---

## 📧 邮件说明
- 邮件会从 `EMAIL_USER` 发送到你指定的收件人（默认就是 `EMAIL_USER` 本身）。  
- 如果需要多人订阅，可以在代码中支持多收件人，或配置邮件列表。  
- 代码完全通用，不依赖具体学校邮箱。  
- 其他用户 fork 后，只需在 Secrets 里填自己的邮箱配置，就能直接使用。  
- 支持不同 SMTP 服务（校园邮箱、Gmail、Outlook、企业邮箱等）。  
