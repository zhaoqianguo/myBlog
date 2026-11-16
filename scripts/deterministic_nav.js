/**
 * 上一篇 / 下一篇 的顺序不稳定。
 *
 * Hexo 的 post generator 用 `locals.posts.sort('-date')` 排完直接按下标取
 * 前后篇，日期相同的文章谁在前谁在后没有规定。ES6 那批里就有两篇都标着
 * 2022-06-01，于是每次 generate「上一篇」指的不是同一篇，页面跟着抖。
 *
 * 这里在渲染前重算一遍：日期倒序，日期相同按 path 排。拿不到 posts 时不动。
 */

'use strict'

hexo.extend.filter.register('template_locals', locals => {
  const page = locals.page
  if (!page || !page.__post) return locals

  const posts = hexo.locals.get('posts')
  if (!posts || !posts.length) return locals

  const ordered = posts.toArray().sort((a, b) => {
    const delta = b.date - a.date
    if (delta !== 0) return delta
    return a.path < b.path ? -1 : a.path > b.path ? 1 : 0
  })

  const i = ordered.findIndex(p => p.path === page.path)
  if (i === -1) return locals

  page.prev = i > 0 ? ordered[i - 1] : undefined
  page.next = i < ordered.length - 1 ? ordered[i + 1] : undefined
  return locals
})
