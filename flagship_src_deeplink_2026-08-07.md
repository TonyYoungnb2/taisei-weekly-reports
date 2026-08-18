# 旗舰项目来源链接深链化（2026-08-07）

## 目标
用户拍板：约 18 个旗舰项目换真实官方/新闻深链，其余 80+ 项目保留 Bing 兜底。

## 本批落地（8 个，全部 HTTP 200 验证）
| 项目 | 开发商 | 替换为 |
|---|---|---|
| P004 六本木五丁目西地区（ローズウッド東京） | 住友不動産 | https://www.sumitomo-rd.co.jp/news/ |
| P008 都立明治公園 Park-PFI | 三井物産 | https://www.mitsui.com/jp/ja/topics/2022/1242772_13393.html |
| P011 (仮称)M計画／MUFG 本館 | 三菱UFJ | https://www.mufg.jp/pressrelease/index.html |
| P017 築地地区まちづくり事業 | 三井不動産等 | https://www.fashion-press.net/news/117871 |
| P018 ALFALINK 東京昭島 | 日本GLP | https://www.glp.com.cn/news/company/403.html |
| P047 日本郵船 横浜タワー棟 | 日本郵船 | https://www.nyk.com/news/2023/20230711_01.html |
| P049 みなとみらい21中央地区52街区 | 横浜・事業者 | https://www.travelvoice.jp/20220617-151454 |
| P051 ハーバーステージ横浜北仲 | 東急・京急・第一生命 | https://shutten-watch.com/kantou/27587 |

## 保持 Bing 兜底
- 其余 97 个项目（含 P007/P019/P020/P046/P072/P085/P087/P098/P105/P106 等）仍用逐项目 Bing 搜索链接——这些多为小/碎片化项目，无干净单一权威来源。
- 既有的 9 个优质深链（P001/P005/P006/P009/P010/P013/P014/P015/P016）不动。

## 流程
1. `_update_src.py` 仅替换 source_url 中仍为 Bing 的 8 条（防误改既有深链）。
2. `build_projects.py` + `build_map.py` 重新生成 projects.html / map.html。
3. `build_search.py` 重建 Pagefind 索引。
4. `verify_all.py` → 45 PASS / 0 FAIL。
5. `publish.py` 推送（fetch+merge+push master:main），commit `79c970f`（ea61715..79c970f）。
6. EdgeOne 线上验证（cache-buster）：8 条深链全部命中，HTTP 200。

## 备注
- GLP 仅有中文官方页（glp.com.cn）可用，日文源被微博/企鹅号噪音淹没，故保留中文官方。
- 仓库结构：源链接只存于 `data/projects.json`（不在生成器内），故改数据文件 + 重生成即可。
- 临时调试脚本已全部清理，git 工作树干净。
