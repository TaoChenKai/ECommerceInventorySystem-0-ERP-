<template>
  <div>
    <h2>扫码出入库</h2>
    <p class="desc">扫条码 / 输入编号查询商品，选择渠道后完成入库或出库</p>

    <!-- 库存概览 -->
    <div class="cards">
      <div class="mini-card"><div class="mini-num">{{ summary.total_spu || 0 }}</div><div class="mini-label">商品款式</div></div>
      <div class="mini-card"><div class="mini-num">{{ summary.total_sku || 0 }}</div><div class="mini-label">规格总量</div></div>
      <div class="mini-card"><div class="mini-num gold">{{ summary.total_stock || 0 }}</div><div class="mini-label">总库存</div></div>
      <div class="mini-card warn"><div class="mini-num">{{ summary.low_stock_sku || 0 }}</div><div class="mini-label">低库存</div></div>
    </div>
    <div v-if="summary.low_stock_list && summary.low_stock_list.length" class="low-tip">
      低库存提醒：
      <span v-for="(s, i) in summary.low_stock_list" :key="i" style="margin-right: 14px">
        {{ s.sku_name }}（剩 {{ s.stock }}）
      </span>
    </div>

    <!-- 扫码区 -->
    <div class="scan-bar">
      <input
        ref="scanInput"
        v-model="scanText"
        placeholder="扫码或输入商品编号 / 条码 / 名称，回车查询"
        @keyup.enter="doScan"
      />
      <button @click="doScan">查询</button>
    </div>

    <!-- 商品结果 -->
    <div v-if="cur" class="panel">
      <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap">
        <div style="flex: 1; min-width: 220px">
          <div style="font-size: 20px; font-weight: 700; color: var(--primary-2)">{{ cur.spu_name }}</div>
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
          <div class="muted" style="font-size: 13px">当前库存（{{ cur.unit }}）</div>
          <div class="muted" style="font-size: 13px; margin-top: 4px">
            进价 ¥{{ cur.cost_price }} ｜ 售价 ¥{{ cur.sale_price }}
          </div>
        </div>
      </div>

      <div style="display: flex; gap: 12px; align-items: flex-end; margin-top: 20px; flex-wrap: wrap">
        <div>
          <label class="f-label">数量</label>
          <input v-model.number="qty" type="number" min="1" style="width: 110px" placeholder="数量" />
        </div>
        <div>
          <label class="f-label">渠道（出库必选，用于统计）</label>
          <select v-model="channelId" style="min-width: 150px">
            <option :value="null">不指定</option>
            <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div style="flex: 1; min-width: 160px">
          <label class="f-label">备注（可选）</label>
          <input v-model="remark" style="width: 100%" placeholder="如：补货 / 平台大促 / 瑕疵退返" />
        </div>
        <div style="display: flex; gap: 10px">
          <button class="btn-in" @click="submit('in')">入库</button>
          <button class="btn-out" @click="submit('out')">出库</button>
        </div>
      </div>
      <div v-if="msg" :class="msgType === 'ok' ? 'ok-msg' : 'err-msg'" style="margin-top: 12px">{{ msg }}</div>
    </div>

    <div v-else-if="notFound" class="panel muted" style="text-align: center; padding: 30px">
      未找到该条码 / 编号对应的商品，请检查后重试。
    </div>

    <div v-else class="panel muted" style="text-align: center; padding: 40px">
      扫描枪扫一下条码，或手动输入编号后回车，即可开始操作。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { stockApi, channelApi } from '../api'

const scanInput = ref(null)
const scanText = ref('')
const cur = ref(null)
const notFound = ref(false)
const qty = ref(1)
const channelId = ref(null)
const remark = ref('')
const msg = ref('')
const msgType = ref('ok')
const channels = ref([])
const summary = ref({})

async function loadSummary() {
  summary.value = await stockApi.summary()
}

async function loadChannels() {
  channels.value = await channelApi.list()
}

async function doScan() {
  const text = scanText.value.trim()
  if (!text) return
  notFound.value = false
  cur.value = null
  msg.value = ''
  // 优先按条码/编号精确查，再按 sku_id 不可行则按名称模糊
  try {
    cur.value = await stockApi.scan({ code: text })
  } catch (e) {
    if (e.response?.status === 404) {
      notFound.value = true
    } else {
      alert(e.response?.data?.detail || '查询失败')
    }
  }
}

async function submit(type) {
  if (!cur.value) return
  if (!qty.value || qty.value <= 0) {
    msg.value = '请输入正确的数量'
    msgType.value = 'err'
    return
  }
  const payload = {
    code: cur.value.barcode || '',
    sku_id: cur.value.sku_id,
    quantity: qty.value,
    channel_id: channelId.value,
    remark: remark.value
  }
  try {
    const r = type === 'in' ? await stockApi.stockIn(payload) : await stockApi.stockOut(payload)
    cur.value.stock = r.stock
    msg.value = `${type === 'in' ? '入库' : '出库'}成功，当前库存 ${r.stock}`
    msgType.value = 'ok'
    remark.value = ''
    qty.value = 1
    loadSummary()
    nextTick(() => scanInput.value?.focus())
  } catch (e) {
    msg.value = e.response?.data?.detail || '操作失败'
    msgType.value = 'err'
  }
}

onMounted(() => {
  loadSummary()
  loadChannels()
  nextTick(() => scanInput.value?.focus())
})
</script>

<style scoped>
.cards {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin-bottom: 14px;
}
.mini-card {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 18px;
}
.mini-num { font-size: 26px; font-weight: 800; color: var(--primary-2); }
.mini-num.gold { color: var(--gold); }
.mini-num.warn { color: var(--danger); }
.mini-label { font-size: 13px; color: var(--text-2); margin-top: 2px; }
.low-tip {
  background: rgba(231, 76, 60, .12); border: 1px solid rgba(231, 76, 60, .35);
  color: #ff9d8f; border-radius: 10px; padding: 10px 14px;
  font-size: 13px; margin-bottom: 14px;
}
.scan-bar {
  display: flex; gap: 10px; margin-bottom: 16px;
}
.scan-bar input {
  flex: 1; height: 46px; padding: 0 16px; font-size: 15px;
  border-radius: 10px; border: 1px solid var(--primary);
  background: rgba(91, 124, 250, .08); color: var(--text);
  outline: none; letter-spacing: .5px;
}
.scan-bar input:focus { box-shadow: 0 0 0 3px rgba(91, 124, 250, .25); }
.f-label { display: block; font-size: 12px; color: var(--text-2); margin-bottom: 6px; }
.btn-in, .btn-out {
  height: 42px; padding: 0 26px; border: none; border-radius: 10px;
  font-size: 15px; font-weight: 600; color: #fff; cursor: pointer;
}
.btn-in { background: linear-gradient(135deg, #37b38a, #2a9d78); }
.btn-out { background: linear-gradient(135deg, #e2b45c, #d99a3f); }
.ok-msg { color: #5bd6a8; }
.err-msg { color: var(--danger); }
</style>
