<template>
  <div>
    <h2>{{ title }}</h2>
    <p class="desc">扫码弹商品卡 → 填数量 / 折扣 / 实际售价 → 加入销售单（可多行拼单）→ 整单确认出库，库存自动扣减并留档</p>

    <!-- 单头信息 -->
    <div class="panel head-panel">
      <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap">
        <b style="font-size: 16px; letter-spacing: 1px; color: var(--primary-2)">{{ order.order_no || '待保存生成单号' }}</b>
        <span v-if="order.status" :class="'tag tag-' + order.status">{{ statusName(order.status) }}</span>
        <span style="flex: 1"></span>
        <span v-if="order.operator" class="muted" style="font-size: 13px">经办：{{ order.operator }}</span>
      </div>

      <div class="head-grid" :class="{ readonly: isDone }">
        <div class="fitem">
          <label>渠道（可选）</label>
          <select v-model="form.channel_id">
            <option :value="null">不指定渠道</option>
            <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div class="fitem">
          <label>客户 / 买家（可留空）</label>
          <input v-model="form.buyer" placeholder="如：线下顾客 / 张三 / XX 公司" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>备注</label>
          <input v-model="form.remark" placeholder="销售说明 / 客户留言等，可留空" />
        </div>
      </div>
    </div>

    <!-- 扫码区 -->
    <div class="scan-bar" v-if="!isDone">
      <input
        ref="scanInput"
        v-model="scanText"
        placeholder="扫条码 / 输编号 / 输名称，回车弹出商品卡"
        @keyup.enter="doScan"
      />
      <button @click="doScan">扫码查询</button>
    </div>
    <div v-if="scanMsg" :class="scanMsgType === 'ok' ? 'ok-msg' : 'err-msg'" style="margin: 6px 0 10px">{{ scanMsg }}</div>

    <!-- 商品信息卡（扫码命中后弹出） -->
    <div v-if="cur" class="panel cur-card">
      <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap">
        <div style="flex: 1; min-width: 220px">
          <div style="font-size: 20px; font-weight: 700; color: var(--primary-2)">{{ cur.sku_name || cur.spu_name }}</div>
          <div style="margin-top: 6px; color: var(--text-2)">
            <template v-if="cur.spec_name">规格：{{ cur.spec_name }}</template>
            <template v-else>规格：默认</template>
          </div>
          <div class="muted" style="margin-top: 4px">
            条码：{{ cur.barcode || '—' }} <span style="margin: 0 8px">|</span>
            商品编号：{{ cur.sku_code || cur.spu_name || '—' }}
          </div>
        </div>
        <div style="text-align: right">
          <div style="font-size: 26px; font-weight: 800; color: var(--gold)">{{ cur.stock }}</div>
          <div class="muted" style="font-size: 13px">当前库存</div>
          <div class="muted" style="font-size: 13px; margin-top: 4px">
            仓库售价 ¥{{ cur.sale_price }}
          </div>
        </div>
      </div>

      <div class="cur-fields">
        <div>
          <label class="f-label">销售数量</label>
          <input v-model.number="pickQty" type="number" min="1" style="width: 110px" placeholder="数量" />
        </div>
        <div>
          <label class="f-label">折扣（如 3.5 / 35 / 66，留空=原价）</label>
          <input v-model="pickDiscountInput" style="width: 110px" placeholder="折扣" @input="onPickDiscount" />
        </div>
        <div>
          <label class="f-label">实际售价（¥，可手动改）</label>
          <input v-model.number="pickPrice" type="number" min="0" step="0.01" style="width: 120px" placeholder="售价" @focus="onPickManualPrice" />
        </div>
        <div class="cur-btn">
          <button @click="addToCart">加入销售单</button>
        </div>
      </div>
      <div v-if="pickHint" class="muted" style="margin-top: 8px; font-size: 12px">{{ pickHint }}</div>
    </div>

    <!-- 明细（拼单区） -->
    <div class="panel" style="overflow: auto">
      <div style="display: flex; align-items: center; margin-bottom: 10px">
        <b style="letter-spacing: 1px">销售明细（{{ items.length }} 项）</b>
        <span style="flex: 1"></span>
        <div class="muted" style="font-size: 13px">
          数量合计 <b style="color: var(--gold)">{{ totalQty }}</b>
          ｜ 应收合计 <b style="color: var(--gold)">¥{{ totalAmount }}</b>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th style="width: 50px">#</th>
            <th>货品</th>
            <th>条码</th>
            <th style="width: 90px">库存</th>
            <th style="width: 100px">数量</th>
            <th style="width: 100px">折扣</th>
            <th style="width: 120px">售价(¥)</th>
            <th style="width: 110px">小计</th>
            <th style="width: 100px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in items" :key="it._key">
            <td class="muted">{{ i + 1 }}</td>
            <td>
              <div style="font-weight: 600">{{ it.sku_name }}</div>
              <div class="muted" style="font-size: 12px" v-if="it.spec_name">规格：{{ it.spec_name }}</div>
            </td>
            <td class="muted">{{ it.barcode || '—' }}</td>
            <td><span :class="'stock-badge' + (it.cur_stock >= it.quantity ? '' : ' low')">{{ it.cur_stock }}</span></td>
            <td>
              <input v-if="!isDone" v-model.number="it.quantity" type="number" min="1" style="width: 70px" />
              <span v-else>{{ it.quantity }}</span>
            </td>
            <td>
              <input v-if="!isDone" v-model="it.discountInput" style="width: 70px" placeholder="无折扣" @input="onRowDiscount(it)" />
              <span v-else>{{ it.discountInput || '—' }}</span>
            </td>
            <td>
              <input v-if="!isDone" v-model.number="it.unit_price" type="number" min="0" step="0.01" style="width: 90px" @focus="onRowManualPrice(it)" />
              <span v-else>¥{{ it.unit_price }}</span>
            </td>
            <td style="color: var(--gold)">¥{{ ((it.quantity || 0) * (it.unit_price || 0)).toFixed(2) }}</td>
            <td>
              <button v-if="!isDone" class="mini-btn danger" @click="removeItem(i)">移除</button>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="9" class="empty">还没有明细，用上面的扫码框扫一件货，填好数量价格后点「加入销售单」</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 底部操作 -->
    <div class="foot-actions" v-if="!isDone">
      <button class="btn-plain" @click="saveDraft">保存草稿</button>
      <button class="btn-confirm" @click="confirmOut" :disabled="confirming">
        {{ confirming ? '出库中...' : '确认出库（减库存 + 留档）' }}
      </button>
    </div>
    <div v-else class="muted" style="margin-top: 14px; font-size: 13px">
      该单已于 {{ order.confirmed_at }} 出库完成。
      <span v-if="order.invoice_status === 'uninvoiced'" style="margin-left: 14px">发票：未开票</span>
      <span v-else style="margin-left: 14px">发票：已开票（{{ order.invoice_no || '—' }}）</span>
      <span v-if="order.receipt_no" style="margin-left: 14px">回单：{{ order.receipt_no }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stockApi, saleApi, channelApi } from '../api'

const route = useRoute()
const router = useRouter()
const isEdit = route.params.id !== undefined && route.params.id !== 'new'
const orderId = isEdit ? Number(route.params.id) : null

const channels = ref([])
const form = ref({ channel_id: null, buyer: '', remark: '' })
const order = ref({ status: '', operator: '', confirmed_at: '', order_no: '' })
const items = ref([])

const scanInput = ref(null)
const scanText = ref('')
const scanMsg = ref('')
const scanMsgType = ref('ok')
const confirming = ref(false)

// 商品信息卡（扫码命中后）
const cur = ref(null)
const pickQty = ref(1)
const pickDiscountInput = ref('')
const pickPrice = ref(0)
const pickHint = ref('')

let keySeq = 0
function newKey() { return 'k' + (++keySeq) + '_' + Date.now() }

const isDone = computed(() => order.value.status === 'done')
const title = computed(() => {
  if (!isEdit) return '新建销售单'
  return order.value.status === 'done' ? '销售单详情' : '编辑销售单'
})

function statusName(s) {
  return { draft: '草稿', done: '已完成', cancelled: '已取消' }[s] || s
}

const totalQty = computed(() => items.value.reduce((s, it) => s + (it.quantity || 0), 0))
const totalAmount = computed(() => items.value.reduce((s, it) => s + (it.quantity || 0) * (it.unit_price || 0), 0).toFixed(2))

// ---- 折扣换算 ----
// 折数 → 系数：3.5/6/9.5 这类(<10)按 ÷10，35/66/37 这类(>=10)按 ÷100，两种结果一致
function toFactor(d) {
  if (d === '' || d === null || d === undefined) return 0
  const v = parseFloat(d)
  if (isNaN(v) || v <= 0) return 0
  if (v >= 10) return Math.round(v / 100 * 10000) / 10000
  return Math.round(v / 10 * 10000) / 10000
}
// 系数 → 折数（回显用），0 表示无折扣
function toZhe(f) {
  if (!f) return ''
  const v = Math.round(f * 10 * 100) / 100
  return String(v)
}

// ---- 扫码 ----
async function doScan() {
  const text = scanText.value.trim()
  if (!text) return
  scanMsg.value = ''
  try {
    const r = await stockApi.scan({ code: text })
    cur.value = r
    pickQty.value = 1
    pickDiscountInput.value = ''
    pickPrice.value = r.sale_price || 0
    pickHint.value = ''
    scanText.value = ''
    scanMsg.value = `已查到：${r.sku_name || r.spu_name}`
    scanMsgType.value = 'ok'
  } catch (e) {
    if (e.response?.status === 404) {
      scanMsg.value = '未找到该条码 / 编号 / 名称对应的商品，请检查后重试'
      scanMsgType.value = 'err'
    } else {
      scanMsg.value = e.response?.data?.detail || '查询失败'
      scanMsgType.value = 'err'
    }
  }
}

// 商品卡：输折扣自动算价
function onPickDiscount() {
  const f = toFactor(pickDiscountInput.value)
  if (f > 0) {
    pickPrice.value = Math.round((cur.value.sale_price || 0) * f * 100) / 100
    pickHint.value = `已按 ${pickDiscountInput.value} 折计算：¥${cur.value.sale_price} × ${f} = ¥${pickPrice.value}`
  } else {
    pickPrice.value = cur.value.sale_price || 0
    pickHint.value = ''
  }
}
// 商品卡：手动改售价 → 清空折扣
function onPickManualPrice() {
  pickDiscountInput.value = ''
  pickHint.value = ''
}

// 加入销售单
function addToCart() {
  if (!cur.value) return
  if (!pickQty.value || pickQty.value <= 0) { alert('请输入正确的销售数量'); return }
  const f = toFactor(pickDiscountInput.value)
  items.value.push({
    _key: newKey(), id: null,
    sku_id: cur.value.sku_id,
    sku_name: cur.value.sku_name || cur.value.spu_name,
    spec_name: cur.value.spec_name || '',
    barcode: cur.value.barcode || '',
    cur_stock: cur.value.stock,
    quantity: pickQty.value,
    discountInput: f > 0 ? pickDiscountInput.value : '',
    discount: f,
    unit_price: pickPrice.value
  })
  scanMsg.value = `已加入销售单：${cur.value.sku_name || cur.value.spu_name}`
  scanMsgType.value = 'ok'
  cur.value = null
  scanText.value = ''
  nextTick(() => scanInput.value?.focus())
}

// 明细行：单独改折扣自动算价
function onRowDiscount(it) {
  const f = toFactor(it.discountInput)
  it.discount = f
  const base = it.sale_price || 0
  if (f > 0) it.unit_price = Math.round(base * f * 100) / 100
}
// 明细行：手动改售价 → 清空该行折扣
function onRowManualPrice(it) {
  it.discountInput = ''
  it.discount = 0
}

function removeItem(i) {
  if (!confirm('确定移除该项吗？')) return
  items.value.splice(i, 1)
}

// ---- 数据 ----
function normalizeItem(it) {
  const f = it.discount || 0
  return {
    _key: newKey(), id: it.id,
    sku_id: it.sku_id,
    sku_name: it.sku_name || '',
    spec_name: it.spec_name || '',
    barcode: it.barcode || '',
    cur_stock: it.cur_stock,
    quantity: it.quantity || 1,
    discountInput: toZhe(f),
    discount: f,
    unit_price: it.unit_price || 0,
    sale_price: it.unit_price || 0   // 回显时以已存售价为基准价
  }
}

async function loadChannels() {
  channels.value = await channelApi.list()
}

async function load() {
  await loadChannels()
  if (!isEdit) return
  const o = await saleApi.get(orderId)
  order.value = o
  form.value = {
    channel_id: o.channel_id || null,
    buyer: o.buyer,
    remark: o.remark
  }
  items.value = (o.items || []).map(normalizeItem)
}

function buildBody() {
  return {
    channel_id: form.value.channel_id,
    buyer: form.value.buyer,
    remark: form.value.remark,
    items: items.value.map(it => ({
      id: it.id, sku_id: it.sku_id,
      quantity: it.quantity, discount: it.discount, unit_price: it.unit_price
    }))
  }
}

function checkReady() {
  if (!items.value.length) { alert('还没有明细，先扫码加一件货吧'); return false }
  for (const it of items.value) {
    if (!it.quantity || it.quantity <= 0) { alert('销售数量必须大于 0'); return false }
    if (it.unit_price === null || it.unit_price === undefined || it.unit_price < 0) {
      alert(`「${it.sku_name}」的实际售价无效`); return false
    }
  }
  return true
}

async function saveDraft() {
  if (!checkReady()) return
  try {
    if (isEdit) {
      await saleApi.update(orderId, buildBody())
    } else {
      const o = await saleApi.create(buildBody())
      router.replace(`/sales/${o.id}`)
      orderIdForConfirm.value = o.id
    }
    alert('草稿已保存，可继续扫码加货')
    if (isEdit) load()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

const orderIdForConfirm = ref(null)

async function confirmOut() {
  if (!checkReady()) return
  let id = orderId
  if (!isEdit) {
    try {
      const o = await saleApi.create(buildBody())
      router.replace(`/sales/${o.id}`)
      id = o.id
    } catch (e) {
      alert(e.response?.data?.detail || '创建销售单失败'); return
    }
  }
  confirming.value = true
  try {
    const r = await saleApi.confirm(id)
    alert(`出库成功！单号 ${r.order_no}，共 ${r.items} 项商品已出库，库存已扣减并留档。`)
    router.push('/sales')
  } catch (e) {
    alert(e.response?.data?.detail || '出库失败，库存已回滚')
  } finally {
    confirming.value = false
  }
}

onMounted(() => {
  load()
  nextTick(() => scanInput.value?.focus())
})
</script>

<style scoped>
.head-panel { margin-bottom: 16px; }
.head-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px 18px; margin-top: 16px;
}
.fitem { display: flex; flex-direction: column; gap: 6px; }
.fitem label { font-size: 13px; color: var(--text-2); }
.fitem input, .fitem select {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.fitem select { min-width: 0; }
.fitem select option, select option { background: #161b38; color: var(--text); }
.head-grid.readonly input, .head-grid.readonly select { opacity: .75; }
.scan-bar { display: flex; gap: 10px; margin: 14px 0 4px; }
.scan-bar input {
  flex: 1; height: 46px; padding: 0 16px; font-size: 15px;
  border-radius: 10px; border: 1px solid var(--primary);
  background: rgba(91, 124, 250, .08); color: var(--text);
  outline: none; letter-spacing: .5px;
}
.scan-bar input:focus { box-shadow: 0 0 0 3px rgba(91, 124, 250, .25); }
.scan-bar button {
  height: 46px; padding: 0 26px; border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600; color: #fff; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.ok-msg { color: #5bd6a8; font-size: 13px; }
.err-msg { color: var(--danger); font-size: 13px; }
.cur-card { border: 1px solid rgba(91,124,250,.4); margin-top: 12px; }
.cur-fields {
  display: flex; gap: 14px; align-items: flex-end;
  margin-top: 18px; flex-wrap: wrap;
}
.f-label { display: block; font-size: 12px; color: var(--text-2); margin-bottom: 6px; }
.cur-fields input {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--primary); background: rgba(91,124,250,.08);
  color: var(--text); font-size: 14px; outline: none;
}
.cur-fields input:focus { box-shadow: 0 0 0 3px rgba(91,124,250,.22); }
.cur-btn button {
  height: 40px; padding: 0 24px; border: none; border-radius: 10px;
  color: #fff; font-size: 14px; font-weight: 600; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; border: 1px solid; }
.tag-draft { color: #e2b45c; border-color: rgba(226,180,92,.5); background: rgba(226,180,92,.12); }
.tag-done { color: #5bd6a8; border-color: rgba(91,214,168,.5); background: rgba(91,214,168,.12); }
.stock-badge {
  display: inline-block; padding: 2px 10px; border-radius: 14px; font-size: 12px;
  color: #8fe0c3; background: rgba(91,214,168,.12); border: 1px solid rgba(91,214,168,.4);
}
.stock-badge.low { color: #ff9d8f; background: rgba(231,76,60,.12); border-color: rgba(231,76,60,.4); }
.mini-btn {
  height: 30px; padding: 0 10px; border-radius: 7px;
  border: 1px solid rgba(91,124,250,.5); background: transparent;
  color: var(--primary); font-size: 12px; cursor: pointer; margin-right: 6px;
}
.mini-btn.danger { border-color: rgba(255,92,92,.5); color: #ff7b7b; }
table input {
  height: 34px; padding: 0 10px; border-radius: 7px;
  border: 1px solid var(--border); background: rgba(255,255,255,.05);
  color: var(--text); font-size: 13px; outline: none;
}
table input:focus { border-color: var(--primary); }
.foot-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.foot-actions button {
  height: 44px; padding: 0 30px; border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600; cursor: pointer;
}
.foot-actions .btn-plain {
  background: transparent; border: 1px solid var(--border); color: var(--text-2);
}
.foot-actions .btn-confirm {
  background: linear-gradient(135deg, #e2b45c, #d99a3f); color: #fff;
}
.foot-actions .btn-confirm:disabled { opacity: .55; cursor: wait; }
</style>
