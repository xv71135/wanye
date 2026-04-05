# 站点大纲 · AI Agents & UX Hub

面向：中英文流量、Google 收录、后续注册与订阅变现。域名示例：`3737-k.info`（部署后请全局替换为你的正式域名）。

---

## 一、信息架构（当前骨架 + 后续扩展）

| 路径 | 用途 | 状态 |
|------|------|------|
| `/` | 语言入口（跳转 EN） | 已建 |
| `/en/` | 英文落地页（主 SEO 页） | 已建 |
| `/zh/` | 中文落地页 | 已建 |
| `/en/agents/` | 智能体目录/分类（后续） | 占位可链 |
| `/zh/agents/` | 同上 | 占位可链 |
| `/en/pricing/` | 订阅与套餐（后续） | 规划 |
| `/zh/pricing/` | 同上 | 规划 |
| `/register` · `/login` | 用户体系（后续） | 规划 |
| `/legal/privacy` · `/terms` | 合规（订阅必备） | 规划 |

---

## 二、核心 SEO 策略（Google）

1. **独立 URL**：`/en/` 与 `/zh/` 各一套，互不混排正文；`<html lang="en">` / `lang="zh-CN"`。
2. **hreflang**：每页互指 `en`、`zh`、`x-default`，避免重复内容惩罚。
3. **结构化数据**：`Organization`、`WebSite`（含 `SearchAction` 占位）、`FAQPage`（精选问答，利于富摘要）。
4. **技术项**：`canonical`、`robots.txt`、`sitemap.xml`、语义化 `h1–h3`、`meta description` 独立撰写。
5. **性能**：静态资源、可上 Cloudflare 缓存；后续加图片时用 `width/height` 与 WebP。

---

## 三、英文主关键词池（首页自然融入，勿堆砌）

- AI agents, autonomous AI agents, multi-agent systems, agent orchestration  
- LLM agents, conversational AI, AI copilots, agent frameworks  
- AI user experience, human–AI interaction, trustworthy AI UX  
- Agent tooling, workflow automation with LLMs  

长尾（后续文章/落地页）：*best practices for AI agent UX*, *how to build multi-agent products*, *AI agent safety for consumer apps* 等。

---

## 四、中文主关键词池

- 人工智能体、AI 智能体、多智能体、自主智能体  
- 大模型智能体、对话式 AI、智能体编排、AI 用户体验  
- 人机交互、可信 AI、智能体产品化  

---

## 五、转化与订阅（预留）

- 首屏次要 CTA：**Join waitlist** / **预约内测**（后续接表单或邮件）。  
- 页脚：**Pre-register** 锚点，便于以后换成真实注册链接。  
- 付费前必备：隐私政策、服务条款、退款说明（页面后续补）。

---

## 六、部署检查清单

- [ ] 将 `3737-k.info` 替换为生产域名（HTML、sitemap、canonical）。  
- [ ] Cloudflare：DNS 指向 Pages 或腾讯云反代；开启 HTTPS。  
- [ ] Google Search Console：添加属性、提交 `sitemap.xml`。  
- [ ] 准备一张 1200×630 的 `og:image` 放 `assets/og-default.jpg` 并更新 meta。  
