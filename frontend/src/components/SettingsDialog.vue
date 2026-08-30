<template>
  <teleport to="body">
    <div class="settings-mask" @click.self="$emit('close')">
      <div class="settings-dialog">
        <div class="settings-head">
          <span class="settings-title">设置中心</span>
          <button class="settings-close" @click="$emit('close')">✕</button>
        </div>
        <div class="settings-body">
          <!-- UI 外观 -->
          <div class="settings-section">
            <h4>UI 外观</h4>
            <div class="settings-row">
              <span class="label">主题色板</span>
              <div class="theme-palette">
                <button
                  v-for="t in THEME_OPTIONS"
                  :key="t.key"
                  class="theme-swatch"
                  :class="{ active: themeColor === t.key }"
                  :style="{ background: t.bg }"
                  :title="t.name"
                  @click="pickTheme(t.key)"
                />
              </div>
            </div>
            <div class="settings-row">
              <span class="label">亮暗模式</span>
              <div class="mode-group">
                <button class="mode-btn" :class="{ active: mode === 'light' }" @click="pickMode('light')">亮色</button>
                <button class="mode-btn" :class="{ active: mode === 'dark' }" @click="pickMode('dark')">暗色</button>
                <button class="mode-btn" :class="{ active: mode === 'random' }" @click="pickRandom">随机</button>
              </div>
            </div>
            <div class="settings-row">
              <span class="label">背景图</span>
              <div class="bg-actions">
                <label class="bg-upload">
                  上传本地图片
                  <input type="file" accept=".png,.jpg,.jpeg,.webp,.gif,.bmp" @change="onBgFile" />
                </label>
                <button v-if="bgImage" class="bg-remove" @click="removeBg">移除背景</button>
              </div>
              <div v-if="bgImage" class="bg-preview">
                <img :src="`/media/${bgImage}`" alt="背景预览" />
              </div>
            </div>
          </div>

          <!-- 数据存储位置（仅 boss / 管理员） -->
          <div v-if="isBossOrAdmin" class="settings-section">
            <h4>数据存储位置</h4>
            <div class="storage-info">
              <div>数据目录：<span>{{ storage.data_dir || '加载中…' }}</span></div>
              <div>数据库文件：<span>{{ storage.db_path || '-' }}</span></div>
              <div>媒体目录：<span>{{ storage.media_dir || '-' }}</span></div>
              <div>数据库大小：<span>{{ fmtSize(storage.db_size) }}</span></div>
            </div>
            <div class="settings-row">
              <span class="label">迁移到</span>
              <input v-model="newDir" class="dir-input" placeholder="例如 D:\inventory-data（仅本机 SQLite 安全迁移）" />
              <button class="migrate-btn" :disabled="migrating" @click="migrate">
                {{ migrating ? '迁移中…' : '开始迁移' }}
              </button>
            </div>
            <div class="muted">迁移将自动备份、校验并在失败时回滚，迁移成功后旧数据目录内容会被清空（备份保留）。</div>
          </div>

          <!-- 员工管理（仅 boss / 管理员） -->
          <div v-if="isBossOrAdmin" class="settings-section">
            <h4>员工管理</h4>
            <div class="settings-row">
              <span class="label">账号与权限</span>
              <button class="migrate-btn" @click="goUsers">管理员工 / 添加新员工</button>
            </div>
          </div>

          <!-- 云端备份（占位） -->
          <div class="settings-section">
            <h4>云端备份</h4>
            <div class="cloud-placeholder">
              <p>云端备份功能预留端口，将在后续版本开放。</p>
              <button disabled>暂未开放</button>
            </div>
          </div>

          <div v-if="msg" class="settings-msg" :class="msgType">{{ msg }}</div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { settingsApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { THEME_OPTIONS, resolveThemeColor, applyTheme, applyBg, saveLocalPref } from '../utils/theme'

const emit = defineEmits(['close'])
const router = useRouter()

const auth = useAuthStore()
const isBossOrAdmin = computed(() => auth.isBoss || auth.isAdmin)

const mode = ref('light')
const themeColor = ref('default')
const bgImage = ref('')

const storage = ref({})
const newDir = ref('')
const migrating = ref(false)

const msg = ref('')
const msgType = ref('ok')

const RANDOM_POOL = ['day', 'night', 'mint', 'sun', 'violet', 'endfield-yellow', 'endfield-cyan']

function showMsg(text, type = 'ok') {
  msg.value = text
  msgType.value = type
  setTimeout(() => { msg.value = '' }, 4000)
}

function goUsers() {
  emit('close')
  router.push('/users')
}

function pickTheme(key) {
  themeColor.value = key
  // 同步亮暗模式（终末地武陵青为深色，谷地黄为浅色）
  if (['default', 'night', 'endfield-cyan'].includes(key)) mode.value = 'dark'
  else mode.value = 'light'
  applyTheme(key)
  savePref()
}

function pickMode(m) {
  mode.value = m
  const target = m === 'dark' ? 'night' : m === 'light' ? 'day' : RANDOM_POOL[Math.floor(Math.random() * RANDOM_POOL.length)]
  themeColor.value = target
  applyTheme(target)
  savePref()
}

function pickRandom() {
  const target = RANDOM_POOL[Math.floor(Math.random() * RANDOM_POOL.length)]
  mode.value = 'random'
  themeColor.value = target
  applyTheme(target)
  savePref()
}

async function savePref() {
  try {
    await settingsApi.savePreference({ theme: mode.value, theme_color: themeColor.value, bg_image: bgImage.value })
    // 后端保存成功后，同步写本地缓存（唯一权威本地副本）
    saveLocalPref({ theme: mode.value, theme_color: themeColor.value, bg_image: bgImage.value })
  } catch (e) {
    showMsg('偏好保存失败：' + (e.response?.data?.detail || e.message), 'err')
  }
}

async function onBgFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const res = await settingsApi.uploadBg(file)
    bgImage.value = res.filename || ''
    applyBg(bgImage.value)
    savePref()
    showMsg('背景图已上传并生效')
  } catch (err) {
    showMsg('上传失败：' + (err.response?.data?.detail || err.message), 'err')
  } finally {
    e.target.value = ''
  }
}

async function removeBg() {
  try {
    await settingsApi.removeBg()
    bgImage.value = ''
    applyBg('')
    savePref()
    showMsg('已移除背景图')
  } catch (err) {
    showMsg('移除失败：' + (err.response?.data?.detail || err.message), 'err')
  }
}

function fmtSize(bytes) {
  if (!bytes && bytes !== 0) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(2) + ' MB'
}

async function migrate() {
  const dir = newDir.value.trim()
  if (!dir) { showMsg('请填写目标数据目录', 'err'); return }
  migrating.value = true
  try {
    const res = await settingsApi.migrate(dir)
    storage.value = { ...storage.value, ...res }
    showMsg('迁移成功，数据目录已切换为：' + res.data_dir)
  } catch (err) {
    showMsg('迁移失败：' + (err.response?.data?.detail || err.message), 'err')
  } finally {
    migrating.value = false
  }
}

onMounted(async () => {
  try {
    const pref = await settingsApi.preference()
    mode.value = pref.theme || 'light'
    themeColor.value = resolveThemeColor(pref.theme, pref.theme_color)
    bgImage.value = pref.bg_image || ''
    applyTheme(themeColor.value)
    applyBg(bgImage.value)
    // 后端成功以后端为准，并校准本地缓存保持换设备一致
    saveLocalPref({ theme: mode.value, theme_color: themeColor.value, bg_image: bgImage.value })
  } catch (e) { /* 静默：偏好接口异常时保留默认主题 */ }

  if (isBossOrAdmin.value) {
    try {
      storage.value = await settingsApi.storage()
      newDir.value = ''
    } catch (e) { /* 存储信息加载失败忽略 */ }
  }
})
</script>
