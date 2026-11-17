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
  ↓ hexo clean && generate （本地构建只为自检：0 字节页、文章页没生成，当场拦下）
  ↓ 源码进 myBlog，推 origin master
  │    → GitHub Actions 跑 .github/workflows/deploy.yml
  │    → npm ci → hexo generate → 推 zhaoqianguo/zhaoqianguo.github.io 的 gh-pages
  │    → https://zhaoqianguo.github.io/
  ├→ astro 正文推到 astro-blog main
  │    → Vercel 自动构建
  │    → https://daxigua-crown.vercel.app/
  ↓ 写 ledger.json，回写 plan/{周}.md 的状态列
```

**部署全在线上，本地不产出 gh-pages 了。** 本地只做两件事：过闸门 + 把提交送出去。
好处是本机网络再抽风，只要提交能上去，构建和部署都不受影响；坏处是本地 `public/`
和线上不再是同一份构建（Node 版本、时区可能有细微差别），所以 `public/` 现在只是自检产物。

耗时：hexo 本地自检 4 秒，push 几秒到几十秒，Actions 构建约 40 秒，Vercel 约 30 秒。
**本机上的操作 1 分钟内结束**，线上构建自己跑，不用等。

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

本机到 github.com 的 git 协议时好时坏：坏的时候 `git fetch` 报
`RPC failed; curl 28 Failed to connect to github.com port 443 after 75002 ms`，
`git ls-remote` 三次里两次静默超时；好的时候（2026-11-16 实测）`git fetch` / `git push`
几十秒内就过。不能赌它通，所以两条路都留着。

`push_with_fallback()` 先试 3 次 `git push`（各 120s 超时），全失败才降级 Git Data API
（建 blob → 建 tree → 建 commit → PATCH ref，token 依次取 `GH_TOKEN`、`BLOG_PAT`、
`~/.git-credentials`）。降级后如果能 fetch 就把本地 `reset --hard` 对齐远端，避免下次
push 撞 non-fast-forward。两条都不通时打 ERROR、ledger 里记 `"failed"`，
重跑 `publish.py --force` 补上就行 —— 线上状态由 Actions 那边决定，不会因为本地失败而错乱。

查发布有没有真的上去：`gh_pages` 看 Actions 的 run 是不是 success，
astro 看 commit status 里的 `Vercel` context。

---

## 标签大小写：别写两个只差大小写的 tag

`source/_posts/ES6/` 那 14 篇原本 tags 同时写了 `ES6` 和 `es6`。Hexo 认成两个标签，
生成 `tags/ES6/` 和 `tags/es6/` 两份页面；而 macOS 文件系统大小写不敏感，本地 `public/`
只能存在一个目录，于是每次 `git status` 都有两个文件永久 modified，挡后续 pull。

已经修掉（只留 `ES6`），远端那两份 `tags/es6/` 也删了，并重建了一次站点让所有页面的
`/tags/es6/` 死链变成 `/tags/ES6/`。**以后写 tags 大小写要一致**。

---

## 为什么以前每次要重推 40 多个文件

远端 gh-pages 曾经是好几年前的旧主题配置构建的（`標籤` 繁体、还留着已删除的 `messageboard/` 页面），
本地拿现在的配置一构建，几乎每个页面都会变。2026-11-16 把六处抖动全掐掉之后，
本地 `public/` 和远端 gh-pages 已经逐文件一致（`compare_output.py` 报 `same=86 diff=0`），
孤儿页已清干净（`compare_output.py` 报 `remote_only=0`）。

**别开 `skip_deletions`**。删错一个页面比多留一个孤儿页糟糕得多。

---

## hexo 构建为什么要装那六个脚本

原来的 butterfly 主题+build 完全不幂等：连续两次构建，82 个产物里 45 个不一样。
七个来源，全在 `scripts/deterministic_*.js` 里掐掉了：

| 抖动来源 | 位置 | 处理 |
| --- | --- | --- |
| 随机封面 | `hexo-theme-butterfly/scripts/filters/random_cover.js:22` | `deterministic_cover.js` 按路径哈希定封面 |
| 相关推荐同权重无序 | `.../helpers/related_post.js` | `deterministic_related.js` 加 `path` 次级键 |
| 列表页 `postUpdate` 是构建时刻 | `.../layout/includes/head/config_site.pug:29` | `deterministic_dates.js` 补全站最新文章日期 |
| 最后更新时间 `date_xml(Date.now())` | `.../layout/includes/widget/card_webinfo.pug:33` | 同文件重注册 `date_xml` |
| 标签云配色随机 | `.../scripts/helpers/page.js:40` | `deterministic_tagcloud.js` 按名字哈希 |
| 上一篇/下一篇同日无序 | `hexo/lib/plugins/generator/post.js:12` | `deterministic_nav.js` 重算 prev/next |
| 列表页/分页页同日无序 | `hexo-generator-index\|archive\|category\|tag` 各自 `sort('-date')` | `deterministic_posts.js` 包住 `locals.posts` 的 getter，取一次排一次 |

三个坑记住：

1. **主题的 `scripts/` 在根目录 `scripts/` 之后加载**，直接 `register` 会被主题那份盖掉，
   必须包在 `hexo.on('generateBefore', ...)` 里。
2. **`cover:` 留空时 Hexo 解析成 `null` 不是 `undefined`**，判空要写 `if (data.cover === false || data.cover)`。
3. **`before_generate` 里拿到的 `locals.posts` 是缓存里的旧查询**（实测只有 2 条，每次还不一样），
   generator 在 `_runGenerators()` 开头会 `locals.invalidate()` 重新查库，排的根本不是同一份数据。
   要排就得包 getter：`const original = hexo.locals.getters.posts; hexo.locals.set('posts', () => sort(original()))`。

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

- `ledger.json` —— 发过什么，每条带 myBlog / astro 的 sha 和通道。**排重就看这个**。
  `status` 现在是 `pushed`（推上去了，部署由线上负责）。
- `plan/2026-W47.md` —— 本周七天的计划，最后那列状态会被回写。
- `logs/daily.log` —— 每次跑的流水。

---

## 坏了怎么办

**闸门不通过**：看输出的 violations，一条条改。别去改 voice_lint.py 的规则来绕过。

**hexo 构建失败**：先 `npm ci`。构建完会检查 0 字节的 `index.html`，有就报错不出稿。

**Actions 构建失败**：看 https://github.com/zhaoqianguo/myBlog/actions 那次 run 的日志。
最常见是 `npm ci` 失败（`package-lock.json` 与 `package.json` 不同步）或者本地能过、
CI 过不了的时区/大小写问题（Linux 大小写敏感，`tags/ES6` 与 `tags/es6` 这类问题在本地
macOS 上看不出来，CI 上会直接暴露成两个目录）。

**Actions 成功了但 Pages 没更新**：gh-pages 分支推成功不等于 Pages 重建，等 30 秒再看；
还不行就看 `zhaoqianguo.github.io` 仓库的 Pages 设置是不是还指着 `gh-pages` 分支根目录。

**astro 推了但 Vercel 没部署**：查
`/repos/zhaoqianguo/astro-blog/commits/{sha}/status`，`Vercel` context 是不是 success。

**本机 curl 打不开 vercel.app**：命令行走的是系统代理（系统设置里 `127.0.0.1:7897`），
但 shell 不继承它，所以要显式带上：

```bash
export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897
curl -s -o /dev/null -w '%{http_code}\n' https://daxigua-crown.vercel.app/
```

不带代理时 DNS 会返回劫持地址、直连 76.76.21.21 的 TLS 握手被 RST，看着像站点挂了，其实是本地没走代理。

**想推 astro 的 node_modules 就重装**：`COREPACK_ENABLE_DOWNLOAD_PROMPT=0 pnpm install --frozen-lockfile`，
不然 `astro check` 会报 `Buffer<ArrayBufferLike>` 那个 `ts(2345)`。

---

## 已知没收拾的

- `daxigua-crown.com` 没注册（Verisign whois 查无记录）。`SITE.website` 已改成
  `https://daxigua-crown.vercel.app`，等域名买了再换回去。
- 想从本机直接打开 Vercel 站点得走系统代理，见上面「坏了怎么办」那段。
