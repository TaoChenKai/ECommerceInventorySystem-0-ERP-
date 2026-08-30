<template>
  <div class="login-page">
    <!-- 终末地黄白黑工业风品牌加载动画（约 2.9s：填充 1750ms → 铺满 520ms → 淡出 620ms） -->
    <div v-if="booting" class="boot-loader" :class="{ pulsing, fading }">
      <div class="boot-frame">
        <div class="boot-gauge" aria-hidden="true">
          <div class="boot-fill" :style="{ height: pct + '%' }"></div>
          <div class="boot-ticks"></div>
        </div>
        <div class="boot-body">
          <div class="boot-brand">
            <span class="boot-brand-main">0号仓库库存管理系统</span>
            <small class="boot-brand-sub">INVENTORY SYSTEM</small>
          </div>
          <div class="boot-status-row">
            <span class="boot-status">{{ statusText }}</span>
            <span class="boot-pct">{{ pct }}%</span>
          </div>
          <div class="boot-hline"></div>
        </div>
      </div>
    </div>

    <!-- 登录表单（加载动画结束后逐元素入场；不同意免责时替换为不可用提示） -->
    <div v-if="denied" class="deny-box">
      <div class="deny-mark">!</div>
      <div class="deny-title">无法进入系统</div>
      <div class="deny-desc">
        您不同意本系统的免责声明，将无法登录与使用本系统。<br />
        如需使用，请重新打开登录页并在免责声明弹窗中选择「我同意」。
      </div>
      <button class="deny-retry" type="button" @click="onDisclaimerRetry">重新阅读免责声明</button>
    </div>
    <div v-else class="login-box" :class="{ show: !booting }">
      <div class="login-title">0号仓库库存管理系统</div>
      <div class="login-sub">0号仓库 · 多端互通库存管理平台</div>
      <div class="login-divider"></div>
      <form @submit.prevent="doLogin">
        <input v-model="username" type="text" placeholder="账号" autocomplete="username" />
        <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" />
        <button type="submit" :disabled="loading">{{ loading ? '登录中…' : '登 录' }}</button>
        <p v-if="error" class="login-error">{{ error }}</p>
      </form>
      <div class="login-footer">0号仓库库存管理系统 · E-Commerce Inventory System v1.3.1</div>
    </div>

    <StarField />

    <!-- 首次登录强制免责声明弹窗（不支持关闭/点击遮罩，必须表态） -->
    <DisclaimerDialog
      v-if="disclaimerForced"
      forced
      @confirm="onDisclaimerConfirm"
      @cancel="onDisclaimerCancel"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import StarField from '../components/StarField.vue'
import DisclaimerDialog from '../components/DisclaimerDialog.vue'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

// ---- 免责声明：首次安装/重装/清除缓存后强制弹窗 ----
const DISCLAIMER_KEY = 'disclaimerAccepted_v1'
const disclaimerForced = ref(false)
const denied = ref(false)

function checkDisclaimer() {
  if (localStorage.getItem(DISCLAIMER_KEY)) return
  disclaimerForced.value = true
}
function onDisclaimerConfirm() {
  localStorage.setItem(DISCLAIMER_KEY, '1')
  disclaimerForced.value = false
}
function onDisclaimerCancel() {
  disclaimerForced.value = false
  denied.value = true
  // 不同意则不使用：尝试关闭窗口，无法关闭时停留在不可用提示页
  try { window.close() } catch (e) { /* 忽略 */ }
}
function onDisclaimerRetry() {
  // 误点"我不同意"后的恢复入口：重新弹出免责声明选择，避免永久卡死无法返回登录
  denied.value = false
  disclaimerForced.value = true
}

// ---- 加载动画（墙钟时间推导，防漂移）----
const booting = ref(true)
const pulsing = ref(false)
const fading = ref(false)
const pct = ref(0)
const statusText = ref('系统自检中…')
let raf = 0
const T_FILL = 1750
const T_FULL = 520
const T_FADE = 620

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

function statusFor(p) {
  if (p < 30) return '系统自检中…'
  if (p < 60) return '加载库存数据…'
  if (p < 90) return '同步星云档案…'
  return '初始化完成'
}

function frame(now) {
  const el = now - (window.__bootT0 || 0)
  if (el < T_FILL) {
    const p = Math.round(100 * easeOutCubic(el / T_FILL))
    pct.value = p
    statusText.value = statusFor(p)
    raf = requestAnimationFrame(frame)
  } else if (el < T_FILL + T_FULL) {
    pct.value = 100
    statusText.value = '初始化完成'
    pulsing.value = true
    raf = requestAnimationFrame(frame)
  } else if (el < T_FILL + T_FULL + T_FADE) {
    if (!fading.value) fading.value = true
    raf = requestAnimationFrame(frame)
  } else {
    booting.value = false
  }
}

onMounted(() => {
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce) {
    booting.value = false
    return
  }
  window.__bootT0 = performance.now()
  raf = requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
})

// 加载动画结束（booting 变 false）后才弹出强制免责声明，避免被 boot-loader(z-index 10000)遮挡
watch(booting, (b) => {
  if (!b) {
    nextTick(() => checkDisclaimer())
  }
})

// ---- 登录 ----
async function doLogin() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 登录页固定终末地黄白黑工业风（登录前不随主题切换） */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
  overflow: hidden;
  padding: 20px;
  background:
    radial-gradient(circle at 50% 38%, rgba(255, 245, 0, 0.07), transparent 62%),
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    #0d0d0c;
  background-size: 100% 100%, 44px 44px, 44px 44px, 100% 100%;
}
/* 四角工业角标（HUD） */
.login-page::before {
  content: "";
  position: absolute;
  inset: 18px;
  z-index: 0;
  pointer-events: none;
  background:
    linear-gradient(#fff500, #fff500) left top / 26px 2px no-repeat,
    linear-gradient(#fff500, #fff500) left top / 2px 26px no-repeat,
    linear-gradient(#fff500, #fff500) right top / 26px 2px no-repeat,
    linear-gradient(#fff500, #fff500) right top / 2px 26px no-repeat,
    linear-gradient(rgba(255, 245, 0, 0.7), rgba(255, 245, 0, 0.7)) left bottom / 26px 2px no-repeat,
    linear-gradient(rgba(255, 245, 0, 0.7), rgba(255, 245, 0, 0.7)) left bottom / 2px 26px no-repeat,
    linear-gradient(rgba(255, 245, 0, 0.7), rgba(255, 245, 0, 0.7)) right bottom / 26px 2px no-repeat,
    linear-gradient(rgba(255, 245, 0, 0.7), rgba(255, 245, 0, 0.7)) right bottom / 2px 26px no-repeat;
  opacity: 0.55;
}
/* 扫描线 */
.login-page::after {
  content: "";
  position: absolute;
  left: 0; right: 0;
  top: 0;
  height: 90px;
  z-index: 0;
  pointer-events: none;
  background: linear-gradient(to bottom, rgba(255, 245, 0, 0.05), transparent);
  animation: scanMove 5s linear infinite;
}
@keyframes scanMove {
  0% { transform: translateY(-90px); }
  100% { transform: translateY(100vh); }
}

/* ---------- 加载屏 ---------- */
.boot-loader {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: #0d0d0c;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  transition: opacity 0.62s ease;
}
.boot-loader.fading { opacity: 0; }
.boot-loader.pulsing::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 50%, rgba(255, 245, 0, 0.10), transparent 55%);
  animation: bootPulse 0.52s ease-in-out infinite alternate;
}
@keyframes bootPulse {
  from { opacity: 0.3; }
  to { opacity: 1; }
}
.boot-frame {
  display: flex;
  gap: 30px;
  align-items: stretch;
  width: 380px;
}
/* 左缘竖轨 */
.boot-gauge {
  position: relative;
  width: 10px;
  background: #2a2a27;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
}
.boot-fill {
  position: absolute;
  left: 0; right: 0; top: 0;
  height: 0;
  background: #fff500;
  box-shadow: 0 0 14px rgba(255, 245, 0, 0.55);
}
.boot-ticks {
  position: absolute;
  left: -9px; right: -9px;
  top: 0; bottom: 0;
  background:
    repeating-linear-gradient(to bottom, transparent 0, transparent 46px, #3c3c36 46px, #3c3c36 47px),
    repeating-linear-gradient(to bottom, transparent 0, transparent 23px, rgba(255, 245, 0, 0.25) 23px, rgba(255, 245, 0, 0.25) 24px);
}
/* 右侧品牌块 */
.boot-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.boot-brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.boot-brand-main {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 6px;
  color: #fff500;
  text-shadow: 0 0 22px rgba(255, 245, 0, 0.35);
}
.boot-brand-sub {
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 7px;
  color: #e6e6e0;
}
.boot-status-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 34px;
}
.boot-status {
  font-size: 12px;
  color: #b8b8b0;
  letter-spacing: 2px;
}
.boot-pct {
  font-size: 26px;
  font-weight: 700;
  color: #fff500;
  font-variant-numeric: tabular-nums;
}
.boot-hline {
  margin-top: 14px;
  height: 2px;
  background: linear-gradient(90deg, #fff500, transparent);
  opacity: 0.5;
}

/* ---------- 登录表单（终末地工业风） ---------- */
.login-box {
  position: relative;
  z-index: 2;
  width: 408px;
  padding: 42px 38px 34px;
  background: rgba(20, 20, 18, 0.88);
  border: 1px solid rgba(255, 245, 0, 0.35);
  border-radius: 0;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.7), inset 0 0 40px rgba(255, 245, 0, 0.03);
}
.login-box::before {
  content: "";
  position: absolute;
  top: -1px; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #fff500, transparent);
}
.login-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 2px;
  text-align: center;
  color: #fff500;
}
.login-sub {
  margin-top: 10px;
  text-align: center;
  color: #b8b8b0;
  font-size: 13px;
  letter-spacing: 1px;
}
.login-divider {
  height: 1px;
  margin: 26px 0 22px;
  background: linear-gradient(90deg, transparent, rgba(255, 245, 0, 0.4), transparent);
}
.login-box input {
  width: 100%;
  height: 44px;
  margin-bottom: 14px;
  padding: 0 14px;
  border-radius: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.05);
  color: #f2f2ec;
  font-size: 15px;
  outline: none;
  transition: border-color .2s, box-shadow .2s;
}
.login-box input::placeholder { color: #6e6e66; }
.login-box input:focus {
  border-color: #fff500;
  box-shadow: 0 0 0 3px rgba(255, 245, 0, 0.16);
}
.login-box button {
  width: 100%;
  height: 46px;
  margin-top: 6px;
  border: none;
  border-radius: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #101110;
  cursor: pointer;
  background: #fff500;
  box-shadow: 0 8px 24px rgba(255, 245, 0, 0.22);
  transition: transform .15s, box-shadow .2s, filter .2s;
}
.login-box button:hover:not(:disabled) {
  transform: translateY(-1px);
  filter: brightness(1.06);
  box-shadow: 0 10px 30px rgba(255, 245, 0, 0.35);
}
.login-box button:disabled { opacity: .6; cursor: not-allowed; }
.login-error {
  margin-top: 12px;
  text-align: center;
  color: #ff6b6b;
  font-size: 13px;
}
.login-footer {
  margin-top: 26px;
  text-align: center;
  color: #6e6e66;
  font-size: 12px;
}

/* 加载动画结束后表单逐元素入场 */
.login-box > * {
  opacity: 0;
}
.login-box.show > * {
  animation: fadeUp 0.5s ease forwards;
}
.login-box.show > *:nth-child(1) { animation-delay: 0.05s; }
.login-box.show > *:nth-child(2) { animation-delay: 0.12s; }
.login-box.show > *:nth-child(3) { animation-delay: 0.19s; }
.login-box.show form { animation-delay: 0.26s; }
.login-box.show .login-footer { animation-delay: 0.34s; }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 不同意免责时的不可用提示 */
.deny-box {
  position: relative;
  z-index: 2;
  width: 420px;
  padding: 40px 34px;
  text-align: center;
  background: rgba(20, 20, 18, 0.9);
  border: 1px solid rgba(255, 107, 107, 0.4);
  border-radius: 0;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.7);
  animation: fadeUp 0.45s ease forwards;
}
.deny-mark {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border: 2px solid #ff6b6b;
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 32px;
  font-weight: 800;
  line-height: 52px;
}
.deny-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #ff6b6b;
  margin-bottom: 14px;
}
.deny-desc {
  font-size: 13.5px;
  line-height: 1.9;
  color: #b8b8b0;
}
.deny-retry {
  display: block;
  width: 100%;
  height: 44px;
  margin-top: 24px;
  border: 1px solid rgba(255, 245, 0, 0.5);
  border-radius: 0;
  background: transparent;
  color: #fff500;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 3px;
  cursor: pointer;
  transition: all .18s;
}
.deny-retry:hover {
  background: rgba(255, 245, 0, 0.12);
}
</style>
