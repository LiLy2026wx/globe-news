# 每日新闻地球仪 · 项目交接文档

> **状态截止**：2026-05-26 晚
> **当前阶段**：上云改造（代码侧已完成，未与 GitHub / Cloudflare 对接）
> **下次继续**：把代码推到 GitHub → 在 Cloudflare Pages 部署 → 配 Secrets → 触发 workflow 验证 → 关本地 PC 服务
> **项目目录**：`C:\Users\zou18\globe-news\`

---

## 0. 今天（2026-05-26）做了什么

回答了昨日交接文档里的三个待决问题：

| 问题 | 答 |
|---|---|
| Q1 GitHub 账号 | **有账号，但不太用 git** → 走 GitHub + Cloudflare 路线，需手把手过命令 |
| Q2 域名 | **用 Cloudflare 免费二级域名长期使用**（`xxx.pages.dev`），不绑自定义域名 |
| Q3 本地 PC 服务 | **关掉**，云上一套就够（云端跑通后卸载计划任务） |

随后完成了**代码侧的上云改造**：把抓取逻辑从 `server.py` 拆出来，加好 GitHub Actions workflow、Cloudflare Pages 缓存头、`.gitignore` 等周边文件，所有云端要用的东西都准备好了，**只差正式推上去**。

---

## 一、项目目标（未变）

每天定时把全球新闻以可视化方式推到用户手机：

- 网页端展示**可拖动的 3D 地球仪**
- **点击国家，凸显该国，右侧面板按固定顺序显示新闻**：政治 → 军事 → 经济 → 科技 → 航空
- 地理精度：**全球到国家**，重点国家（美/俄/欧/日）后续做到省/州
- **每天早 8:00（北京时间）自动推送链接到用户微信**
- 用户在手机/平板浏览器打开链接即可使用

---

## 二、目标架构（上云后）

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub（仓库 + Actions）                                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  .github/workflows/daily.yml                          │    │
│  │  ├─ cron: 0 0 * * *  (UTC 0:00 = 北京 08:00)         │    │
│  │  ├─ workflow_dispatch（手动触发按钮）                  │    │
│  │  ├─ 跑 fetcher.py → 生成 news-data.json               │    │
│  │  ├─ git commit + push（数据有变化才提交）              │    │
│  │  └─ 跑 push.py（用 SCT_SENDKEY + SITE_URL 推微信）     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                │                            │
                │ Webhook 触发部署            │ Server酱 API
                ▼                            ▼
       ┌──────────────────┐         ┌──────────────────┐
       │ Cloudflare Pages │         │ 用户微信         │
       │ xxx.pages.dev    │ ◀── 链接 ── 收到日推链接 │
       │ 直接吐静态站点   │         │                  │
       └──────────────────┘         └──────────────────┘
                ▲
                │ 手机/平板浏览器
                │ （随时随地，不依赖家中 PC）
                ▼
       ┌──────────────────┐
       │ 用户手机/平板    │
       │ 打开地球仪       │
       └──────────────────┘
```

**今天与昨天的核心差别**：本地 PC 完全退出新闻链路。开关机不再影响服务可用性。

---

## 三、文件清单（最新）

```
C:\Users\zou18\globe-news\
├── .github\
│   └── workflows\
│       └── daily.yml       ★ 新增：Actions 每日 cron + 手动触发
├── .gitignore              ★ 新增：屏蔽 config.json / 日志 / __pycache__
├── _headers                ★ 新增：Cloudflare Pages 缓存策略（news-data.json 不缓存）
├── fetcher.py              ★ 新增：纯抓取逻辑（从 server.py 拆出）
├── requirements.txt        ★ 新增：feedparser
├── server.py               ✎ 改：删掉抓取逻辑，改为 import fetcher
├── push.py                 ✎ 改：链接读 SITE_URL 环境变量，回退到 LAN IP（本地仍可跑）
├── index.html              （未动；明天小调一下刷新按钮文案 + /refresh 优雅降级）
├── news-data.js            （静态 fallback，保留）
├── news-data.json          （Actions 会自动覆盖更新）
├── server.log              （本地运行才会生成；.gitignore 已排除）
├── setup_schedule.ps1      （明天云端跑通后用 -Unregister 卸掉本地任务）
└── HANDOFF.md              本文件
```

### 各文件职责详解（仅讲新增/变更的）

#### `fetcher.py`（新）
- 把 `COUNTRIES`、`CATEGORIES`、`gnews_rss()`、`fetch_cell()`、`fetch_all()` 从 server.py 搬过来
- **不开 HTTP，不开线程**，直接 `python fetcher.py` 就跑一次抓取并写 `news-data.json`
- GitHub Actions 用这个；本地 `server.py` 通过 import 复用

#### `server.py`（改）
- 删掉所有抓取常量和函数，改为 `from fetcher import COUNTRIES, CATEGORIES, fetch_all`
- 行数从 ~245 砍到 ~110
- 行为保持不变：仍然绑 `0.0.0.0:8765`，仍然每 6h 后台刷新，仍然 `/refresh` 手动触发
- **上云后该文件将不再被启动**（明天卸载计划任务后彻底闲置）

#### `push.py`（改）
- 新逻辑：`SITE_URL` 环境变量优先
  - 有 → 用它当链接（云端跑时由 Actions 注入 `vars.SITE_URL`）
  - 无 → 回退到 `http://{LAN_IP}:8765/`（本地直接跑时仍能工作）
- 文案条件分支：云端写"随时随地打开（无需家中 PC 开机）"；本地写"链接仅在家中 WiFi 可访问"

#### `.github/workflows/daily.yml`（新）
- 触发：`cron: '0 0 * * *'`（UTC 0:00 = 北京 08:00）+ `workflow_dispatch`（手动按钮）
- 步骤：checkout → setup-python 3.11 → pip install → 跑 fetcher.py → 数据有变化才 commit & push → 跑 push.py 推微信
- 微信推送只在 `schedule` 事件发生时跑（手动触发不会扰民）
- 用 `permissions: contents: write` 让 `GITHUB_TOKEN` 能把数据 commit 回仓库
- `concurrency: daily-news` 防止并发重复

#### `_headers`（新）
- Cloudflare Pages 专用静态规则文件
- `news-data.json` → `Cache-Control: no-store`（保证用户每次都拿最新）
- 其它静态资源短缓存

#### `requirements.txt`（新）
- 只有 `feedparser>=6.0.10`

#### `.gitignore`（新）
- `config.json`（含微信 SENDKEY，**绝不能提交**）
- `server.log*`、`*.tmp`、`__pycache__/`、`.vscode/` 等

---

## 四、明天开工的第一件事：上云三步走

### 步骤 A：创建 GitHub 仓库（用户操作 · 浏览器）

1. 打开 https://github.com/new
2. 仓库名：`globe-news`（或任意名）
3. 选 **Public**（重要：公开仓库才能享 Actions 免费无限分钟数；本仓库不含密钥）
4. **不要勾选** "Add a README"、"Add .gitignore"、"Add license"（避免初始化冲突，我们本地已有文件）
5. 点 **Create repository**
6. 复制下一步要用的仓库 URL（形如 `https://github.com/你的用户名/globe-news.git`）

### 步骤 B：本地推送代码（Claude 带着用户敲命令）

Claude 明天会按顺序帮用户在 PowerShell 里跑：

```powershell
cd C:\Users\zou18\globe-news

# 先检查 git 装了没
git --version

# 初始化 + 第一次提交
git init
git branch -M main
git add .
git status        # 检查 config.json 等不该提交的有没有被忽略
git commit -m "Initial commit: cloud-ready globe news"

# 接远端
git remote add origin https://github.com/<你的用户名>/globe-news.git
git push -u origin main
```

**风险检查**：
- 如果未装 git → 引导装 Git for Windows
- 如果 `git status` 看到 `config.json` 在 staged 里 → 立刻 `git rm --cached config.json` 后重新 commit
- 如果 push 时要登录 → 用 GitHub Desktop 或个人 Token（user 不熟 git，可能要走 GUI）

### 步骤 C：Cloudflare Pages 部署（用户操作 · 浏览器）

1. 注册 / 登录 https://dash.cloudflare.com/
2. 左栏 **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**
3. 授权 Cloudflare 读你的 GitHub → 选 `globe-news` 仓库
4. 部署设置：
   - **Project name**：自填（这就是 `xxx.pages.dev` 里的 `xxx`，唯一）
   - **Production branch**：`main`
   - **Framework preset**：`None`
   - **Build command**：留空
   - **Build output directory**：`/`（根目录）
5. 点 **Save and Deploy**
6. 等 1-2 分钟，记下你的 `xxx.pages.dev` 域名

### 步骤 D：配 GitHub Actions Secrets + Variables（用户操作 · 浏览器）

去仓库页 → **Settings** → **Secrets and variables** → **Actions**

- 在 **Secrets** 标签页 → **New repository secret**：
  - Name: `SCT_SENDKEY`
  - Value: 你的 Server酱 SENDKEY（`SCT...` 开头）

- 切到 **Variables** 标签页 → **New repository variable**：
  - Name: `SITE_URL`
  - Value: `https://xxx.pages.dev`（用刚刚 CF 给的域名，**末尾不要带 /**）

### 步骤 E：手动触发验证（用户操作 · 浏览器）

仓库页 → **Actions** → 选 **Daily News Refresh & Push** → 右侧 **Run workflow** → **Run workflow**

预期看到：
1. ✅ fetcher 跑完（~60-80 秒）
2. ✅ 自动 commit 一次 `news-data.json` 更新
3. ⏸️ 跳过 push.py（手动触发 = `schedule` 条件不满足，符合预期；不要在测试时打扰微信）
4. Cloudflare Pages 检测到 push，自动重新部署（在 CF 仪表板能看到）

部署完后用手机打开 `https://xxx.pages.dev/`，确认地球仪能转、点国家有新闻。

### 步骤 F：第二天 08:00 自然触发推送

不用做事，自然等。08:00 微信应收到日推。

### 步骤 G：关闭本地 PC 服务（云端验证通过后）

```powershell
cd C:\Users\zou18\globe-news
.\setup_schedule.ps1 -Unregister
```

确认两条任务都被删：

```powershell
Get-ScheduledTask -TaskName GlobeNews-* -ErrorAction SilentlyContinue
```

---

## 五、剩余的小代码改动（明天再做）

只剩 `index.html` 的两处小调整（**5 分钟工作量**）：

1. **刷新按钮**：在云上 `/refresh` 不存在（CF Pages 没有 server.py），现在的代码会请求 `/refresh` 然后等 15 秒。改成直接重拉 `news-data.json`，不浪费等待。
2. **底部状态文案**：从"实时数据 · 更新于 HH:MM"调整为"今日数据 · 更新于 HH:MM"（云端每天一次，叫"实时"不严谨）。

不改也能跑通，纯优化体验。

---

## 六、运维命令速查（云端版）

```powershell
# 看 Actions 状态
# 浏览器：https://github.com/<用户名>/globe-news/actions

# 手动触发一次（不会推微信）
# 浏览器：Actions → Daily News Refresh & Push → Run workflow

# 本地预览最新代码（不依赖云）
cd C:\Users\zou18\globe-news
$env:PYTHONUTF8="1"
python server.py
# 然后访问 http://localhost:8765/

# 本地手动跑一次抓取（验证 fetcher.py）
python fetcher.py

# 本地手动测一次推送（会真发微信！）
$env:SCT_SENDKEY="SCT你的Key"
$env:SITE_URL="https://xxx.pages.dev"
python push.py
```

---

## 七、决策记录（累计）

- **新闻源**：免费 Google News RSS
- **地理精度**：全球到国家，重点国家后续扩
- **部署**：~~本地 Windows~~ → **GitHub Actions + Cloudflare Pages**（今天定）
- **推送渠道**：Server酱（微信公众号）
- **推送时间**：每天一次 · 08:00 北京时间
- **推送内容**：只推链接（不附摘要）
- **GitHub 路径**：用户有账号 + 不熟 git → 由 Claude 手把手过命令
- **域名**：长期用 CF 免费的 `xxx.pages.dev`
- **本地服务**：云端跑通后关掉（用 `setup_schedule.ps1 -Unregister`）

---

## 八、风险与注意事项

- **`config.json` 已加入 .gitignore**，但第一次 `git status` 之前必须二次确认它没被提交
- **Server酱免费版 5 条/天**，远超我们 1 条/天的用量
- **Cloudflare Pages 免费版**：500 builds/月、无限带宽、无构建分钟数限制
- **GitHub Actions 免费版**：公开仓库无限分钟，私有仓库 2000 分钟/月。我们走公开仓库
- **Google News RSS 是非官方接口**，存在被封风险；建议后续加 BBC/Reuters/DW 直接 RSS 作 fallback
- **cron 偏移**：GitHub Actions cron 实际执行时间可能延迟几分钟到十几分钟（共享资源排队），不影响"早上"这个语义
- **跨日时区**：`cron: '0 0 * * *'` 是 UTC，对应北京 08:00。如果需要严格 08:00 准时，CF Workers 的 Cron Triggers 比 GitHub Actions 准（但当前没必要）

---

## 九、下一阶段路线图（云上稳定后再说）

1. **省/州下钻**：美 50 州、俄联邦主体、日本都道府县，二次点击进入
2. **新闻热度气柱**：球面 3D bar 表达每国新闻数量
3. **SEO 垃圾源过滤**：黑名单 + 标题去重
4. **多语言切换**：英文版查询同源（`hl=en-US`），右上角切换
5. **历史时间轴**：利用 git history 实现"昨天的新闻"回看
6. **PWA**：加 manifest + service worker，手机可"添加到主屏幕"像 App 一样

---

## 十、明日开工 TL;DR

```
1. index.html 收尾微调（5 分钟）
2. 用户在 github.com/new 建 globe-news 公开仓库（2 分钟）
3. 在 PowerShell 跑 git init / commit / push（Claude 带着敲，5 分钟）
4. 用户在 Cloudflare Pages 连仓库部署（5 分钟）
5. 用户在 GitHub 仓库 Settings 加 SCT_SENDKEY (Secret) 和 SITE_URL (Variable)（3 分钟）
6. Actions 手动触发验证 → 手机打开 pages.dev 域名（5 分钟）
7. 等明天 08:00 自然推送验证 → 收到则关本地 PC 服务（次日）
```

**完。明天见。**
