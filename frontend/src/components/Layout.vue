<template>
  <div class="layout" @mouseleave="closeSidebar">
    <ThemeBackdrop />
    <!-- 左缘热区：鼠标移入即展开侧栏 -->
    <div class="sidebar-hotzone" @mouseenter="openSidebar"></div>

    <aside
      class="sidebar"
      :class="expanded ? 'expanded' : 'collapsed'"
      @mouseenter="openSidebar"
      @mouseleave="closeSidebar"
    >
      <div class="logo">
        <span class="logo-star">✦</span>
        <div class="logo-text">
          <span>0号仓库</span>
          <small>INVENTORY SYSTEM</small>
        </div>
      </div>

      <nav>
        <router-link
          v-for="m in visibleStandalone"
          :key="m.to"
          :to="m.to"
          :title="m.label"
        >
          <span class="nav-icon" v-html="m.icon"></span>
          <span class="nav-text">{{ m.label }}</span>
        </router-link>
        <div v-for="g in visibleGroups" :key="g.title" class="nav-group">
          <div class="nav-group-title">{{ g.title }}</div>
          <router-link
            v-for="m in g.items"
            :key="m.to"
            :to="m.to"
            :title="m.label"
            class="group-item"
          >
            <span class="nav-icon" v-html="m.icon"></span>
            <span class="nav-text">{{ m.label }}</span>
          </router-link>
        </div>
      </nav>

      <div class="disclaimer-entry" title="免责声明">
        <button class="btn-disclaimer" @click="showDisclaimer">
          <span class="nav-icon">
            <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>
          </span>
          <span v-if="expanded" class="btn-txt">免责声明</span>
        </button>
      </div>

      <div class="user-box">
        <div class="uname" :title="userName">{{ userName }}</div>
        <div class="user-actions">
          <button class="btn-settings" title="设置" @click="showSettings">
            <span class="nav-icon">⚙</span><span v-if="expanded" class="btn-txt">设置</span>
          </button>
          <button class="btn-logout" title="退出登录" @click="logout">
            <span class="nav-icon">⏻</span><span v-if="expanded" class="btn-txt">退出</span>
          </button>
        </div>
        <div class="hud-gauge" aria-hidden="true">
          <svg width="128" height="46" viewBox="0 0 128 46" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M6 40 A58 58 0 0 1 122 40" />
            <path d="M16 40 A48 48 0 0 1 112 40" />
            <line x1="64" y1="0" x2="64" y2="40" />
            <line x1="32" y1="16" x2="32" y2="40" />
            <line x1="96" y1="16" x2="96" y2="40" />
            <circle cx="64" cy="40" r="3" fill="currentColor" stroke="none" />
          </svg>
        </div>
      </div>
    </aside>

    <main class="main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <SettingsDialog v-if="settingsOpen" @close="settingsOpen = false" />
    <DisclaimerDialog v-if="disclaimerOpen" @close="disclaimerOpen = false" />
    <StarField />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import SettingsDialog from './SettingsDialog.vue'
import DisclaimerDialog from './DisclaimerDialog.vue'
import StarField from './StarField.vue'
import ThemeBackdrop from './ThemeBackdrop.vue'

const auth = useAuthStore()
const router = useRouter()
const settingsOpen = ref(false)
const disclaimerOpen = ref(false)

const userName = computed(() => {
  const name = auth.user?.nickname || auth.user?.username || ''
  return `${name}（${auth.roleName || ''}）`
})

// 侧边栏动态收展：悬停展开 / 移出延时收回（热区与侧栏联动，避免误收抖动）
const expanded = ref(false)
let closeTimer = null
function openSidebar() {
  clearTimeout(closeTimer)
  expanded.value = true
}
function closeSidebar() {
  clearTimeout(closeTimer)
  closeTimer = setTimeout(() => {
    expanded.value = false
  }, 180)
}

// 菜单（代码自绘 SVG 图标，规避版权素材）
const ICONS = {
  home: '<svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>',
  products: '<svg viewBox="0 0 24 24"><path d="M21 8 12 3 3 8l9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/></svg>',
  scan: '<svg viewBox="0 0 24 24"><path d="M4 7V5a1 1 0 0 1 1-1h2"/><path d="M17 4h2a1 1 0 0 1 1 1v2"/><path d="M20 17v2a1 1 0 0 1-1 1h-2"/><path d="M7 20H5a1 1 0 0 1-1-1v-2"/><rect x="7" y="9" width="10" height="6"/></svg>',
  purchase: '<svg viewBox="0 0 24 24"><path d="M2 3h2l2.4 12.2A2 2 0 0 0 8.36 17h9.6a2 2 0 0 0 1.96-1.6L22 7H5.1"/><circle cx="9" cy="21" r="1.4"/><circle cx="18" cy="21" r="1.4"/></svg>',
  sales: '<svg viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
  logs: '<svg viewBox="0 0 24 24"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
  channels: '<svg viewBox="0 0 24 24"><circle cx="9" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 6.5 17 17.5"/><path d="M9 19h6"/></svg>',
  finance: '<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 14l3-3 3 2 5-6"/><path d="M18 7h2v3"/></svg>',
  analysis: '<svg viewBox="0 0 24 24"><path d="M21.2 15.9A10 10 0 1 1 8 2.8"/><path d="M22 12A10 10 0 0 0 12 2v10Z"/></svg>',
  label: '<svg viewBox="0 0 24 24"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r="1.2"/></svg>',
  users: '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  recycle: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
  audit: '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M9 13h6"/><path d="M9 17h6"/></svg>'
}

// v1.3.1 菜单分组：首页独立置顶，其余按「库存管理 / 运营分析 / 系统」分组
// 「商品回收站」作为「库存管理」分组下的二级子菜单（展开态缩进显示）
const standaloneMenus = [
  { to: '/', label: '首页', icon: ICONS.home, roles: null }
]
const menuGroups = [
  {
    title: '库存管理',
    items: [
      { to: '/products', label: '商品档案', icon: ICONS.products, roles: null },
      { to: '/recycle', label: '商品回收站', icon: ICONS.recycle, roles: ['boss', 'admin'] },
      { to: '/stock', label: '扫码出入库', icon: ICONS.scan, roles: null },
      { to: '/purchase', label: '采购入库', icon: ICONS.purchase, roles: null },
      { to: '/sales', label: '销售出库', icon: ICONS.sales, roles: null },
      { to: '/stock/logs', label: '出入库流水', icon: ICONS.logs, roles: null }
    ]
  },
  {
    title: '运营分析',
    items: [
      { to: '/channels', label: '渠道追踪', icon: ICONS.channels, roles: null },
      { to: '/finance', label: '财务对账', icon: ICONS.finance, roles: ['boss', 'admin'] },
      { to: '/analysis', label: '库存分析', icon: ICONS.analysis, roles: null }
    ]
  },
  {
    title: '系统',
    items: [
      { to: '/label-print', label: '标签打印', icon: ICONS.label, roles: null },
      { to: '/users', label: '账号权限', icon: ICONS.users, roles: ['boss', 'admin'] },
      { to: '/audits', label: '操作日志', icon: ICONS.audit, roles: ['boss', 'admin'] }
    ]
  }
]
const visibleStandalone = computed(() =>
  standaloneMenus.filter((m) => !m.roles || m.roles.includes(auth.user?.role))
)
const visibleGroups = computed(() =>
  menuGroups
    .map((g) => ({
      title: g.title,
      items: g.items.filter((m) => !m.roles || m.roles.includes(auth.user?.role))
    }))
    .filter((g) => g.items.length > 0)
)

function showSettings() {
  settingsOpen.value = true
}

function showDisclaimer() {
  disclaimerOpen.value = true
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
/* 免责声明入口（侧边栏底部，非 scoped 全局样式） */
.disclaimer-entry {
  padding: 6px 0 4px;
}
.disclaimer-entry .btn-disclaimer {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: transparent;
  color: var(--text-2);
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
  transition: all .18s;
}
.disclaimer-entry .btn-disclaimer .nav-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.disclaimer-entry .btn-disclaimer .nav-icon svg {
  width: 20px;
  height: 20px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.disclaimer-entry .btn-disclaimer:hover {
  border-color: var(--gold);
  color: var(--gold);
  background: rgba(226, 180, 92, 0.10);
}
/* 收起态：居中显示图标 */
.sidebar.collapsed .disclaimer-entry .btn-disclaimer {
  justify-content: center;
  width: 100%;
  padding: 0;
}
/* 终末地主题：对齐强调色 */
[data-theme^="endfield"] .disclaimer-entry .btn-disclaimer:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--nav-hover);
}
</style>
