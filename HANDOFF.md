# 每日新闻地球仪 · 项目交接文档

> **状态截止**：2026-05-29
> **当前阶段**：**生产稳定，纯网页访问**。微信推送已下线、域名迁移作废（用户只用浏览器看网页，pages.dev 在系统浏览器本就正常）。新闻已可点开原文 + 限定近 2 天。
> **下次继续**：明早（05-30 09:45 BJT）看定时 routine 报告——GitHub Actions schedule 是否终于自动触发（历史 0 次）；若仍 0 触发则上外部兜底触发（第五节·🔭）。

---

## 一、今日（2026-05-29）做了什么

### 1. 核实：is-a.dev 域名路线已死 🪦
- 用权威方式（GitHub API + 实际访问）确认 PR #39517 = **closed, not merged**（2026-05-28T21:36:33Z）
- 拒绝理由 "reason: not dev related"——is-a.dev 根级子域名必须软件开发相关，儿童时事项目不符
- `globe-news.is-a.dev` 访问 302 跳 `https://is-a.dev/?d=globe-news`（未注册落地页），从未归属我们
- 详见第九节归档

### 2. 关键决策：微信推送下线 + 放弃换域名
- 用户明确**不需要微信推送**，直接浏览器开网页看每日地球仪即可
- 微信 X5 黑名单只拦微信内置浏览器，对系统浏览器/电脑访问无影响 → **不必换域名**
- `daily.yml` 精简为**纯抓取+提交**（commit `5ba899b`）：删 push 步骤/幂等标记/SCT_SENDKEY/force_push；cron 扩到 5 档错峰（07:31/07:53/08:17/08:41/09:13 BJT）

### 3. 发现真隐患：schedule 从未自动触发
- 查 GitHub API：`event=schedule` 历史运行 = **0 次**，前两天数据全靠手动 Run
- 本地手动跑 fetcher.py 把 05-29 数据推上线兜底
- 排定一次性 routine：**05-30 09:45 BJT** 自动检查 schedule 有没有终于跑起来（见第五节·🔭）

### 4. 修两个内容质量坑（commit `71f419e`）
- **点不进去** → `index.html` 原把标题渲染成纯文本 `<div>`、没用 `item.url`。改成 `<a href target="_blank" rel="noopener">` 可点开原文（CSS 加 `display:block; cursor:pointer`）
- **大多几天前** → Google News 搜索默认按相关性排序混入旧闻。`fetcher.py` 查询加 `when:2d` 限近 2 天（`gnews_rss` 用 `safe=":"` 保冒号不被编码）。重抓后 671 条全部 ≤1天前、零旧日期
- 线上已验证：`_generated=2026-05-29T10:14`，根页面含链接渲染代码

### 5. 今日 commit
`5ba899b` 精简workflow → `71f419e` 链接+新鲜度 → `40f1c36` HANDOFF → 本次再补 docs

---

## 二、文件清单（2026-05-29 状态）

```
C:\Users\zou18\globe-news\
├── .github\workflows\daily.yml       纯抓取+提交，5 档错峰 cron（微信/幂等已删）[今日精简]
├── .gitignore                          屏蔽 config.json / server.log / __pycache__
├── _headers                            CF Pages 缓存策略（news-data.json no-store）
├── assets\                             同域托管的外部资源
│   ├── countries.geojson               488 KB
│   ├── earth-night.jpg                 715 KB
│   ├── earth-topology.png              378 KB
│   └── night-sky.png                   904 KB
├── vendor\globe.gl.min.js              globe.gl 2.32.4 同域托管 (1 MB)
├── fetcher.py                          纯抓取（Actions 跑）；查询带 when:2d 近期过滤 [今日改]
├── server.py                           本地开发用，云端不启动
├── push.py                             [孤儿] 调 Server酱；workflow 已不调用，留作手动备用
├── index.html                          前端主页；新闻项现为可点击 <a> 链接 [今日改]
├── news-data.js                        静态 fallback 数据
├── news-data.json                      实时数据，Actions 每天更新
├── requirements.txt                    feedparser
├── setup_schedule.ps1                  本地 Windows 计划任务（已不用）
├── .last-push-date                     [孤儿] 旧幂等标记；精简后不再读写，可删
└── HANDOFF.md                          本文件
```

---

## 三、GitHub 配置（2026-05-28 状态）

### Secrets（Settings → Secrets and variables → Actions）
- `SCT_SENDKEY` = **已不再被 workflow 使用**（2026-05-29 微信推送下线后变孤儿；可留可删）
- `GITHUB_TOKEN` = Actions 自动注入，用于 commit 回仓

### Variables
- `SITE_URL` = `https://globe-news-do4.pages.dev`（**已不再被 workflow 使用**——push.py 才用它，现在 workflow 不跑 push.py 了；保留无害）

---

## 四、关键架构决策记录

1. **平台**：GitHub Actions（cron + 推送）+ Cloudflare Pages（静态前端）
2. **域名（已定稿，不再迁移）**：
   - 生产域名：`globe-news-do4.pages.dev`（系统浏览器/电脑正常）
   - 2026-05-29 决策：**放弃换域名**。用户只用浏览器访问网页、不需要微信推送，而 pages.dev 在系统浏览器本就正常——微信黑名单问题对网页访问无影响。
   - is-a.dev 路线已死：PR #39517 被拒（"not dev related"），见第九节归档。
3. **资源同域**：所有外部 CDN 下到仓库内同域加载（避免国内访问 unpkg/raw 不稳）
4. **本机角色**：仅作开发机，**不参与生产链路**；关机不影响推送
5. **cron 策略（2026-05-28 调整）**：
   - 单一整点 cron 在 GH Actions free tier 跳过率高
   - 改用 3 档错峰冗余，幂等标记防重复
6. **微信推送已下线（2026-05-29）**：
   - 用户确认不需要每天推微信，直接浏览器开网页看每日地球仪即可
   - `daily.yml` 已精简为**纯抓取+提交**：去掉 push 步骤、幂等标记、SCT_SENDKEY/force_push
   - `push.py` / `.last-push-date` 文件保留在仓库（不再被 workflow 调用，留作手动备用，无害）
   - 链路变为：cron → fetcher.py 抓 → commit news-data.json → CF Pages 自动部署 → 浏览器访问
7. **公司电脑特殊性**：
   - 全局 git 配置是同事 `gaoguangzhi82-oss`，仓库设了 local `LiLy2026wx`
   - 每次 push 后必须 `cmdkey /delete:LegacyGeneric:target=git:https://github.com`
   - **git push 必须设代理**：`$env:HTTP_PROXY="http://127.0.0.1:7890"` + `$env:HTTPS_PROXY="..."`，Clash Verge 监听 7890
   - 浏览器 OAuth 务必先确认 github.com 登的是 LiLy2026wx
8. **微信内置浏览器限制（2026-05-28 发现，仅历史参考）**：
   - WeChat X5 内核黑名单拦截所有"免费海外静态托管二级域名"
   - 表现：`ERR_NAME_NOT_RESOLVED`（伪装成 DNS 错误）
   - 系统浏览器无限制
   - **现已不影响本项目**：微信推送下线，纯网页访问走系统浏览器

---

## 五、🌅 接下来要做的事

### ✅ 2026-05-29 已完成
- 域名迁移任务**作废**（见第四节·2、第九节归档）
- `daily.yml` 精简为纯抓取+提交，cron 扩到 5 档错峰（07:31/07:53/08:17/08:41/09:13 BJT）
- 本地手动跑 fetcher.py 把 05-29 数据推上线（修补 schedule 首日没自动跑）
- **修两个内容质量坑**（commit 71f419e）：
  1. 新闻点不进去 → `index.html` 原来把标题渲染成纯文本 `<div>`，没用 `item.url`。改成 `<a target="_blank" rel="noopener">` 可点开原文（CSS 加 display:block/cursor:pointer）
  2. 新闻大多几天前 → Google News 搜索默认按相关性排序混入旧闻。`fetcher.py` 查询加 `when:2d` 限近 2 天（`gnews_rss` 用 safe=":" 保冒号）。重抓后 671 条全部 ≤1天前，零旧日期

### 🔭 唯一待观察项：schedule 是否真能自动触发
- **背景**：GitHub Actions schedule 在本仓库历史触发次数 = **0**（前几天数据全是手动 Run 出来的）。免费公共仓库 schedule 高延迟/会丢首跑。
- **怎么验**：明天（05-30）早上 9:30 BJT 后查
  ```powershell
  # 浏览器：https://github.com/LiLy2026wx/globe-news/actions
  # 或 API：看有没有 event=schedule 的成功 run
  ```
  也可直接看网页 news-data.json 的 `_generated` 是不是 05-30。
- **若仍不触发**（连续两天 0 schedule run）→ 升级为外部触发兜底（任选其一）：
  1. 免费外部 cron（cron-job.org）定时打 GitHub API `workflow_dispatch`（需一个 fine-grained PAT，scope: actions:write）
  2. 本机 Windows 计划任务每早跑 `fetcher.py` + push（见 setup_schedule.ps1，但要求开机）
  3. Cloudflare Worker Cron Trigger（最可靠，但 fetcher 是 Python 需重写为 JS，工作量大）
- **手动应急刷新**（任何时候数据旧了）：
  ```powershell
  cd C:\Users\zou18\globe-news
  $env:PYTHONUTF8="1"; $env:HTTP_PROXY="http://127.0.0.1:7890"; $env:HTTPS_PROXY="http://127.0.0.1:7890"
  python fetcher.py
  git add news-data.json; git commit -m "chore(data): manual refresh"; git push
  cmdkey /delete:LegacyGeneric:target=git:https://github.com
  ```
  或浏览器 Actions → Daily News Refresh → Run workflow（无需任何输入）

---

## 六、未来路线图（不紧急，看心情做）

### 🎨 视觉/功能
1. 改 fetcher.py 让光柱真有高低差（当前等高）
2. 省/州下钻（美 50 州 / 俄联邦主体 / 日本都道府县）
3. SEO 垃圾源过滤（黑名单 + 标题去重）
4. 多语言（中/英切换，hl=en-US）
5. 历史时间轴（利用 git history 看"昨天的新闻"）
6. PWA（manifest + service worker，加到主屏）

### 🛠️ 工程/运维
1. 生成 fine-grained PAT 代替本机 OAuth（免除每次 push 凭据仪式）
2. 升级 GitHub Actions 版本（消除 Node 20 deprecated 警告）
3. 加 fallback 抓取源（BBC/Reuters/DW 直接 RSS）

---

## 七、常用运维命令速查

```powershell
# === 看 Actions 状态 ===
# 浏览器：https://github.com/LiLy2026wx/globe-news/actions

# === 看 is-a.dev PR 状态 ===
# 浏览器：https://github.com/is-a-dev/register/pull/39517

# === 手动触发一次完整 Actions 跑 + 强制推送 ===
# 浏览器：Actions → Daily News Refresh & Push → Run workflow → 勾 force_push → Run

# === 本地手动跑一次抓取（验证 fetcher.py，不发微信）===
cd C:\Users\zou18\globe-news
$env:PYTHONUTF8="1"
python fetcher.py

# === 本地手动测一次推送（会真发微信！）===
$env:SCT_SENDKEY="SCT你的新KEY"      # ⚠️ 用 2026-05-28 重置后的新值
$env:SITE_URL="https://globe-news-do4.pages.dev"
python push.py

# === push 代码到 GitHub（公司电脑仪式）===
# 步骤 0：浏览器先确认 github.com 登的是 LiLy2026wx 而非同事 gaoguangzhi82-oss
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
cd C:\Users\zou18\globe-news
git push
cmdkey /delete:LegacyGeneric:target=git:https://github.com
```

---

## 八、下次开工 TL;DR

```
1. 浏览器开 https://globe-news-do4.pages.dev/ 看地球仪是否最新
2. 看 news-data.json 的 _generated 是不是当天 → 判断 schedule 自动跑了没
3. 若 schedule 连续两天 0 触发 → 上外部触发兜底（第五节·🔭·1）
4. 数据旧了随时手动应急刷新（第五节末尾命令）
```

**完。** 2026-05-29：域名任务作废，微信推送下线，链路精简为「cron→抓取→提交→CF Pages→浏览器」。当前数据已手动刷到 05-29，待观察 schedule 明早能否自动跑。

---

## 九、归档：已死的 is-a.dev 路线（2026-05-29）

- PR #39517 状态：**closed, not merged**（2026-05-28T21:36:33Z）
- 拒绝理由：维护者 @dragsbruh "reason: not dev related"——is-a.dev 根级子域名必须软件开发相关，儿童时事地球仪不符
- `globe-news.is-a.dev` 不归属我们：访问 302 跳转 `https://is-a.dev/?d=globe-news`（未注册子域落地页）
- 教训：is-a.dev 只收开发相关项目；非开发项目要"微信可打开域名"得买真实域名或走 eu.org 等
