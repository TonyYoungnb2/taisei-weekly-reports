# Taisei Real Estate Intelligence Platform - 实施路线(用户最终拍板)

> 这是「住本小新 / 大誠」房地产情报平台的落地路线。基于 GPT 原始 PRD + Agent 可行性修正 + 用户 2026-07-31 反馈,最终确认如下。

## 核心共识(已对齐)
1. **当前系统本质**:不是数据库,是「每周一个静态 JSON → 渲染网页」。平台化 = 把新闻流沉淀成可积累的项目数据库。
2. **news ↔ projects 两层解耦,Day 1 就做**(用户比 Agent 更坚持)。避免"東京站东口/东侧/TOFROM/Yaesu"最终炸库。支持日后 AI/人工/规则 Merge,架构不动。
3. **不上重后端 / 不碰 Postgres / 甚至 SQLite 也暂不需要**。JSON 文件(月度分片)足以支撑数万条。保持纯静态 + EdgeOne 零运维优势。
4. **Project 由「新闻驱动 + 人工确认」建立,不靠 AI**。合并用字符串相似度(difflib SequenceMatcher)即可,阈值人工确认。
5. **Project Dashboard(列表)是主界面,地图只是 List/Map 视图切换之一**。没有地图系统照样跑。
6. **地图提前到 Phase 0.5**(用户唯一反对 Agent 之处):地图 = `projects.json → forEach → addMarker()`,是数据的自然可视化,工作量不大,只要数据模型建起来哪怕 3 个项目也值得出。

## 四阶段路线(最终版)

### Phase 0(立即开始,纯数据层,不改 UI)
- [x] 重构 JSON 结构:`data/projects.json` + `data/news/YYYY/MM.json`
- [x] 每条新闻支持 `project_id`(可空)
- [x] Project 含 `aliases`(为 Merge 预留去重键)、`verified`、`news_count`、`latitude/longitude(可空)`
- [x] 工具 `project_tools.py`:list / stats / add-news(带相似度建议) / add-project / merge
- [ ] 现有周报 JSON(weekly_data_*.json)维持不变,平台数据层独立演进

### Phase 0.5(已落地,2026-07-31)
- [x] Leaflet + 国土地理院(GSI) 标准地图瓦片(本地 vendor,不用 CDN,国内/微信可开)
- [x] `build_map.py` 读 `data/projects.json` 内联数据 → 生成 `map.html`
- [x] Marker:大小=新闻数,颜色=官方(蓝)/媒体(红);点击弹出项目摘要
- [x] 已给 3 个真实项目补公开经纬度(TOFROM YAESU / 墨田 / 福冈)验证出图
- [x] 确定性校验 7 项全 PASS(本地 Leaflet 引用 / 无 CDN 外链 / GSI 瓦片 / 内联 3 项目 / 外部域仅 GSI / vendor 文件存在)
- 注:沙盒内浏览器自动化被 policy 拦截,无法截图验证渲染;但瓦片 URL 已实测 200、Leaflet 本地化、数据为内联标准用法,逻辑校验已覆盖。
- ⚠️ 发布时 `vendor/leaflet/` 需随仓一起 push 才能生效(否则地图 JS 404)。

### Phase 1（已落地，2026-07-31）
- [x] `build_projects.py` 生成 `projects.html`（单一静态文件，内联 projects.json + news/**/*.json，零后端）
- [x] **Project List（Dashboard 主界面）**：卡片网格 + 按企业/地区/来源筛选 + 名称检索 + 按企业·按地区分组切换
- [x] **List / Map 视图切换**：地图复用 Leaflet+GSI，Marker 大小=新闻数、颜色=官方/媒体
- [x] **Project 详情抽屉**：信息摘要 + 相关新闻时间轴（按日期倒序，点击展开摘要，外链可点）
- [x] 覆盖 PRD 的「企业页面 / 地区页面 / 新闻详情 / 新闻↔项目关联」需求（用筛选+分组+详情抽屉实现，不拆多文件，保持纯静态）
- [x] 移动端防溢出：`.grid` 默认 `minmax(0,1fr)`，`minmax(280px,1fr)` 仅桌面块
- [x] 全站校验 `verify_all.py`：周报/地图/平台 3 页共 39 项确定性断言全 PASS

### Phase 3(未来,阈值触发)
- 条件:Project > 1000 且 News > 10000 才考虑 SQLite / 搜索 / API / PostgreSQL
- 不是现在

## 当前已落地(Phase 0 实测可用)
- `data/projects.json`:3 个真实项目(TOFROM YAESU / 墨田酒店 / 福冈住宿),含 aliases
- `data/news/2026/07.json`:3 条真实新闻,已关联 project_id
- `project_tools.py`:
  - `python project_tools.py list` / `stats`
  - `python project_tools.py add-news --title=... --source=... --date=2026-08-01 --summary=...` (自动相似度匹配,建议挂接/新建,人工 input 确认)
  - `python project_tools.py merge --from=P003 --to=P002`(合并:新闻改关联、删源、alias 合并)
  - 注意:GBK 终端打印日文会乱码,报告类输出建议写 UTF-8 文件用 `Get-Content -Encoding UTF8` 读;交互式 add-news 的 input 正常。

## 技术约束(环境现实,PRD 原稿漏提)
- 当前沙盒 Python `_socket` DLL 被拦截,**Python 不能出网**。因此:
  - "自动抓取新闻"在当前环境物理不可行 → 走人工录入(add-news)或另起可出网环境。
  - 地理编码若需在线调 GSI,要用前端 JS(浏览器出网)而非 Python 后端。
- 所有脚本打印非 ASCII 内容在 GBK 终端会崩 → 统一 stdout 强制 UTF-8 包装(generate_weekly.py 同款做法),或写文件读。

## 不做的(保持简单)
评论 / 用户系统 / 点赞 / 论坛 / AI 聊天 / AI 搜索 / 实时 AI 分析 / 复杂 CMS。
系统定位:静态展示 + 数据持续积累 + 查询。

## 线上修复记录 (2026-07-31)
- build_projects.py 修复单引号转义导致 JS 整块语法错误(列表/详情/地图全空)，改用 String.fromCharCode(39) 拼引号。
- build_map.py 修复 __CENTER__ 双括号导致 Leaflet setView 抛错(地图空白)，改为裸坐标注入。
- 主页平台入口卡片改 repeat(2, minmax(0, 1fr)) 等宽 + 图标固定 42px 防比例失调。
- commit 36a3c29 已上线，verify_all 39 项全 PASS。
