/**
 * 相关推荐的顺序也是随机的。
 *
 * butterfly 的 related_posts helper 只按 weight 排序，权重相同的那几篇保留
 * 「遍历到它们的顺序」，而遍历源是 site.posts —— 两篇日期完全相同的文章
 * 谁先谁后没有保证（一次 generate 里 ES6 那批同一天发的文章就撞上了）。
 * 结果是每次构建「相关推荐」里出现的文章不同，产物仓库跟着整站抖动。
 *
 * 这里重注册同一个 helper，排序时多带一个 path 作为次级键，彻底锁死顺序。
 */

'use strict'

function isTagRelated(tagName, tags) {
  return tags.some(tag => tagName === tag.name)
}

function relatedPosts (currentPost, allPosts) {
  const related = []
  const indexByPath = new Map()

  currentPost.tags.forEach(tag => {
    allPosts.forEach(post => {
      if (!isTagRelated(tag.name, post.tags)) return
      if (post.path === currentPost.path) return

      if (indexByPath.has(post.path)) {
        related[indexByPath.get(post.path)].weight += 1
        return
      }

      indexByPath.set(post.path, related.length)
      related.push({
        title: post.title,
        path: post.path,
        cover: post.cover,
        cover_type: post.cover_type,
        weight: 1,
        updated: post.updated,
        created: post.date
      })
    })
  })

  if (related.length === 0) return ''

  related.sort((a, b) => {
    if (b.weight !== a.weight) return b.weight - a.weight
    return a.path < b.path ? -1 : a.path > b.path ? 1 : 0
  })

  const limitNum = hexo.theme.config.related_post.limit || 6
  const dateType = hexo.theme.config.related_post.date_type || 'created'
  const headlineLang = this._p('post.recommend')

  let result = '<div class="relatedPosts">'
  result += `<div class="headline"><i class="fas fa-thumbs-up fa-fw"></i><span>${headlineLang}</span></div>`
  result += '<div class="relatedPosts-list">'

  related.slice(0, limitNum).forEach(item => {
    const cover = item.cover || 'var(--default-bg-color)'
    const title = this.escape_html(item.title)
    result += `<div><a href="${this.url_for(item.path)}" title="${title}">`
    if (item.cover_type === 'img') {
      result += `<img class="cover" src="${this.url_for(cover)}" alt="cover">`
    } else {
      result += `<div class="cover" style="background: ${cover}"></div>`
    }
    const when = dateType === 'created' ? item.created : item.updated
    const icon = dateType === 'created' ? 'far fa-calendar-alt' : 'fas fa-history'
    result += `<div class="content is-center"><div class="date"><i class="${icon} fa-fw"></i> ${this.date(when, hexo.config.date_format)}</div>`
    result += `<div class="title">${title}</div>`
    result += '</div></a></div>'
  })

  result += '</div></div>'
  return result
}

// 主题的 scripts/ 比根目录 scripts/ 后加载，直接注册会被主题那份盖掉。
// 等所有脚本都装完（generateBefore）再盖回去。
hexo.on('generateBefore', () => {
  hexo.extend.helper.register('related_posts', relatedPosts)
})
