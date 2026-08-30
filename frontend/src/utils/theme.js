// 设置中心 · 主题应用工具（SettingsDialog 与 App 全局初始化共用）
export const THEME_OPTIONS = [
  { key: 'default', name: '0号仓库', bg: 'linear-gradient(135deg,#0b0d1a,#1a1f3d)' },
  { key: 'day', name: '白昼', bg: 'linear-gradient(135deg,#eef1f7,#cfe0fb)' },
  { key: 'night', name: '暗夜', bg: 'linear-gradient(135deg,#0a0a0c,#23252b)' },
  { key: 'mint', name: '薄荷', bg: 'linear-gradient(135deg,#eaf6f1,#b9e4d5)' },
  { key: 'sun', name: '暖阳', bg: 'linear-gradient(135deg,#fdf3e7,#f8d9b8)' },
  { key: 'violet', name: '雾紫', bg: 'linear-gradient(135deg,#f3eefb,#dccdf5)' },
  { key: 'endfield-yellow', name: '终末地·谷地黄', bg: 'linear-gradient(135deg,#e8e8e2,#fff500)' },
  { key: 'endfield-cyan', name: '终末地·武陵青', bg: 'linear-gradient(135deg,#101110,#14d0d0)' }
]
const THEME_KEYS = THEME_OPTIONS.map((t) => t.key)

// 将用户偏好映射到实际生效的主题值
export function resolveThemeColor(theme, themeColor) {
  if (THEME_KEYS.includes(themeColor)) return themeColor
  if (theme === 'dark') return 'night'
  if (theme === 'light') return 'day'
  return 'default'
}

export function applyTheme(themeColor) {
  document.documentElement.setAttribute('data-theme', themeColor || 'default')
}

export function applyBg(bgImage) {
  const body = document.body
  if (bgImage) {
    body.classList.add('has-bg')
    body.style.setProperty('--bg-image', `url('/media/${bgImage}')`)
  } else {
    body.classList.remove('has-bg')
    body.style.removeProperty('--bg-image')
  }
}

export function applyPref(pref = {}) {
  const tc = resolveThemeColor(pref.theme, pref.theme_color)
  applyTheme(tc)
  applyBg(pref.bg_image || '')
}

// ---- 本地缓存兜底（刷新/重开在后端不可用时仍能恢复用户主题/背景）----
// 本机权威本地副本：键名 appThemePref，存 JSON {theme, theme_color, bg_image}
export const THEME_PREF_CACHE_KEY = 'appThemePref'

export function saveLocalPref(pref = {}) {
  try {
    const data = JSON.stringify({
      theme: pref.theme || 'light',
      theme_color: pref.theme_color || 'default',
      bg_image: pref.bg_image || ''
    })
    localStorage.setItem(THEME_PREF_CACHE_KEY, data)
  } catch (e) {
    /* localStorage 不可用（隐私模式/存储满）时静默，仅本次内存生效 */
  }
}

export function loadLocalPref() {
  try {
    const raw = localStorage.getItem(THEME_PREF_CACHE_KEY)
    if (!raw) return null
    const p = JSON.parse(raw)
    if (!p || typeof p !== 'object') return null
    return {
      theme: p.theme || 'light',
      theme_color: p.theme_color || 'default',
      bg_image: p.bg_image || ''
    }
  } catch (e) {
    return null
  }
}

// 后端返回的"纯默认"（等价于该用户在后端无偏好记录时的 GET 返回值）
// 用于“后端确无记录时保留本地缓存值”的判定
export function isDefaultPref(pref = {}) {
  return (pref.theme || 'light') === 'light' &&
    (pref.theme_color || 'default') === 'default' &&
    !(pref.bg_image || '')
}
