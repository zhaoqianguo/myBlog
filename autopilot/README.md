# 每天一篇：这套东西怎么转

给未来的自己看的运维手册。什么时候坏了、坏了怎么修，看这份。

---

## 一次发布长什么样

```
草稿 drafts/2026-11-17.md
  ↓ voice_lint.py          （闸门，不过就不发）
  ↓ render.py              （同一份正文，渲两套 frontmatter）
  ├→ myBlog/source/_posts/2026-11-17-xxx.md
  └→ astro-blog/src/content/blog/2026-11-17-xxx.md
  ↓ hexo clean && generate （myBlog/public/）
  ↓ 与远端 gh-pages 逐文件比 blob sha，只推变化的
  ├→ gh-pages  走 GitHub Data API 批量提交   → https://zhaoqianguo.github.io/
  └→ astro main 走 GitHub Data API 提交      → Vercel 自动构建 → https://daxigua-crown.vercel.app/
  ↓ 本地 git commit（只提交，不 push）
  ↓ 写 ledger.json，回写 plan/{周}.md 的状态列
```

耗时实测：hexo 构建 4 秒，推 gh-pages 约 3 分钟（48 个 blob 一个个建），astro 20 秒。
**一次完整发布 3~4 分钟**，别在中途 Ctrl-C。

---

## 常用命令

```bash
cd /Users/zhaolanbaobao/Desktop/code/myBlog

python3 autopilot/publish.py --check                       # 今天该不该发、发了没
python3 autopilot/publish.py --date 2026-11-17 --dry-run   # 只过闸门和构建，不推
python3 autopilot/publish.py --date 2026-11-17             # 真发

python3 autopilot/voice_lint.py autopilot/drafts/2026-11-17.md   # 单跑闸门，看 JSON
python3 autopilot/weekly_plan.py --status                  # 本周七天进度
python3 autopilot/weekly_plan.py --check                   # 下周计划齐了没（周日跑）
python3 autopilot/weekly_plan.py --template 2026-W48       # 下周的空模板
python3 autopilot/compare_output.py                        # 本地 public/ 与远端 gh-pages 的差异

# 想暂停一天：建个 HOLD 文件，定时任务的提示词第一步会看它
touch autopilot/HOLD
```

---

## 为什么发布不用 git push

本机到 github.com 的 git 协议基本不通：`git fetch` 报
`RPC failed; curl 28 Failed to connect to github.com port 443 after 75002 ms`，
`git ls-remote` 三次里两次静默超时。

但 `api.github.com` 稳定 200。所以 `github_api.py` 走 Git Data API：
建 blob → 建 tree → 建 commit → PATCH ref。token 依次取 `GH_TOKEN`、`BLOG_PAT`、
`~/.git-credentials` 里的 github 那一行。

myBlog 那边只做本地 `git commit`，不 push。等哪天网络好了，`git push` 一把全上去。

---

## 为什么每次要重推 40 多个文件

远端 gh-pages 是好几年前的旧主题配置构建的（`標籤` 繁体、还留着已删除的 `messageboard/` 页面），
本地拿现在的配置一构建，每个页面的标签云顺序、`article:modified_time` 都会变。

选择接受这个成本：多推 48 个小 HTML 换确定性，比只推增量、让新旧页面主题不一致更划算。

**别开 `skip_deletions`**。删错一个页面比多留一个孤儿页糟糕得多。

---

## hexo 构建为什么要装那五个脚本

原来的 butterfly 主题+build 完全不幂等：连续两次构建，82 个产物里 45 个不一样。
六个来源，全在 `scripts/deterministic_*.js` 里掐掉了：

| 抖动来源 | 位置 | 处理 |
| --- | --- | --- |
| 随机封面 | `hexo-theme-butterfly/scripts/filters/random_cover.js:22` | `deterministic_cover.js` 按路径哈希定封面 |
| 相关推荐同权重无序 | `.../helpers/related_post.js` | `deterministic_related.js` 加 `path` 次级键 |
| 列表页 `postUpdate` 是构建时刻 | `.../layout/includes/head/config_site.pug:29` | `deterministic_dates.js` 补全站最新文章日期 |
| 最后更新时间 `date_xml(Date.now())` | `.../layout/includes/widget/card_webinfo.pug:33` | 同文件重注册 `date_xml` |
| 标签云配色随机 | `.../scripts/helpers/page.js:40` | `deterministic_tagcloud.js` 按名字哈希 |
| 上一篇/下一篇同日无序 | `hexo/lib/plugins/generator/post.js:12` | `deterministic_nav.js` 重算 prev/next |

两个坑记住：

1. **主题的 `scripts/` 在根目录 `scripts/` 之后加载**，直接 `register` 会被主题那份盖掉，
   必须包在 `hexo.on('generateBefore', ...)` 里。
2. **`cover:` 留空时 Hexo 解析成 `null` 不是 `undefined`**，判空要写 `if (data.cover === false || data.cover)`。

改完验证：

```bash
cd /Users/zhaolanbaobao/Desktop/code/myBlog
./node_modules/.bin/hexo clean && ./node_modules/.bin/hexo generate
cp -r public /tmp/pub1 && ./node_modules/.bin/hexo clean && ./node_modules/.bin/hexo generate
diff -r /tmp/pub1 public && echo 幂等
```

另外 `_config.yml` 的 `updated_option` 从 `mtime` 改成了 `date`——不改的话每页的
`article:modified_time` 会跟着本地文件时间乱跑。

---

## 时间是怎么定的

`common.py` 的 `pub_datetime()` 直接返回**此刻**（截到分钟）。

试过「20:00 往前推 0~45 分钟随机」，两个问题：一是手工提前发布时会算出未来时间，
AstroPaper 的 `scheduledPostMargin: 15min` 会把它当定时稿藏起来，而站点只在推送时构建一次，
藏起来就是永久隐藏；二是每篇都标 20:1x 的整分钟数，比不随机还假。

现在这样子，写多久决定发在几点，天然散在窗口里。

`jitter_minutes()` 还留着，没在用。

---

## 状态在哪

- `ledger.json` —— 发过什么，每条带两个 sha 和文件数。**排重就看这个**。
- `plan/2026-W47.md` —— 本周七天的计划，最后那列状态会被回写。
- `logs/daily.log` —— 每次跑的流水。

---

## 坏了怎么办

**闸门不通过**：看输出的 violations，一条条改。别去改 voice_lint.py 的规则来绕过。

**hexo 构建失败**：先 `npm ci`。构建完会检查 0 字节的 `index.html`，有就报错不出稿。

**gh-pages 推了一半**：Git Data API 是原子的（tree+commit+ref 分开 PATCH），
commit 没建成功就不会动 ref，远端还是上一次的样子。重跑一遍即可，是幂等的。

**astro 推了但 Vercel 没部署**：查
`/repos/zhaoqianguo/astro-blog/commits/{sha}/status`，`Vercel` context 是不是 success。
本机访问不到 `vercel.app`（DNS 被劫持、直连 IP 被 reset），只能用 API 看。

**想推 astro 的 node_modules 就重装**：`COREPACK_ENABLE_DOWNLOAD_PROMPT=0 pnpm install --frozen-lockfile`，
不然 `astro check` 会报 `Buffer<ArrayBufferLike>` 那个 `ts(2345)`。

---

## 已知没收拾的

- `_config.butterfly.yml:45` 还挂着 `留言板: /messageboard/`，页面早删了，是个死链。
- 远端 gh-pages 有 10 个孤儿文件（`messageboard/`、`categories/踩坑/` 等），没删。
