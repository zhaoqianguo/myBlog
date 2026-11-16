/**
 * 列表页、分页页里同日文章的顺序不稳定。
 *
 * hexo-generator-index / archive / category / tag 都拿 `locals.posts` 再
 * `sort('-date')`，日期相同的文章保留数据库里的原始顺序，而那个顺序取决于
 * 源文件的处理先后，每次 generate 都可能换。ES6 那批里两篇都是 2022-06-01，
 * 于是每一页列表里它们的位置会互换，分页页跟着抖。
 *
 * 这里在 generator 跑之前，把 posts 查询的底层数组按「日期倒序 + path 升序」
 * 排一次。后面各 generator 再用稳定排序按日期排，同日期就自然保持 path 序。
 */

'use strict'

const order = (a, b) => {
  const delta = b.date - a.date
  if (delta !== 0) return delta
  return a.path < b.path ? -1 : a.path > b.path ? 1 : 0
}

hexo.extend.filter.register('before_generate', () => {
  const posts = hexo.locals.get('posts')
  if (!posts || !posts.data) return

  // Query 内部就是普通数组，原地排序，后续 generator 共用同一份
  posts.data.sort(order)
})
