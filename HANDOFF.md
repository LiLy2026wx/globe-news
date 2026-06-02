# 每日新闻地球仪 · 项目交接文档

> **状态截止**：2026-06-02
> **当前阶段**：**生产稳定，全自动**。GitHub Actions schedule 已确认能自动触发（每日自动抓取+提交），冗余 cron 撞 push 的 non-fast-forward 竞争已修复。纯网页访问，微信推送已下线、域名迁移作废。
> **下次继续**：① 手机验证：新闻点击能打开文章 + 光柱有高低差 + 点中国→下钻省份→点省看新闻→返回全球。② 观察 06-03 起 "Run failed" 邮件是否停。可选下一步：把省级下钻扩展到美/俄/日（管道已通用化，见第一节·8）。⚠️ Google News 解码走非公开 `batchexecute` 接口，若 Google 改版会批量回退百度搜索（点击仍可用），届时更新 `fetcher.py::resolve_gnews_url`。

---

## 一、今日（2026-06-02）做了什么

### 1. 排查：连日 "Daily News Refresh Run failed" 邮件
- 用户连续几天收到 GitHub 失败通知邮件（All jobs have failed，2 annotations）
- 用公开 GitHub API 逐 run 拆步骤定位：**失败永远在第 7 步 `Commit data if changed`（exit code 1），抓取本身（第 6 步）每次都成功**
- 失败是**间歇性**的（有成功有失败，且都挤在两三分钟内的爆发里）

### 2. 根因：冗余 cron 爆发触发 → push 撞 non-fast-forward
- 免费公共仓库的 schedule 会高延迟 + **批量爆发触发**，5 档错峰 cron 被挤在同一时段
- 一个 run checkout 后，另一个 run 抢先 push，它再 push 就被远端拒绝（`fetch first` / non-fast-forward）→ exit 1
- 排查时我自己提交 daily.yml 也现场撞上同一个 bug，正好验证了诊断 😄
- 邮件里"2 annotations" = ① Node20 弃用**警告**（无害，checkout@v4/setup-python@v5 已是最新大版本）+ ② push 失败
- `dynamic` 事件的 run 是 **GitHub Pages 自动部署**（github-pages[bot]），只部署不 push，与冲突无关

### 3. 修复：抗竞争推送（commit `99e9f65`）
- `daily.yml` 第 7 步改为：`git push` 被拒 → `git fetch origin main` + `git reset --soft origin/main` 把本次最新 `news-data.json` 原样叠到最新 main 上 → 重推，循环最多 5 次
- 单一生成文件 → 零合并冲突、幂等；若上游已是当前数据则直接跳过
- **5 档错峰 cron 是有意保留的可靠性设计，不删**——现在它们再撞也会自动让路重推

### 4. 顺带确认：schedule 已能自动触发 ✅
- 查 API：本仓库已有 43 个 run、`event=schedule` 成功提交（如 06-02 03:33 / 04:00 自动 refresh）
- 记忆里"历史 0 次触发"的担忧**已解除**——之前的失败纯粹是 push 竞争，不是没触发

### 6. 修两个用户反馈的线上 bug（commit `fb7a555`）
- **更新时间不对劲** → `fetcher.py` 原用裸 `datetime.now()`（Actions runner 是 UTC），存出的 `_generated`/`_meta` 比北京时间慢 8 小时，前端 `new Date()` 渲染成"昨天 19:58"。改为 `datetime.now(BJT)`（`timezone(timedelta(hours=8))`），`_generated` 带 `+08:00` 偏移；`humanize_time` 的"x小时前"本就用 UTC 比较、不受影响。
- **新闻点进去黑屏跳回** → 存的 URL 全是 `news.google.com/rss/articles/...` 跳转链接，Google 在国内/微信打不开。改为**抓取时解码成真实文章直链**：
  - 走 Google 内部 `batchexecute` 接口（`resolve_gnews_url`）：先 GET rss/articles 页拿 `data-n-a-sg`/`data-n-a-ts` 签名，再 POST 还原真实 URL。**注意：签名在那 576KB 页面末尾，必须下整页**，没法流式省流量。
  - 8 线程并发（`resolve_all_urls`），全量 694 条约 36s；GET 累计下载 ~385MB（Actions 带宽够）
  - **双重兜底，绝不存打不开的链接**：① 解码失败 → 百度搜索该标题；② 已知被墙外媒域名（BBC/RFI/DW/NYT/路透/卫报… 见 `BLOCKED_DOMAINS`）即便解出真链也转百度搜索同题报道
  - 全量结果：641 直链 + 53 转百度，0 残留 google 链接
  - 新增依赖 `requests`（已写入 requirements.txt）
- 已本地全量跑一遍把修好的数据推上线（`_generated=2026-06-02T10:30+08:00`），不用等明早 cron

### 7. 推进路线图：光柱高低差（commit `1a5e46f`）
- 原因：光柱高度本来就按"留下的条数"算，但每国最多 5条×5类=25 条、活跃国全顶到上限 → 看着等高
- 改用**热度**：`fetcher` 给每国存按类别的 `_intensity`（近2天该查询原始命中数，如中国 337 / 波兰 40）
- 前端：高度=对数缩放后的总热度；颜色=热度最高的类别（伊朗/以色列/美/俄→军事，中国→经济，韩国→航空），不再 hash 随机
- 悬停光柱显示"热度 X · 主导：类别"

### 8. 推进路线图：中国省级下钻（commit `f5a3982`）
- 交互：点中国（全球视图）→ 面板出现"下钻到省份 →" → 拉近到 34 省、显示各省热度光柱 → 点省看该省综合前 8 条 → "← 返回全球"退出
- `assets/china-provinces.geojson`：DataV 阿里云省界（中文名+centroid，国内可访问），同域托管，**首次下钻才加载**
- `fetcher.fetch_cn_provinces()` → `news-cn.json`：每省一个"综合"查询取前 8 条。**省级热度坑**：单查询省名都撞 ~100 RSS 上限、无区分度 → 改用"近 12h 内发布条数"近似新闻速度（今日 12–76，不饱和）。复用 Google 解码+百度兜底。
- 前端加 `viewMode`（global/cn）状态机；省级光柱用更陡的高度曲线（区间窄）
- `daily.yml` 同时提交 `news-cn.json`；`_headers` 给它加 no-store
- **扩展到美/俄/日**：现在只需加各国省界 geojson + 省名→查询词映射，管道已通用化

### 8b. 下钻上线后修了三个渲染 bug（用户手机实测发现）
1. **点下钻就卡死** → DataV 省界全精度（34省2.5万顶点 vs 全部177国才1万），三角化+挤出+过渡动画把手机卡死。修：Douglas-Peucker 简化到 5887 点/140KB（commit `aa2e2ce`）+ `polygonsTransitionDuration(0)` 关过渡动画。省界文件加 `?v=2` 绕缓存（`9271cef`）。
2. **镜头糊满屏** → 下钻镜头高度 1.1/0.6 太近。改 1.7（总览）/1.2（点省）（`04ec283`）。
3. **整个中国一坨实心金色** → 每省半透明金色填充(0.12)叠在被照亮地表上糊成一片。修：省级面**不填充**(`capColor()` 在 cn 视图返回透明)，靠白描边+金光柱区分（`d5a435e`）。
- **验证法（重要）**：本机有 Playwright（全局，在 `@playwright/mcp/node_modules` 下）。无头浏览器开 `chrome` channel + `--no-proxy-server`（Clash 会拦 localhost）+ swiftshader 软件 WebGL，可截图肉眼查渲染 bug。注意 `world/viewMode/cnGeo` 是脚本作用域、不在 window 上；但 `enterCNDrill/selectProvince` 等函数声明是全局可调。

### 9. 今日 commit
`99e9f65` 抗竞争推送 → `6e95268` HANDOFF → `fb7a555` 时区+链接解码 → `1a5e46f` 光柱热度 → `f5a3982` 中国省级下钻 → `aa2e2ce`/`9271cef` 修卡死 → `04ec283` 修镜头 → `d5a435e` 修金色糊屏

---

## 二、文件清单（2026-05-29 状态）

```
C:\Users\zou18\globe-news\
├── .github\workflows\daily.yml       纯抓取+提交，5 档错峰 cron（微信/幂等已删）[今日精简]
├── .gitignore                          屏蔽 config.json / server.log / __pycache__
├── _headers                            CF Pages 缓存策略（news-data.json no-store）
├── assets\                             同域托管的外部资源
│   ├── countries.geojson               488 KB（国家级）
│   ├── china-provinces.geojson         582 KB（中国34省界，DataV，下钻用）[新]
│   ├── earth-night.jpg                 715 KB
│   ├── earth-topology.png              378 KB
│   └── night-sky.png                   904 KB
├── vendor\globe.gl.min.js              globe.gl 2.32.4 同域托管 (1 MB)
├── fetcher.py                          纯抓取（Actions 跑）；查询带 when:2d 近期过滤 [今日改]
├── server.py                           本地开发用，云端不启动
├── push.py                             [孤儿] 调 Server酱；workflow 已不调用，留作手动备用
├── index.html                          前端主页；新闻项现为可点击 <a> 链接 [今日改]
├── news-data.js                        静态 fallback 数据
├── news-data.json                      国家级实时数据，Actions 每天更新（含 _intensity 热度）
├── news-cn.json                        中国省级综合热点，Actions 每天更新，下钻时加载 [新]
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

### ✅ 2026-06-02 已解决：schedule 自动触发 + push 竞争
- **schedule 已确认能自动触发**：API 查到 43 个 run、`event=schedule` 成功提交（06-02 03:33/04:00 自动 refresh）。免费公共仓库 schedule 高延迟/批量爆发，但确实会跑——外部触发兜底**不再需要**。
- **修掉 push 竞争**（commit `99e9f65`）：冗余 cron 爆发触发导致第 7 步 `git push` 互撞 non-fast-forward（exit 1），即连日 "Run failed" 邮件根因。已改为被拒→同步最新 main→叠数据→重推（最多 5 次，单文件零冲突）。
- **怎么验收**：06-03 起观察那批失败邮件是否停了；或浏览器 https://github.com/LiLy2026wx/globe-news/actions 看 schedule run 是否全绿。

### 🛟 外部触发兜底（已不需要，留作万一退路）
- 若哪天 schedule 又罢工（连续两天 0 schedule run）：① cron-job.org 定时打 `workflow_dispatch`（需 fine-grained PAT，scope actions:write）② 本机计划任务跑 `fetcher.py`+push（setup_schedule.ps1，要求开机）③ CF Worker Cron（最稳但 fetcher 需重写 JS）

### 🆘 手动应急刷新（任何时候数据旧了）
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
1. ✅ 光柱高低差（已做，commit 1a5e46f：按新闻热度+对数缩放）
2. 省/州下钻：✅ 中国（commit f5a3982）；待扩展 美 50 州 / 俄联邦主体 / 日本都道府县（加各国省界 geojson + 省名→查询词映射即可，管道已通用化）
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

# === 手动触发一次 Actions 跑（无需任何输入）===
# 浏览器：Actions → Daily News Refresh → Run workflow → Run
# （微信推送已下线，已无 force_push 选项）

# === 本地手动跑一次抓取（验证 fetcher.py）===
cd C:\Users\zou18\globe-news
$env:PYTHONUTF8="1"
python fetcher.py
# 注：push.py / SCT_SENDKEY 已随微信推送下线作废，不要再用

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
2. 看 news-data.json 的 _generated 是不是当天 → 确认 schedule 自动跑了
3. 收到 "Run failed" 邮件别慌：先按第一节方法拆步骤（多半已被抗竞争推送自动解决）
4. 数据旧了随时手动应急刷新（第五节·🆘 命令）
5. 想做新东西 → 第六节路线图
```

**完。** 2026-06-02：定位并修复连日 "Run failed" 邮件根因（冗余 cron 撞 push non-fast-forward），改为抗竞争重推；同时确认 schedule 已能自动触发。项目进入**全自动稳定**状态，基本无待办。

---

## 九、归档：已死的 is-a.dev 路线（2026-05-29）

- PR #39517 状态：**closed, not merged**（2026-05-28T21:36:33Z）
- 拒绝理由：维护者 @dragsbruh "reason: not dev related"——is-a.dev 根级子域名必须软件开发相关，儿童时事地球仪不符
- `globe-news.is-a.dev` 不归属我们：访问 302 跳转 `https://is-a.dev/?d=globe-news`（未注册子域落地页）
- 教训：is-a.dev 只收开发相关项目；非开发项目要"微信可打开域名"得买真实域名或走 eu.org 等
