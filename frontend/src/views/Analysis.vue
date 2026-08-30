<template>
  <div>
    <h2>库存分析</h2>
    <p class="desc">
      库存总览 · 分类分布 · 库存排名 · 出入库趋势 · 畅销 / 滞销 / 低库存预警，图表与数据来自同一批接口，打开页面自动加载
    </p>

    <!-- 库存总览卡片 -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">库存总件数</div>
        <div class="stat-num gold">{{ summary.total_qty || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">库存总价值</div>
        <div class="stat-num">¥{{ fmtMoney(summary.total_value) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">SKU 数</div>
        <div class="stat-num">{{ summary.sku_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">SPU 数</div>
        <div class="stat-num">{{ summary.spu_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">低库存商品</div>
        <div class="stat-num" :style="{ color: (summary.low_stock_count || 0) > 0 ? '#ff7b7b' : '#5bd6a8' }">{{ summary.low_stock_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">滞销商品</div>
        <div class="stat-num" :style="{ color: (summary.stale_count || 0) > 0 ? '#ffb54d' : '#5bd6a8' }">{{ summary.stale_count || 0 }}</div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="chart-grid">
      <!-- 分类库存分布：饼图/柱状图可切换 -->
      <div class="panel chart-box">
        <div style="display: flex; align-items: center; margin-bottom: 4px">
          <b style="letter-spacing: 1px">分类库存分布</b>
          <span style="flex: 1"></span>
          <div class="seg">
            <button :class="{ active: catMode === 'pie' }" @click="setCatMode('pie')">饼图</button>
            <button :class="{ active: catMode === 'bar' }" @click="setCatMode('bar')">柱状图</button>
          </div>
        </div>
        <div ref="catChartRef" class="chart"></div>
      </div>

      <!-- 库存价值 TOP -->
      <div class="panel chart-box">
        <b style="letter-spacing: 1px">库存价值 TOP 10</b>
        <div ref="rankChartRef" class="chart"></div>
      </div>

      <!-- 近 30 天出入库趋势 -->
      <div class="panel chart-box">
        <b style="letter-spacing: 1px">近 30 天出入库趋势</b>
        <div ref="trendChartRef" class="chart"></div>
      </div>

      <!-- 畅销 TOP -->
      <div class="panel chart-box">
        <b style="letter-spacing: 1px">近 30 天畅销 TOP 10</b>
        <div ref="sellChartRef" class="chart"></div>
      </div>
    </div>

    <!-- 数据表格区（与图表同源） -->
    <div class="tables-grid">
      <!-- 低库存预警 -->
      <div class="panel" style="overflow: auto">
        <b style="letter-spacing: 1px">低库存预警（库存 &lt; 10）</b>
        <table style="margin-top: 10px">
          <thead>
            <tr><th>货品</th><th>当前库存</th><th>成本价</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in lowStock" :key="r.sku_id">
              <td style="font-weight: 600">{{ r.name }}</td>
              <td :style="{ color: r.stock <= 0 ? '#ff7b7b' : '#ffb54d' }">{{ r.stock }}</td>
              <td>¥{{ fmtMoney(r.cost_price) }}</td>
            </tr>
            <tr v-if="!lowStock.length"><td colspan="3" class="empty">暂无低库存商品</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 滞销榜 -->
      <div class="panel" style="overflow: auto">
        <b style="letter-spacing: 1px">滞销榜（最近出库最久）</b>
        <table style="margin-top: 10px">
          <thead>
            <tr><th>货品</th><th>当前库存</th><th>最近出库</th><th>天数</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in slowMoving" :key="r.sku_id">
              <td style="font-weight: 600">{{ r.name }}</td>
              <td>{{ r.stock }}</td>
              <td class="muted">{{ r.last_out ? fmtTime(r.last_out) : '从未出库' }}</td>
              <td :style="{ color: r.days >= 30 ? '#ffb54d' : 'inherit' }">{{ r.days }} 天</td>
            </tr>
            <tr v-if="!slowMoving.length"><td colspan="4" class="empty">暂无滞销商品</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 畅销 TOP -->
      <div class="panel" style="overflow: auto">
        <b style="letter-spacing: 1px">畅销 TOP 10（近 30 天出库）</b>
        <table style="margin-top: 10px">
          <thead>
            <tr><th>货品</th><th>出库件数</th><th>出库金额</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in sellingTop" :key="r.sku_id">
              <td style="font-weight: 600">{{ r.name }}</td>
              <td>{{ r.qty }}</td>
              <td style="color: var(--gold)">¥{{ fmtMoney(r.amount) }}</td>
            </tr>
            <tr v-if="!sellingTop.length"><td colspan="3" class="empty">近 30 天暂无出库记录</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { analysisApi } from '../api'

const summary = ref({})
const lowStock = ref([])
const slowMoving = ref([])
const sellingTop = ref([])
const categoryRows = ref([])

const catMode = ref('pie')
const catChartRef = ref(null)
const rankChartRef = ref(null)
const trendChartRef = ref(null)
const sellChartRef = ref(null)

let catChart = null
let rankChart = null
let trendChart = null
let sellChart = null

const PALETTE = ['#5b7cfa', '#8f6ce6', '#f0c96a', '#5bd6a8', '#ff9f6b', '#ff7b7b', '#4fc3f7', '#b388ff', '#69d0c9', '#ffd54f']

function fmtMoney(v) {
  if (v === null || v === undefined || isNaN(v)) return '0.00'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtTime(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 10)
}
function baseOption() {
  return {
    color: PALETTE,
    textStyle: { color: '#b8c0e0', fontFamily: 'inherit' },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,26,61,.95)', borderColor: 'rgba(91,124,250,.4)', textStyle: { color: '#e6eaff' } },
    grid: { left: 10, right: 16, top: 36, bottom: 10, containLabel: true }
  }
}

function renderCatChart() {
  if (!catChart) return
  const rows = categoryRows.value
  if (catMode.value === 'pie') {
    catChart.setOption({
      ...baseOption(),
      tooltip: { trigger: 'item', formatter: '{b}<br/>库存 {c} 件（{d}%）', backgroundColor: 'rgba(20,26,61,.95)', borderColor: 'rgba(91,124,250,.4)', textStyle: { color: '#e6eaff' } },
      series: [{
        type: 'pie', radius: ['42%', '68%'], center: ['50%', '52%'],
        itemStyle: { borderRadius: 6, borderColor: '#10153a', borderWidth: 2 },
        label: { color: '#b8c0e0', formatter: '{b}\n{c} 件' },
        data: rows.map(r => ({ name: r.category_name, value: r.qty }))
      }]
    })
  } else {
    catChart.setOption({
      ...baseOption(),
      xAxis: { type: 'category', data: rows.map(r => r.category_name), axisLabel: { color: '#b8c0e0' }, axisLine: { lineStyle: { color: 'rgba(91,124,250,.35)' } } },
      yAxis: { type: 'value', axisLabel: { color: '#b8c0e0' }, splitLine: { lineStyle: { color: 'rgba(120,140,220,.12)' } } },
      series: [{
        type: 'bar', barMaxWidth: 36,
        data: rows.map(r => r.qty),
        itemStyle: { borderRadius: [6, 6, 0, 0], color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#5b7cfa' }, { offset: 1, color: '#8f6ce6' }]) }
      }]
    })
  }
}

function renderRankChart() {
  if (!rankChart) return
  // 价值 TOP 横向柱：取前 10，倒序展示使最大值在上方
  const rows = rankRows.slice(0, 10).reverse()
  rankChart.setOption({
    ...baseOption(),
    grid: { left: 8, right: 60, top: 8, bottom: 10, containLabel: true },
    tooltip: { ...baseOption().tooltip, formatter: (p) => `${p.name}<br/>库存价值 ¥${fmtMoney(p.value)}（${p.data.stock} 件）` },
    xAxis: { type: 'value', axisLabel: { color: '#b8c0e0' }, splitLine: { lineStyle: { color: 'rgba(120,140,220,.12)' } } },
    yAxis: { type: 'category', data: rows.map(r => r.name), axisLabel: { color: '#b8c0e0', width: 130, overflow: 'truncate' }, axisLine: { lineStyle: { color: 'rgba(91,124,250,.35)' } } },
    series: [{
      type: 'bar', barMaxWidth: 14,
      data: rows.map(r => ({ value: r.value, stock: r.stock })),
      itemStyle: { borderRadius: [0, 6, 6, 0], color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#8f6ce6' }, { offset: 1, color: '#f0c96a' }]) }
    }]
  })
}

function renderTrendChart() {
  if (!trendChart) return
  const rows = trendRows
  trendChart.setOption({
    ...baseOption(),
    xAxis: { type: 'category', data: rows.map(r => r.date.slice(5)), axisLabel: { color: '#b8c0e0' }, axisLine: { lineStyle: { color: 'rgba(91,124,250,.35)' } } },
    yAxis: { type: 'value', axisLabel: { color: '#b8c0e0' }, splitLine: { lineStyle: { color: 'rgba(120,140,220,.12)' } } },
    legend: { data: ['入库件数', '出库件数'], textStyle: { color: '#b8c0e0' }, top: 0, right: 8 },
    series: [
      { name: '入库件数', type: 'line', smooth: true, data: rows.map(r => r.in_qty), itemStyle: { color: '#5bd6a8' }, areaStyle: { color: 'rgba(91,214,168,.18)' } },
      { name: '出库件数', type: 'line', smooth: true, data: rows.map(r => r.out_qty), itemStyle: { color: '#ff9f6b' }, areaStyle: { color: 'rgba(255,159,107,.15)' } }
    ]
  })
}

function renderSellChart() {
  if (!sellChart) return
  const rows = sellingTop.value.slice(0, 10)
  sellChart.setOption({
    ...baseOption(),
    xAxis: { type: 'category', data: rows.map(r => r.name), axisLabel: { color: '#b8c0e0', interval: 0, rotate: 28, width: 110, overflow: 'truncate' }, axisLine: { lineStyle: { color: 'rgba(91,124,250,.35)' } } },
    yAxis: { type: 'value', axisLabel: { color: '#b8c0e0' }, splitLine: { lineStyle: { color: 'rgba(120,140,220,.12)' } } },
    tooltip: { ...baseOption().tooltip, formatter: (p) => `${p.name}<br/>出库 ${p.value} 件<br/>金额 ¥${fmtMoney(p.data.amount)}` },
    series: [{
      type: 'bar', barMaxWidth: 34,
      data: rows.map(r => ({ value: r.qty, amount: r.amount })),
      itemStyle: { borderRadius: [6, 6, 0, 0], color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#f0c96a' }, { offset: 1, color: '#ff9f6b' }]) }
    }]
  })
}

const rankRows = ref([])
const trendRows = ref([])

function setCatMode(mode) {
  catMode.value = mode
  renderCatChart()
}

function resizeAll() {
  ;[catChart, rankChart, trendChart, sellChart].forEach((c) => c && c.resize())
}

async function loadAll() {
  try {
    const [s, cat, rank, sell, slow, low, trend] = await Promise.all([
      analysisApi.summary(),
      analysisApi.categoryStock(),
      analysisApi.stockRank({ limit: 10, order: 'value' }),
      analysisApi.sellingTop({ limit: 10, days: 30 }),
      analysisApi.slowMoving({ limit: 10 }),
      analysisApi.lowStock({ limit: 50 }),
      analysisApi.trend({ days: 30 })
    ])
    summary.value = s
    categoryRows.value = cat.rows || []
    rankRows.value = rank.rows || []
    sellingTop.value = sell.rows || []
    slowMoving.value = slow.rows || []
    lowStock.value = low.rows || []
    trendRows.value = trend.rows || []
    renderCatChart()
    renderRankChart()
    renderTrendChart()
    renderSellChart()
  } catch (e) {
    alert(e.response?.data?.detail || '加载库存分析数据失败')
  }
}

onMounted(() => {
  catChart = echarts.init(catChartRef.value)
  rankChart = echarts.init(rankChartRef.value)
  trendChart = echarts.init(trendChartRef.value)
  sellChart = echarts.init(sellChartRef.value)
  window.addEventListener('resize', resizeAll)
  loadAll()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  ;[catChart, rankChart, trendChart, sellChart].forEach((c) => c && c.dispose())
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
.chart-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px;
}
.tables-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
}
.chart-box { min-width: 0; }
.chart { width: 100%; height: 300px; }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.seg button {
  height: 26px; padding: 0 12px; border: none; background: transparent;
  color: var(--text-2); cursor: pointer; font-size: 12px;
}
.seg button.active {
  background: linear-gradient(135deg, rgba(91, 124, 250, .35), rgba(143, 108, 230, .3));
  color: #fff;
}
@media (max-width: 1100px) {
  .chart-grid, .tables-grid { grid-template-columns: 1fr; }
}
</style>
