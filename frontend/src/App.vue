<template>
  <router-view v-slot="{ Component }">
    <transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { settingsApi } from './api'
import { applyPref, loadLocalPref, saveLocalPref, isDefaultPref } from './utils/theme'

const route = useRoute()

// 登录进入系统后，应用该用户的全局主题/背景图偏好（换设备一致）
// 双保险：先应用本地缓存避免闪烁回默认，再异步请求后端校准；
// 后端失败/超时时保留本地值继续使用，不得静默回默认。
watch(
  () => route.path,
  async (path) => {
    if (path !== '/login' && localStorage.getItem('token')) {
      // 1) 本地缓存先立即应用（首个用户在后端无记录时也有效）
      const local = loadLocalPref()
      if (local) applyPref(local)

      // 2) 后端校准：成功后以后端为准并覆盖本地缓存
      try {
        const pref = await settingsApi.preference()
        if (isDefaultPref(pref) && local) {
          // 后端该用户确无记录时，保留本地缓存值继续使用
          applyPref(local)
        } else {
          applyPref(pref)
          saveLocalPref(pref)
        }
      } catch (e) {
        // 后端不可用/超时：保留本地缓存值（若本地也无，维持默认），温和提示
        if (local) {
          // eslint-disable-next-line no-console
          console.warn('[theme] 后端偏好校准失败，沿用本地缓存主题：', e?.message || e)
        }
      }
    }
  },
  { immediate: true }
)
</script>
