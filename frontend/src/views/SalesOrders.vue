<template>
  <div>
    <h2>销售出库</h2>
    <p class="desc">新建销售单 → 扫码选品 → 填数量/折扣/售价 → 整单确认出库，库存自动扣减并留档</p>

    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索单号 / 买家 / 渠道" style="width: 220px" @keyup.enter="load" />
      <select v-model="filterStatus" @change="load" style="min-width: 120px">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="done">已完成</option>
        <option value="cancelled">已取消</option>
      </select>
      <button @click="load">查询</button>
      <span style="flex: 1"></span>
      <button style="background: linear-gradient(135deg,#e2b45c,#d99a3f)" @click="goNew">新建销售单</button>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th>单号</th>
            <th>渠道</th>
            <th>买家</th>
            <th>明细数</th>
            <th>数量合计</th>
            <th>金额合计</th>
            <th>状态</th>
            <th>开票</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id">
            <td>
              <a style="color: var(--primary-2); cursor: pointer; text-decoration: none" @click="goDetail(o.id)">{{ o.order_no }}</a>
            </td>
            <td>{{ o.channel_name || '—' }}</td>
            <td>{{ o.buyer || '—' }}</td>
            <td>{{ o.items.length }}</td>
            <td style="color: var(--gold)">{{ o.total_qty }}</td>
            <td>¥{{ o.total_amount }}</td>
            <td><span :class="'tag tag-' + o.status">{{ statusName(o.status) }}</span></td>
            <td>
              <span v-if="o.invoice_status === 'invoiced'" class="tag tag-done">已开票</span>
              <span v-else class="muted">未开票</span>
            </td>
            <td class="muted">{{ fmtTime(o.created_at) }}</td>
            <td>
              <button style="border-color: rgba(91,124,250,.5); color: var(--primary)" @click="goDetail(o.id)">
                {{ o.status === 'draft' ? '继续' : '查看' }}
              </button>
              <button v-if="o.status === 'draft'" @click="remove(o)">删除</button>
            </td>
          </tr>
          <tr v-if="!orders.length">
            <td colspan="10" class="empty">还没有销售单，点击「新建销售单」开始第一单</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { saleApi } from '../api'

const router = useRouter()
const orders = ref([])
const keyword = ref('')
const filterStatus = ref('')

function statusName(s) {
  return { draft: '草稿', done: '已完成', cancelled: '已取消' }[s] || s
}

function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}

async function load() {
  orders.value = await saleApi.list({
    keyword: keyword.value,
    status: filterStatus.value
  })
}

function goNew() { router.push('/sales/new') }
function goDetail(id) { router.push(`/sales/${id}`) }

async function remove(o) {
  if (!confirm(`确定删除销售单「${o.order_no}」吗？删除后不可恢复。`)) return
  try {
    await saleApi.remove(o.id)
    load()
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
</style>
