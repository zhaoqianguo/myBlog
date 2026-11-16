/**
 * 两处「写死为构建时刻」的时间戳，把它们钉死。
 *
 * 1. butterfly 的 config_site.pug 里写 `full_date(page.updated)`，而 Hexo 的
 *    full_date 遇到空值会取 moment() —— 列表页（首页、归档、标签、分类）都
 *    没有 updated，于是每跑一次 generate 全变一遍。
 * 2. card_webinfo.pug 里 `data-lastPushDate=date_xml(Date.now())`，直接就是
 *    构建那一刻。
 *
 * 两处都会让产物整站抖动，做不到「只提交真的变了的文件」。
 * 统一改用「全站最新一篇文章的日期」：内容最后一次变更是那天，语义也对。
 */

'use strict'

function latestPostDate() {
  const posts = hexo.locals.get('posts')
  if (!posts || !posts.length) return null
  return posts.sort('-date').first().date
}

hexo.extend.filter.register('template_locals', locals => {
  const page = locals.page
  if (!page || page.updated) return locals

  const latest = latestPostDate()
  if (latest) page.updated = latest
  return locals
})

// Date.now() 落在模板里，只能改模板拿到的那个变量 —— 直接替换 helper 更稳。
hexo.extend.helper.register('date_xml', function (date) {
  if (date == null || typeof date === 'number') {
    const latest = latestPostDate()
    date = latest || new Date(0)
  }
  const d = date instanceof Date ? date : new Date(date)
  return isNaN(d.getTime()) ? new Date(0).toISOString() : d.toISOString()
})
