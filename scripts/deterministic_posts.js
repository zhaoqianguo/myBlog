/**
 * 列表页、分页页里同日文章的顺序不稳定。
 *
 * hexo-generator-index / archive / category / tag 都拿 `locals.posts` 再
 * `sort('-date')`，日期相同的文章保留数据库里的原始顺序，而那个顺序取决于
 * 源文件的处理先后，每次 generate 都可能换。ES6 那批里两篇都是 2022-06-01，
 * 于是每一页列表里它们的位置会互换，分页页跟着抖。
 *
 * 为什么不在 `before_generate` 里排：那个时机拿到的 `locals.posts` 是缓存里的
 * 一份旧查询（实测只有两条，而且每次是哪两条都不一样），而 generator 在
 * `_runGenerators()` 开头会 `locals.invalidate()` 重新查一遍库，排到的根本不是
 * 同一份数据。
 *
 * 所以改成包一层 getter：generator 每次取 `locals.posts` 都先按
 * 「日期倒序 + path 升序」排一次，它后面再用（V8 里 Array#sort 是稳定排序）
 * 按日期排时就保住了同日期文章的 path 顺序。
 */

'use strict'

const order = (a, b) => {
  const delta = b.date - a.date
  if (delta !== 0) return delta
  return a.path < b.path ? -1 : a.path > b.path ? 1 : 0
}

const sortQuery = query => {
  if (query && Array.isArray(query.data)) query.data.sort(order)
  return query
}

const original = hexo.locals.getters.posts

if (typeof original === 'function') {
  hexo.locals.set('posts', () => sortQuery(original()))
}
