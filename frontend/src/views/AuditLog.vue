<template>
  <div>
    <div class="page-head">
      <div>
        <h2>操作日志</h2>
        <p class="desc">记录登录、建号、删号等关键操作，谁在什么时候做了什么，一目了然。</p>
      </div>
      <button v-if="auth.isBoss || auth.isAdmin" class="cleanup-btn" @click="openDialog">清理日志</button>
    </div>
    <div class="panel">
      <table>
        <thead>
          <tr><th>时间</th><th>用户</th><th>操作</th><th>详情</th></tr>
        </thead>
        <tbody>
          <tr v-for="a in logs" :key="a.id">
            <td>{{ fmt(a.created_at) }}</td>
            <td>{{ a.username }}</td>
            <td>{{ a.action }}</td>
            <td>{{ a.detail }}</td>
          </tr>
          <tr v-if="!logs.length"><td colspan="4" style="text-align:center;color:#8b93a7">暂无记录</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 清理确认弹窗 -->
    <div v-if="dialogOpen" class="settings-mask" @click.self="closeDialog">
      <div class="settings-dialog audit-dialog">
        <div class="settings-head">
          <span class="settings-title">清理操作日志</span>
          <button class="settings-close" @click="closeDialog">✕</button>
        </div>
        <div class="settings-body">
          <div class="settings-section">
            <h4>按日期清理</h4>
            <p class="audit-hint">删除所选日期之前的所有操作日志。</p>
            <div class="audit-row">
              <input v-model="beforeDate" type="date" class="dir-input" style="flex:1" />
              <button class="migrate-btn" :disabled="!beforeDate || cleaning" @click="cleanByDate">
                {{ cleaning ? '清理中…' : '清理该日期前' }}
              </button>
            </div>
          </div>
          <div class="settings-section">
            <h4>清空全部</h4>
            <p class="audit-hint audit-danger">将删除全部操作日志，且不可恢复。</p>
            <button class="danger-btn" :disabled="cleaning" @click="cleanAll">
              {{ cleaning ? '清理中…' : '清空全部日志' }}
            </button>
          </div>
          <div v-if="msg" class="settings-msg" :class="msgClass">{{ msg }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const logs = ref([])
const dialogOpen = ref(false)
const beforeDate = ref('')
const cleaning = ref(false)
const msg = ref('')
const msgClass = ref('ok')

const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '')

async function load() {
  logs.value = await api.get('/audits')
}

function openDialog() {
  dialogOpen.value = true
  beforeDate.value = ''
  msg.value = ''
}

function closeDialog() {
  if (cleaning.value) return
  dialogOpen.value = false
}

function showMsg(text, ok = true) {
  msg.value = text
  msgClass.value = ok ? 'ok' : 'err'
}

async function doClean(url, okText) {
  cleaning.value = true
  try {
    const data = await api.delete(url)
    showMsg(`${okText}：已删除 ${data.deleted} 条记录`, true)
    await load()
  } catch (e) {
    showMsg(e?.response?.data?.detail || '清理失败，请重试', false)
  } finally {
    cleaning.value = false
  }
}

async function cleanByDate() {
  if (!beforeDate.value) return
  await doClean(`/audits?before=${encodeURIComponent(beforeDate.value)}`, '清理完成')
}

async function cleanAll() {
  await doClean('/audits', '清空完成')
}

onMounted(load)
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-head .desc { margin-bottom: 0; }
.cleanup-btn {
  flex-shrink: 0;
  height: 38px;
  padding: 0 20px;
  border: 1px solid rgba(255, 107, 129, 0.5);
  border-radius: 9px;
  background: transparent;
  color: var(--danger);
  font-size: 14px;
  cursor: pointer;
  transition: all .18s;
}
.cleanup-btn:hover {
  background: rgba(255, 107, 129, 0.12);
  filter: brightness(1.1);
}
.audit-dialog { width: 520px; }
.audit-hint {
  font-size: 13px;
  color: var(--text-2);
  margin-bottom: 12px;
}
.audit-hint.audit-danger { color: var(--danger); }
.audit-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.danger-btn {
  height: 38px;
  padding: 0 20px;
  border: none;
  border-radius: 9px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  background: linear-gradient(135deg, #ff6b81, #e0485e);
  box-shadow: 0 6px 18px rgba(255, 107, 129, 0.3);
  transition: filter .18s, transform .15s;
}
.danger-btn:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
.danger-btn:disabled { opacity: .6; cursor: not-allowed; }
</style>
