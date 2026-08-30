<template>
  <div>
    <h2>财务对账</h2>
    <p class="desc">
      毛利 = (实际售价 - 成本价) × 数量，成本取「确认出库」时点快照，历史数据不随商品档案成本改动而漂移，按确认时间对账可追溯
    </p>

    <!-- 筛选栏 -->
    <div class="toolbar">
      <label>开始</label>
      <input type="date" v-model="startDate" @change="loadAll" />
      <label>结束</label>
      <input type="date" v-model="endDate" @change="loadAll" />
      <select v-model="channelId" @change="loadAll" style="min-width: 140px">
        <option value="0">全部渠道</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <button @click="loadAll">查询</button>
      <span style="flex: 1"></span>
      <span class="muted" style="align-self: center">{{ statusName }}</span>
    </div>

    <!-- 汇总卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">销售总额</div>
        <div class="stat-num gold">¥{{ fmtMoney(summary.sales_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">成本总额</div>
        <div class="stat-num">¥{{ fmtMoney(summary.cost_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">毛利总额</div>
        <div class="stat-num" :style="{ color: (summary.gross_total || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">¥{{ fmtMoney(summary.gross_total) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">毛利率</div>
        <div class="stat-num" :style="{ color: (summary.gross_rate || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">{{ fmtRate(summary.gross_rate) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">销售单数</div>
        <div class="stat-num">{{ summary.order_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">出库件数</div>
        <div class="stat-num">{{ summary.item_qty || 0 }}</div>
      </div>
    </div>

    <!-- 渠道分组统计 -->
    <div class="panel" style="overflow: auto; margin-bottom: 16px">
      <div style="margin-bottom: 10px"><b style="letter-spacing: 1px">渠道分组统计</b></div>
      <table>
        <thead>
          <tr>
            <th>渠道</th>
            <th>单数</th>
            <th>件数</th>
            <th>销售总额</th>
            <th>成本</th>
            <th>毛利</th>
            <th>毛利率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(g, i) in channelRows" :key="i">
            <td style="font-weight: 600">{{ g.channel_name }}</td>
            <td>{{ g.order_count }}</td>
            <td>{{ g.item_qty }}</td>
            <td style="color: var(--gold)">¥{{ fmtMoney(g.sales_total) }}</td>
            <td>¥{{ fmtMoney(g.cost_total) }}</td>
            <td :style="{ color: (g.gross_total || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">¥{{ fmtMoney(g.gross_total) }}</td>
            <td :style="{ color: (g.gross_rate || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">{{ fmtRate(g.gross_rate) }}</td>
          </tr>
          <tr v-if="!channelRows.length">
            <td colspan="7" class="empty">该日期范围内还没有已出库的销售单</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 销售单对账明细 -->
    <div class="panel" style="overflow: auto">
      <div style="display: flex; align-items: center; margin-bottom: 10px">
        <b style="letter-spacing: 1px">销售单对账明细（{{ total }} 单）</b>
        <span style="flex: 1"></span>
        <span class="muted">点击单号查看逐行货品毛利</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>单号</th>
            <th>确认时间</th>
            <th>渠道</th>
            <th>客户</th>
            <th>件数</th>
            <th>销售总额</th>
            <th>成本</th>
            <th>毛利</th>
            <th>毛利率</th>
            <th>开票</th>
            <th>回单号</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id">
            <td>
              <a style="color: var(--primary-2); cursor: pointer; text-decoration: none" @click="openDetail(o.id)">{{ o.order_no }}</a>
            </td>
            <td class="muted">{{ fmtTime(o.confirmed_at) }}</td>
            <td>{{ o.channel_name || '—' }}</td>
            <td>{{ o.buyer || '—' }}</td>
            <td>{{ o.item_qty }}</td>
            <td style="color: var(--gold)">¥{{ fmtMoney(o.sales_total) }}</td>
            <td>¥{{ fmtMoney(o.cost_total) }}</td>
            <td :style="{ color: (o.gross_total || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">¥{{ fmtMoney(o.gross_total) }}</td>
            <td :style="{ color: (o.gross_rate || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">{{ fmtRate(o.gross_rate) }}</td>
            <td>
              <span v-if="o.invoice_status === 'invoiced'" class="tag tag-done">已开票</span>
              <span v-else class="muted">未开票</span>
            </td>
            <td class="muted">{{ o.receipt_no || '—' }}</td>
          </tr>
          <tr v-if="!orders.length">
            <td colspan="11" class="empty">该日期范围内没有符合条件的销售单</td>
          </tr>
        </tbody>
      </table>
      <div class="pager">
        <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span class="muted">第 {{ page }} / {{ maxPage }} 页</span>
        <button :disabled="page >= maxPage" @click="changePage(page + 1)">下一页</button>
      </div>
    </div>

    <!-- 单笔对账详情（逐行货品） -->
    <div class="modal-mask" v-if="detail">
      <div class="modal">
        <div class="modal-head">
          <b style="letter-spacing: 1px">{{ detail.order_no }} · 对账详情</b>
          <span style="flex: 1"></span>
          <button class="modal-close" @click="detail = null">✕</button>
        </div>
        <div class="modal-body">
          <div class="info-grid">
            <div><label>确认时间</label><span>{{ fmtTime(detail.confirmed_at) }}</span></div>
            <div><label>渠道</label><span>{{ detail.channel_name || '—' }}</span></div>
            <div><label>客户</label><span>{{ detail.buyer || '—' }}</span></div>
            <div><label>经办人</label><span>{{ detail.operator || '—' }}</span></div>
            <div><label>销售总额</label><span class="gold">¥{{ fmtMoney(detail.sales_total) }}</span></div>
            <div><label>成本总额</label><span>¥{{ fmtMoney(detail.cost_total) }}</span></div>
            <div><label>毛利</label><span :style="{ color: (detail.gross_total || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">¥{{ fmtMoney(detail.gross_total) }}</span></div>
            <div><label>毛利率</label><span :style="{ color: (detail.gross_rate || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">{{ fmtRate(detail.gross_rate) }}</span></div>
            <div><label>开票状态</label><span>{{ detail.invoice_status === 'invoiced' ? '已开票' : '未开票' }}</span></div>
            <div><label>回单号</label><span>{{ detail.receipt_no || '—' }}</span></div>
          </div>
          <table style="margin-top: 12px">
            <thead>
              <tr>
                <th>#</th>
                <th>货品</th>
                <th>数量</th>
                <th>折扣</th>
                <th>实际售价</th>
                <th>成本价</th>
                <th>销售小计</th>
                <th>成本小计</th>
                <th>毛利</th>
                <th>毛利率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(ln, i) in detail.lines" :key="i">
                <td class="muted">{{ i + 1 }}</td>
                <td style="font-weight: 600">{{ ln.sku_name }}</td>
                <td>{{ ln.quantity }}</td>
                <td class="muted">{{ ln.discount ? ln.discount * 10 + ' 折' : '—' }}</td>
                <td>¥{{ fmtMoney(ln.unit_price) }}</td>
                <td>¥{{ fmtMoney(ln.cost_price) }}</td>
                <td style="color: var(--gold)">¥{{ fmtMoney(ln.item_sales) }}</td>
                <td>¥{{ fmtMoney(ln.item_cost) }}</td>
                <td :style="{ color: (ln.gross || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">¥{{ fmtMoney(ln.gross) }}</td>
                <td :style="{ color: (ln.gross_rate || 0) >= 0 ? '#5bd6a8' : '#ff7b7b' }">{{ fmtRate(ln.gross_rate) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { financeApi, channelApi } from '../api'

const PAGE_SIZE = 20
const channels = ref([])
const startDate = ref('')
const endDate = ref('')
const channelId = ref(0)

const summary = ref({})
const channelRows = ref([])
const orders = ref([])
const total = ref(0)
const page = ref(1)
const detail = ref(null)

function fmtDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function monthStart() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function fmtMoney(v) {
  if (v === null || v === undefined || isNaN(v)) return '0.00'
  const num = Number(v)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtRate(v) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return (Number(v) * 100).toFixed(2) + '%'
}
function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}

const maxPage = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const statusName = computed(() => `统计口径：已确认出库单（按确认时间）`)

function params() {
  const p = { start: startDate.value, end: endDate.value, page: page.value, page_size: PAGE_SIZE }
  if (Number(channelId.value) > 0) p.channel_id = Number(channelId.value)
  return p
}

async function loadAll() {
  page.value = 1
  await load()
}
async function load() {
  const p = params()
  const [s, c, o] = await Promise.all([
    financeApi.summary(p),
    financeApi.byChannel({ start: p.start, end: p.end }),
    financeApi.orders(p)
  ])
  summary.value = s
  channelRows.value = c.rows || []
  orders.value = o.items || []
  total.value = o.total || 0
}

async function changePage(np) {
  if (np < 1) return
  page.value = np
  await load()
}

async function openDetail(id) {
  try {
    detail.value = await financeApi.orderDetail(id)
  } catch (e) {
    alert(e.response?.data?.detail || '获取对账详情失败')
  }
}

async function loadChannels() {
  channels.value = await channelApi.list()
}

onMounted(() => {
  endDate.value = fmtDate(new Date())
  startDate.value = monthStart()
  loadChannels().then(loadAll)
})
</script>

<style scoped>
.stat-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.stat-card {
  border-radius: 12px; padding: 14px 16px;
  border: 1px solid rgba(91, 124, 250, .22);
  background: linear-gradient(160deg, rgba(91, 124, 250, .10), rgba(143, 108, 230, .05));
}
.stat-label { font-size: 12px; color: var(--text-2); margin-bottom: 6px; letter-spacing: 1px; }
.stat-num { font-size: 22px; font-weight: 800; color: var(--text); }
.stat-num.gold { color: var(--gold); }
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; border: 1px solid; }
.tag-done { color: #5bd6a8; border-color: rgba(91,214,168,.5); background: rgba(91,214,168,.12); }
.pager { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.pager button {
  height: 30px; padding: 0 14px; border-radius: 7px;
  border: 1px solid var(--border); background: transparent; color: var(--text-2);
  cursor: pointer; font-size: 13px;
}
.pager button:disabled { opacity: .4; cursor: not-allowed; }
.modal-mask {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(10, 12, 32, .72); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.modal {
  width: min(960px, 100%); max-height: 86vh; overflow: auto;
  border-radius: 14px; border: 1px solid rgba(91, 124, 250, .35);
  background: #141a3d; box-shadow: 0 24px 60px rgba(0,0,0,.5);
}
.modal-head {
  display: flex; align-items: center; padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(90deg, rgba(91,124,250,.14), rgba(143,108,230,.08));
}
.modal-close {
  width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; color: var(--text-2); cursor: pointer; font-size: 13px;
}
.modal-body { padding: 16px 18px 20px; }
.info-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px 18px; margin-bottom: 4px;
}
.info-grid label { display: block; font-size: 12px; color: var(--text-2); margin-bottom: 4px; }
.info-grid span { font-size: 14px; }
.info-grid .gold { color: var(--gold); }
</style>
