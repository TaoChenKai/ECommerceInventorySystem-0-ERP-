<template>
  <div>
    <h2>渠道追踪</h2>
    <p class="desc">登记你的销售渠道（淘宝 / 拼多多 / 抖音 / 线下等），出库时打标，从第一天攒数据</p>

    <div class="toolbar">
      <button style="background: linear-gradient(135deg,#37b38a,#2a9d78)" @click="openForm()">新增渠道</button>
      <span style="flex: 1"></span>
      <button @click="load">刷新</button>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th>渠道名称</th>
            <th>类型</th>
            <th>备注</th>
            <th>出库量</th>
            <th>出库金额</th>
            <th>毛利</th>
            <th style="width: 130px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in stats" :key="s.channel_id === null ? 'none' : s.channel_id">
            <td>{{ s.channel_name }}</td>
            <td class="muted">{{ typeName(s) }}</td>
            <td class="muted">{{ remarkOf(s.channel_id) }}</td>
            <td>{{ s.out_qty }}</td>
            <td style="color: var(--text)">¥{{ s.out_amount }}</td>
            <td :style="s.gross_profit >= 0 ? 'color:#5bd6a8' : 'color:var(--danger)'">¥{{ s.gross_profit }}</td>
            <td>
              <template v-if="s.channel_id !== null">
                <button style="border-color: rgba(91,124,250,.5); color: var(--primary)" @click="openForm(s.channel_id)">编辑</button>
                <button @click="remove(s)">删除</button>
              </template>
              <span v-else class="muted" style="font-size: 13px">—</span>
            </td>
          </tr>
          <tr v-if="!stats.length">
            <td colspan="7" class="empty">暂无渠道，先新增一个渠道开始攒数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 渠道表单弹窗 -->
    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal">
        <h3>{{ form.id ? '编辑渠道' : '新增渠道' }}</h3>
        <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 16px">
          <div>
            <label class="f-label">渠道名称</label>
            <input v-model="form.name" placeholder="如：淘宝店 / 拼多多 / 抖音 / 线下批发" style="width: 100%" />
          </div>
          <div>
            <label class="f-label">渠道类型</label>
            <select v-model="form.channel_type" style="width: 100%">
              <option value="电商">电商</option>
              <option value="线下">线下</option>
              <option value="批发">批发</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div>
            <label class="f-label">备注（可选）</label>
            <input v-model="form.remark" placeholder="如：主推款 / 新开的店" style="width: 100%" />
          </div>
        </div>
        <div v-if="formErr" style="color: var(--danger); font-size: 13px; margin-top: 10px">{{ formErr }}</div>
        <div class="modal-actions">
          <button class="btn-plain" @click="showForm = false">取消</button>
          <button @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { channelApi, stockApi } from '../api'

const channels = ref([])
const stats = ref([])
const showForm = ref(false)
const form = ref({ id: null, name: '', channel_type: '电商', remark: '' })
const formErr = ref('')

function remarkOf(id) {
  const c = channels.value.find((x) => x.id === id)
  return c?.remark || '—'
}
function typeName(s) {
  const c = channels.value.find((x) => x.id === s.channel_id)
  return c?.channel_type || '—'
}

async function load() {
  channels.value = await channelApi.list()
  stats.value = await stockApi.channelStats()
}

function openForm(id) {
  formErr.value = ''
  if (id) {
    const c = channels.value.find((x) => x.id === id)
    form.value = { id: c.id, name: c.name, channel_type: c.channel_type || '电商', remark: c.remark || '' }
  } else {
    form.value = { id: null, name: '', channel_type: '电商', remark: '' }
  }
  showForm.value = true
}

async function save() {
  const name = form.value.name.trim()
  if (!name) { formErr.value = '渠道名称不能为空'; return }
  try {
    if (form.value.id) {
      await channelApi.update(form.value.id, { name, channel_type: form.value.channel_type, remark: form.value.remark })
    } else {
      await channelApi.create({ name, channel_type: form.value.channel_type, remark: form.value.remark })
    }
    showForm.value = false
    load()
  } catch (e) {
    formErr.value = e.response?.data?.detail || '保存失败'
  }
}

async function remove(s) {
  if (!confirm(`确定删除渠道「${s.channel_name}」吗？历史流水会保留但归为未选渠道。`)) return
  try {
    await channelApi.remove(s.channel_id)
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.f-label { display: block; font-size: 12px; color: var(--text-2); margin-bottom: 6px; }
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
}
.modal {
  width: 440px; max-width: 92vw;
  background: var(--panel-strong);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 4px; letter-spacing: 1px; }
.modal input, .modal select {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.modal-actions {
  display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px;
}
.modal-actions button {
  height: 38px; padding: 0 22px; border: none; border-radius: 9px;
  color: #fff; font-size: 14px; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.modal-actions .btn-plain {
  background: transparent; border: 1px solid var(--border); color: var(--text-2);
}
</style>
