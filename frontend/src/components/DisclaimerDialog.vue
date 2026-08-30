<template>
  <teleport to="body">
    <div class="settings-mask" @click.self="onMask">
      <div class="settings-dialog disclaimer-dialog">
        <div class="settings-head disclaimer-head">
          <span class="settings-title">免责声明</span>
          <button v-if="!forced" class="settings-close" @click="$emit('close')">✕</button>
          <span v-else class="disclaimer-badge">首次使用须知</span>
        </div>

        <div class="disclaimer-body">
          <div class="disclaimer-pager-view">
            <div
              v-for="(pg, i) in pages"
              :key="i"
              v-show="i === page"
              class="disclaimer-page"
              v-html="pg.html"
            ></div>
          </div>

          <div class="disclaimer-pager">
            <button class="pager-btn" :disabled="page === 0" @click="prev">上一页</button>
            <span class="pager-info">{{ page + 1 }} / {{ pages.length }}</span>
            <button class="pager-btn" :disabled="page === pages.length - 1" @click="next">下一页</button>
          </div>

          <div class="disclaimer-actions">
            <template v-if="forced">
              <div class="disclaimer-agree-hint" :class="{ ready: canAgree }">
                <template v-if="!canAgree">
                  <span v-if="countdown > 0">请仔细阅读免责声明，{{ countdown }} 秒后可表示同意</span>
                  <span v-else>请阅读至最后一页后即可表示同意</span>
                </template>
                <span v-else>您已阅读完整内容，可表示同意</span>
              </div>
              <div class="disclaimer-btn-row">
                <button class="agree-btn" :disabled="!canAgree" @click="agree">
                  我同意本免责声明中的所有内容
                </button>
                <button class="deny-btn" @click="deny">我不同意</button>
              </div>
            </template>
            <template v-else>
              <div class="disclaimer-btn-row">
                <button class="agree-btn" @click="$emit('close')">我已阅读，关闭</button>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  forced: { type: Boolean, default: false }
})
const emit = defineEmits(['confirm', 'cancel', 'close'])

// ---- 免责声明正文（与根目录 DISCLAIMER.md 内容一致，分 4 页展示）----
const pages = [
  {
    html: `
      <h3>0号仓库库存管理系统 免责声明</h3>
      <h4>一、项目性质与版权声明</h4>
      <p>本项目由开发者与 AI 联合创作，为完全免费、开源的原创项目，<strong>非商业化项目</strong>。</p>
      <ul>
        <li>严禁任何个人或第三方对其进行商业化运营、抢注、仿冒或二次销售。</li>
        <li>未经开发者书面授权，任何组织或个人不得将本项目用于任何商业用途。</li>
        <li>开发者发现本项目被盗用、仿冒或商业化运营的，有权依照相关法律法规维护自身合法权益。</li>
      </ul>
      <h5>举报与监督</h5>
      <p>欢迎社会各界监督。若在第三方平台（视频平台、应用商店、电商平台等）发现本项目被商业化运营、抢注、仿冒或二次销售，请举报至邮箱：<strong class="em-strong">tao18257920208@outlook.com</strong>。开发者核实后将依法维权，并对举报人信息严格保密。</p>
    `
  },
  {
    html: `
      <h4>二、数据安全与备份</h4>
      <p class="em-block"><strong>【重点提示】</strong>本项目依赖本地数据库存储数据，可能因断电、误操作、程序缺陷等原因导致数据损坏或丢失。使用前请务必自行备份重要数据。因未备份或备份不当造成的数据丢失，开发者不承担责任。</p>
      <h4>三、使用风险</h4>
      <p>开发者不对因使用本项目而导致的任何<strong>直接或间接损失</strong>承担责任，包括但不限于数据丢失、业务中断、利润损失等。</p>
    `
  },
  {
    html: `
      <h4>四、第三方素材版权</h4>
      <p class="em-block"><strong>【重点提示】</strong>本项目所使用的背景图、参考美术风格等素材版权归原作者所有，仅用于个人学习与研究。若需进行商业使用或公开分发，请自行确认相关授权。由此产生的侵权风险由使用者自行承担。</p>
      <h4>五、当前版本已知局限</h4>
      <p>当前为第一版（v1.0–v1.3），可能存在印刷打印小问题、云端备份尚未搭建等情况，相关功能将在后续版本中迭代完善。</p>
    `
  },
  {
    html: `
      <h4>六、云端服务与数据存放</h4>
      <p>后续版本将完善云端备份功能，可能租用开发者个人服务器提供云端服务。重点数据建议存放于本地或自行租赁服务器。若选择使用开发者提供的服务器，开发者有权对该<strong>附加/增值服务</strong>进行收费，该收费服务与免费系统本身无关。</p>
      <h4>七、合规提醒</h4>
      <p>本免责声明不构成任何法律、财务或税务建议。如有相关需求，请咨询专业人士。</p>
      <h4>八、修改与终止</h4>
      <p>开发者保留随时更新、修改或终止本项目及其相关服务的权利。</p>
      <h4>九、同意与使用</h4>
      <p>您使用本项目即视为已阅读、理解并同意本免责声明的全部条款。</p>
    `
  }
]

const page = ref(0)
const countdown = ref(5)
let timer = null
const reachedEnd = computed(() => page.value === pages.length - 1)
const canAgree = computed(() => (props.forced ? countdown.value <= 0 && reachedEnd.value : true))

function prev() {
  if (page.value > 0) page.value--
}
function next() {
  if (page.value < pages.length - 1) page.value++
}
function agree() {
  emit('confirm')
}
function deny() {
  emit('cancel')
}
function onMask() {
  if (!props.forced) emit('close')
}

onMounted(() => {
  if (props.forced) {
    timer = setInterval(() => {
      if (countdown.value > 0) {
        countdown.value--
      } else {
        clearInterval(timer)
      }
    }, 1000)
  }
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style>
/* 免责声明弹窗专属样式（非 scoped，命中 teleport 到 body 的挂载节点） */
.disclaimer-dialog {
  width: 640px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.disclaimer-dialog .disclaimer-badge {
  font-size: 12px;
  color: var(--btn-text, #fff);
  padding: 4px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.disclaimer-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 22px 20px;
}
.disclaimer-pager-view {
  min-height: 300px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--input-bg);
}
.disclaimer-page {
  font-size: 13.5px;
  line-height: 1.9;
  color: var(--text);
}
.disclaimer-page h3 {
  font-size: 17px;
  margin-bottom: 12px;
  color: var(--gold);
  letter-spacing: 1px;
}
.disclaimer-page h4 {
  font-size: 14px;
  font-weight: 700;
  margin: 14px 0 6px;
  color: var(--primary);
}
.disclaimer-page h5 {
  font-size: 13px;
  font-weight: 700;
  margin: 12px 0 4px;
  color: var(--gold);
}
.disclaimer-page p { margin: 6px 0; }
.disclaimer-page ul { margin: 6px 0 6px 18px; }
.disclaimer-page li { margin: 4px 0; }
.disclaimer-page strong { font-weight: 700; }
.disclaimer-page .em-strong {
  color: var(--danger);
  font-weight: 800;
  letter-spacing: 1px;
}
.disclaimer-page .em-block {
  border-left: 3px solid var(--danger);
  padding-left: 10px;
  background: rgba(255, 107, 129, 0.08);
}
.disclaimer-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
}
.pager-btn {
  height: 32px;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
  transition: all .18s;
}
.pager-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.pager-btn:disabled { opacity: .45; cursor: not-allowed; }
.pager-info {
  font-size: 12px;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
  min-width: 52px;
  text-align: center;
}
.disclaimer-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.disclaimer-agree-hint {
  font-size: 12.5px;
  color: var(--danger);
  text-align: center;
}
.disclaimer-agree-hint.ready { color: var(--gold); }
.disclaimer-btn-row {
  display: flex;
  gap: 12px;
}
.disclaimer-btn-row .agree-btn,
.disclaimer-btn-row .deny-btn {
  flex: 1;
  height: 42px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all .18s;
}
.agree-btn {
  color: var(--btn-text, #fff);
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  box-shadow: 0 6px 18px rgba(91, 124, 250, 0.3);
}
.agree-btn:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
.agree-btn:disabled {
  opacity: .45;
  cursor: not-allowed;
  filter: grayscale(0.6);
  box-shadow: none;
}
.deny-btn {
  color: var(--danger);
  background: transparent;
  border: 1px solid rgba(255, 107, 129, 0.5);
}
.deny-btn:hover { background: rgba(255, 107, 129, 0.12); }
</style>
