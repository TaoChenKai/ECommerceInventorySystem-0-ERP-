<template>
  <div
    class="theme-backdrop"
    :data-theme="theme"
    v-show="isEndfield"
    aria-hidden="true"
  >
    <!-- 主题背景图：谷地黄（白天）= 暖调实机图 bg_day_05.jpg / 武陵青（夜晚）= 废墟夜景 bg_night_01.jpg -->
    <div class="theme-bg-image"></div>

    <!-- 半透明遮罩：叠加主题色调（谷地黄=暖黄压暗中央 / 武陵青=青冷调），保证前景文字与表格可读 -->
    <div class="backdrop-veil"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const theme = ref(document.documentElement.dataset.theme || 'default')
const isEndfield = computed(
  () => theme.value === 'endfield-yellow' || theme.value === 'endfield-cyan'
)

let observer = null
onMounted(() => {
  observer = new MutationObserver(() => {
    theme.value = document.documentElement.dataset.theme || 'default'
  })
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  })
})
onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.theme-backdrop {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
/* 真实游戏截图背景层 */
.theme-bg-image {
  position: absolute;
  inset: 0;
  background-image: url('/backgrounds/endfield_space.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.backdrop-veil {
  position: absolute;
  inset: 0;
}
/* 谷地黄（亮 · 黄白黑 · 白天主题）：暖调官方实机图 bg_day_05.jpg
   中央区天然偏亮（平均亮度约 198/255），用暖黄主题色半透明遮罩
   压暗中央过亮区、四周保持通透，整体通透度中等偏淡 */
.theme-backdrop[data-theme="endfield-yellow"] .theme-bg-image {
  background-image: url('/backgrounds/bg_day_05.jpg');
  opacity: 0.65;
}
.theme-backdrop[data-theme="endfield-yellow"] .backdrop-veil {
  background:
    radial-gradient(ellipse 80% 72% at 50% 45%, rgba(150, 110, 55, 0.32), rgba(255, 250, 232, 0.10) 60%, rgba(255, 244, 210, 0.28)),
    linear-gradient(rgba(16, 17, 16, 0.05), rgba(16, 17, 16, 0.16));
}
/* 武陵青（暗 · 青绿黑 · 夜晚主题）：废墟夜景 bg_night_01.jpg + 青冷调遮罩，保住浅色文字可读 */
.theme-backdrop[data-theme="endfield-cyan"] .theme-bg-image {
  background-image: url('/backgrounds/bg_night_01.jpg');
  opacity: 0.85;
}
.theme-backdrop[data-theme="endfield-cyan"] .backdrop-veil {
  background:
    linear-gradient(rgba(8, 18, 20, 0.50), rgba(8, 18, 20, 0.28)),
    linear-gradient(rgba(20, 208, 208, 0.13), rgba(20, 208, 208, 0.05));
}
</style>
