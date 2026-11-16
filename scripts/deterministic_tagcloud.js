/**
 * 标签云的配色也是随机的。
 *
 * butterfly 的 cloudTags helper 给每个标签生成 `rgb(rand, rand, rand)`，
 * 于是每次 generate 标签云的颜色全换一遍，产物仓库里所有带侧栏的页面都在抖。
 *
 * 这里重写同一个 helper：颜色按标签名取哈希派生，字号算法照旧。
 * 另外顺带把没配 sort_order 时传给 sort 的 undefined 收成明确的 count 排序。
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

function cloudTags(options = {}) {
  const env = this
  let { source, minfontsize, maxfontsize, limit, unit, orderby, order } = options
  unit = unit || 'px'

  if (limit > 0) source = source.limit(limit)

  const sizes = []
  source.sort('length').forEach(tag => {
    if (!sizes.includes(tag.length)) sizes.push(tag.length)
  })

  const span = sizes.length - 1
  let result = ''

  // 同 count / 同长度的标签在仓库里本来就没有先后，必须自己补一个次级键，
  // 否则标签云里那几个标签每次构建都换位置。
  const dir = (order || -1) < 0 ? -1 : 1
  const key = orderby || 'count'
  const tags = source.toArray().sort((a, b) => {
    if (a[key] !== b[key]) return dir * (a[key] < b[key] ? -1 : 1)
    return a.name < b.name ? -1 : a.name > b.name ? 1 : 0
  })

  tags.forEach(tag => {
    const ratio = span ? sizes.indexOf(tag.length) / span : 0
    const size = minfontsize + (maxfontsize - minfontsize) * ratio
    // 色相从标签名派生，亮度压在中段，保证深浅两种主题下都读得清
    const h = hash(tag.name)
    const r = 90 + (h % 90)
    const g = 90 + ((h >> 8) % 90)
    const b = 90 + ((h >> 16) % 90)
    const style = `font-size: ${parseFloat(size.toFixed(2))}${unit}; color: rgb(${r}, ${g}, ${b})`
    result += `<a href="${env.url_for(tag.path)}" style="${style}">${tag.name}</a>`
  })

  return result
}

// 主题的 scripts/ 在根目录 scripts/ 之后加载，直接注册会被盖掉。
hexo.on('generateBefore', () => {
  hexo.extend.helper.register('cloudTags', cloudTags)
})
