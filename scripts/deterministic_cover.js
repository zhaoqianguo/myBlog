/**
 * 让封面选择变成确定的。
 *
 * butterfly 的 random_cover.js 在 before_post_render 里用 Math.random() 取
 * default_cover 数组里的一张，副作用是每跑一次 hexo generate，所有没显式写
 * cover 的文章封面都会换一遍 —— 产物仓库因此整站都「有改动」，没法做增量比对。
 *
 * 这里在它之前（priority 比默认的 10 小）挂一个过滤器，按文章 path 派生一个
 * 稳定的下标，把 cover 直接写死。同一篇文章每次构建都拿到同一张图。
 */

'use strict'

function hash(str) {
  let h = 2166136261
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h)
}

hexo.extend.filter.register(
  'before_post_render',
  data => {
    // frontmatter 里写了 `cover:` 但留空时，Hexo 解析出来是 null 不是 undefined，
    // 所以这里只能按「有没有值」判断，不能拿 undefined 做哨兵。
    if (data.cover === false || data.cover) return data

    const { cover } = hexo.theme.config
    const list = cover && cover.default_cover
    if (!list || !Array.isArray(list) || list.length === 0) return data

    data.cover = list[hash(data.path || data.title || '') % list.length]
    return data
  },
  9
)
