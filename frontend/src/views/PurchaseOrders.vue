<template>
  <div>
    <h2>采购入库</h2>
    <p class="desc">新建采购单 → 扫码加货 → 统一确认入库；没扫到的货现场建档，整单入库自动转入商品档案</p>

    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索单号 / 供应商" style="width: 220px" @keyup.enter="load" />
      <select v-model="filterStatus" @change="load" style="min-width: 120px">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="done">已入库</option>
        <option value="cancelled">已取消</option>
      </select>
      <button @click="load">查询</button>
      <span style="flex: 1"></span>
      <button style="background: linear-gradient(135deg,#37b38a,#2a9d78)" @click="openSupplier">供应商管理</button>
      <button @click="goNew">新建采购单</button>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th>单号</th>
            <th>供应商</th>
            <th>采购方式</th>
            <th>采购日期</th>
            <th>明细数</th>
            <th>数量合计</th>
            <th>金额合计</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id">
            <td>
              <a style="color: var(--primary-2); cursor: pointer; text-decoration: none" @click="goDetail(o.id)">{{ o.order_no }}</a>
            </td>
            <td>{{ o.supplier_name || '—' }}</td>
            <td>{{ o.purchase_method || '—' }}</td>
            <td>{{ o.order_date || '—' }}</td>
            <td>{{ o.items.length }}</td>
            <td style="color: var(--gold)">{{ o.total_qty }}</td>
            <td>¥{{ o.total_amount }}</td>
            <td><span :class="'tag tag-' + o.status">{{ statusName(o.status) }}</span></td>
            <td class="muted">{{ fmtTime(o.created_at) }}</td>
            <td>
              <button style="border-color: rgba(91,124,250,.5); color: var(--primary)" @click="goDetail(o.id)">
                {{ o.status === 'draft' ? '继续' : '查看' }}
              </button>
              <button v-if="o.status === 'draft'" @click="remove(o)">删除</button>
            </td>
          </tr>
          <tr v-if="!orders.length">
            <td colspan="10" class="empty">还没有采购单，点击「新建采购单」开始第一单</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 供应商管理弹窗 -->
    <div v-if="showSup" class="modal-mask" @click.self="showSup = false">
      <div class="modal">
        <h3>供应商（采购商）管理</h3>
        <p class="muted" style="margin: 8px 0 14px; font-size: 13px">记录你的进货来源，下单时直接选，不用重复打字</p>
        <div style="display: flex; gap: 8px; margin-bottom: 14px">
          <input v-model="newSup" placeholder="供应商名称，如：广州XX玩具厂" style="flex: 1" @keyup.enter="addSup" />
          <button @click="addSup">新增</button>
        </div>
        <table>
          <thead>
            <tr><th>名称</th><th>联系人</th><th>电话</th><th style="width: 60px">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in sups" :key="s.id">
              <td>
                <input v-model="s.name" style="width: 150px" @keyup.enter="saveSup(s)" />
              </td>
              <td><input v-model="s.contact" style="width: 90px" @keyup.enter="saveSup(s)" /></td>
              <td><input v-model="s.phone" style="width: 120px" @keyup.enter="saveSup(s)" /></td>
              <td>
                <button class="mini-btn" @click="saveSup(s)">存</button>
                <button class="mini-btn danger" @click="delSup(s)">删</button>
              </td>
            </tr>
            <tr v-if="!sups.length"><td colspan="4" class="empty">暂无供应商，先添加一个</td></tr>
          </tbody>
        </table>
        <div class="modal-actions">
          <button class="btn-plain" @click="showSup = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { purchaseApi, supplierApi } from '../api'

const router = useRouter()
const orders = ref([])
const keyword = ref('')
const filterStatus = ref('')

const showSup = ref(false)
const sups = ref([])
const newSup = ref('')

function statusName(s) {
  return { draft: '草稿', done: '已入库', cancelled: '已取消' }[s] || s
}

function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}

async function load() {
  orders.value = await purchaseApi.list({
    keyword: keyword.value,
    status: filterStatus.value
  })
}

function goNew() { router.push('/purchase/new') }
function goDetail(id) { router.push(`/purchase/${id}`) }

async function remove(o) {
  if (!confirm(`确定删除采购单「${o.order_no}」吗？删除后不可恢复。`)) return
  try {
    await purchaseApi.remove(o.id)
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

function openSupplier() {
  showSup.value = true
  loadSups()
}

async function loadSups() {
  sups.value = await supplierApi.list()
}

async function addSup() {
  const name = newSup.value.trim()
  if (!name) return
  try {
    await supplierApi.create({ name })
    newSup.value = ''
    await loadSups()
  } catch (e) {
    alert(e.response?.data?.detail || '新增失败')
  }
}

async function saveSup(s) {
  try {
    await supplierApi.update(s.id, { name: s.name, contact: s.contact, phone: s.phone })
    await loadSups()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function delSup(s) {
  if (!confirm(`确定删除供应商「${s.name}」吗？`)) return
  try {
    await supplierApi.remove(s.id)
    await loadSups()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.tag {
  display: inline-block; padding: 3px 12px; border-radius: 20px;
  font-size: 12px; border: 1px solid;
}
.tag-draft { color: #e2b45c; border-color: rgba(226,180,92,.5); background: rgba(226,180,92,.12); }
.tag-done { color: #5bd6a8; border-color: rgba(91,214,168,.5); background: rgba(91,214,168,.12); }
.tag-cancelled { color: var(--text-2); border-color: var(--border); }
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; z-index: 50;
}
.modal {
  width: 640px; max-width: 92vw; max-height: 80vh; overflow: auto;
  background: var(--panel-strong); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px; box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 4px; letter-spacing: 1px; }
.modal input {
  height: 36px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 13px; outline: none;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.modal-actions button {
  height: 38px; padding: 0 22px; border: none; border-radius: 9px;
  color: #fff; font-size: 14px; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.modal-actions .btn-plain { background: transparent; border: 1px solid var(--border); color: var(--text-2); }
.mini-btn {
  height: 30px; padding: 0 10px; border-radius: 7px;
  border: 1px solid rgba(91,124,250,.5); background: transparent;
  color: var(--primary); font-size: 12px; cursor: pointer;
}
.mini-btn.danger { border-color: rgba(255,92,92,.5); color: #ff7b7b; }
</style>
