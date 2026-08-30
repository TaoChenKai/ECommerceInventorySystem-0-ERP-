<template>
  <div>
    <h2>商品档案</h2>
    <p class="desc">商品款式(SPU) + 规格(SKU) 管理，支持秒账数据一键导入</p>

    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索名称 / 编号" style="width: 220px" @keyup.enter="load" />
      <select v-model="filterCat" @change="load" style="min-width: 130px">
        <option value="0">全部分类</option>
        <option v-for="c in cats" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <button @click="load">查询</button>
      <span style="flex: 1"></span>
      <button v-if="isBossOrAdmin" style="background: linear-gradient(135deg,#c0392b,#96281b)" @click="openBatchDelete">批量删除</button>
      <button style="background: linear-gradient(135deg,#e2b45c,#d99a3f)" @click="showImport = true">秒账导入</button>
      <button style="background: linear-gradient(135deg,#37b38a,#2a9d78)" @click="openCat">分类管理</button>
      <button @click="goNew">新建商品</button>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th style="width: 60px">主图</th>
            <th>编号</th>
            <th>名称</th>
            <th>分类</th>
            <th>单位</th>
            <th>规格数</th>
            <th>总库存</th>
            <th>材质</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in products" :key="p.id">
            <td>
              <img v-if="mainImg(p)" :src="mainImg(p)" class="thumb" alt="" />
              <span v-else class="muted">—</span>
            </td>
            <td class="muted">{{ p.code || '—' }}</td>
            <td>
              <a style="color: var(--primary-2); cursor: pointer; text-decoration: none" @click="goEdit(p.id)">{{ p.name }}</a>
            </td>
            <td>{{ p.category_name || '—' }}</td>
            <td>{{ p.unit }}</td>
            <td>{{ p.sku_count }}</td>
            <td style="color: var(--gold)">{{ p.total_stock }}</td>
            <td class="muted">{{ p.material || '—' }}</td>
            <td class="muted" style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ p.remark || '—' }}</td>
            <td>
              <button style="border-color: rgba(91,124,250,.5); color: var(--primary)" @click="goEdit(p.id)">编辑</button>
              <button @click="remove(p)">删除</button>
            </td>
          </tr>
          <tr v-if="!products.length">
            <td colspan="10" class="empty">暂无商品，点击「新建商品」或「秒账导入」开始建档</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 秒账导入弹窗 -->
    <div v-if="showImport" class="modal-mask" @click.self="showImport = false">
      <div class="modal">
        <h3>秒账数据导入</h3>
        <p class="muted" style="margin: 8px 0 14px">
          支持 .xlsx / .csv。表头需包含常见列名（名称、编号、规格、条码、进价、售价、库存、分类、单位）。
          同一商品多行 = 多个规格。编号或名称已存在的商品会自动跳过。
        </p>
        <input type="file" ref="fileInput" accept=".xlsx,.xls,.csv" style="color: var(--text)" />
        <div v-if="importing" class="muted" style="margin-top: 10px">正在解析导入...</div>
        <div v-if="importResult" style="margin-top: 12px; font-size: 14px; line-height: 1.9">
          <div style="color: var(--gold)">导入完成：新建商品 <b>{{ importResult.created_spu }}</b> 个，规格 <b>{{ importResult.created_sku }}</b> 个，跳过 <b>{{ importResult.skipped_count }}</b> 条</div>
          <div v-if="importResult.skipped.length" class="muted" style="max-height: 140px; overflow: auto">
            <div v-for="(s, i) in importResult.skipped" :key="i">{{ s }}</div>
          </div>
        </div>
        <div v-if="importError" style="margin-top: 12px; color: var(--danger); font-size: 14px">{{ importError }}</div>
        <div class="modal-actions">
          <button class="btn-plain" @click="showImport = false">关闭</button>
          <button @click="doImport">开始导入</button>
        </div>
      </div>
    </div>

    <!-- 分类管理弹窗 -->
    <div v-if="showCat" class="modal-mask" @click.self="showCat = false">
      <div class="modal">
        <h3>分类管理</h3>
        <div style="display: flex; gap: 8px; margin: 14px 0">
          <input v-model="newCat" placeholder="新分类名称" style="flex: 1" @keyup.enter="addCat" />
          <button @click="addCat">新增</button>
        </div>
        <table>
          <thead>
            <tr><th>分类</th><th>备注</th><th style="width: 70px">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in cats" :key="c.id">
              <td>{{ c.name }}</td>
              <td class="muted">{{ c.remark }}</td>
              <td><button @click="delCat(c)">删除</button></td>
            </tr>
            <tr v-if="!cats.length"><td colspan="3" class="empty">暂无分类</td></tr>
          </tbody>
        </table>
        <div class="modal-actions">
          <button class="btn-plain" @click="showCat = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 批量删除弹窗 -->
    <div v-if="showBatch" class="modal-mask" @click.self="closeBatch">
      <div class="modal" style="width: 860px">
        <h3>批量删除（移入回收站）</h3>
        <p class="muted" style="margin: 6px 0 12px">删除仅移入回收站，30 天内可在「回收站」还原，历史出入库记录保留</p>

        <div class="batch-head">
          <select v-model="batchDays" style="min-width: 120px" @change="runAnalyze">
            <option v-for="d in dayOptions" :key="d.value" :value="d.value">{{ d.label }}</option>
          </select>
          <button @click="runAnalyze" :disabled="analyzing">{{ analyzing ? '分析中...' : '智能分析' }}</button>
          <span v-if="analyzed" class="muted">建议关注 <b style="color: var(--gold)">{{ analyzeInfo }}</b> 条货品</span>
        </div>

        <div v-if="analyzeItems.length" class="batch-table">
          <div class="batch-tools">
            <label><input type="checkbox" :checked="allChecked" @change="toggleAll" /> 全选</label>
            <button class="mini-btn" @click="invertSelection">反选</button>
            <span class="muted">已选 {{ selectedIds.length }} 条</span>
          </div>
          <table>
            <thead>
              <tr>
                <th style="width: 44px">选</th>
                <th>名称</th>
                <th>编码</th>
                <th>库存</th>
                <th>最后变动</th>
                <th>积压天数</th>
                <th>建议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in analyzeItems" :key="it.id">
                <td><input type="checkbox" :value="it.id" v-model="selectedIds" /></td>
                <td>{{ it.name }}</td>
                <td class="muted">{{ it.code || '—' }}</td>
                <td :style="{ color: it.total_stock > 0 ? 'var(--gold)' : 'var(--danger)' }">{{ it.total_stock }}</td>
                <td class="muted">{{ fmtTime(it.last_change_at) }}</td>
                <td class="muted">{{ it.idle_days }} 天</td>
                <td><span class="tag" :class="it.total_stock > 0 ? 'tag-warn' : 'tag-hot'">{{ it.suggestion }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="analyzed && !analyzing" class="muted" style="padding: 14px 0">该时间范围内没有符合条件的货品</div>

        <div class="modal-actions">
          <button class="btn-plain" @click="closeBatch">取消</button>
          <button style="background: linear-gradient(135deg,#c0392b,#96281b)" :disabled="!selectedIds.length" @click="confirmBatchDelete">删除所选（{{ selectedIds.length }}）</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { productApi, categoryApi, recycleApi } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const isBossOrAdmin = computed(() => auth.isBoss || auth.isAdmin)
const products = ref([])
const cats = ref([])
const keyword = ref('')
const filterCat = ref(0)

const showImport = ref(false)
const importing = ref(false)
const importResult = ref(null)
const importError = ref('')

const showCat = ref(false)
const newCat = ref('')

// 批量删除（v1.3）
const showBatch = ref(false)
const batchDays = ref(180)
const analyzing = ref(false)
const analyzed = ref(false)
const analyzeInfo = ref(0)
const analyzeItems = ref([])
const selectedIds = ref([])
const dayOptions = [
  { value: 30, label: '1个月' },
  { value: 60, label: '2个月' },
  { value: 90, label: '3个月' },
  { value: 120, label: '4个月' },
  { value: 150, label: '5个月' },
  { value: 180, label: '6个月' },
  { value: 365, label: '1年' },
  { value: 730, label: '2年' },
  { value: 1095, label: '3年' }
]
const allChecked = computed(() => analyzeItems.value.length > 0 && selectedIds.value.length === analyzeItems.value.length)

async function load() {
  products.value = await productApi.list({
    keyword: keyword.value,
    category_id: filterCat.value
  })
}

async function loadCats() {
  cats.value = await categoryApi.list()
}

function goNew() { router.push('/products/new') }
function goEdit(id) { router.push(`/products/${id}`) }

function mainImg(p) {
  const imgs = p.images || []
  if (imgs.length) {
    const main = imgs.find(i => i.img_type === 'main') || imgs[0]
    if (main?.url) return main.url
  }
  return p.image_url || ''
}

async function remove(p) {
  if (!confirm(`确定将商品「${p.name}」移入回收站吗？其下所有规格一并移入，可在「回收站」还原。`)) return
  await productApi.remove(p.id)
  load()
}

// ---------- 批量删除（v1.3） ----------
function openBatchDelete() {
  showBatch.value = true
  if (!analyzed.value) runAnalyze()
}
function closeBatch() {
  showBatch.value = false
  selectedIds.value = []
}
function toggleAll(e) {
  selectedIds.value = e.target.checked ? analyzeItems.value.map((i) => i.id) : []
}
function invertSelection() {
  const all = analyzeItems.value.map((i) => i.id)
  selectedIds.value = all.filter((id) => !selectedIds.value.includes(id))
}
async function runAnalyze() {
  analyzing.value = true
  try {
    const data = await recycleApi.analyze(batchDays.value)
    analyzeItems.value = data.items || []
    analyzeInfo.value = data.count || 0
    analyzed.value = true
    selectedIds.value = []
  } catch (e) {
    alert(e.response?.data?.detail || '智能分析失败')
  } finally {
    analyzing.value = false
  }
}
async function confirmBatchDelete() {
  if (!selectedIds.value.length) return
  if (!confirm(`确定将所选 ${selectedIds.value.length} 条货品移入回收站吗？删除后可在「回收站」还原。`)) return
  try {
    await recycleApi.batchDelete(selectedIds.value)
    closeBatch()
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '批量删除失败')
  }
}
function fmtTime(t) {
  if (!t) return '—'
  const d = new Date(t)
  if (isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

async function doImport() {
  const file = document.querySelector('input[type=file]').files[0]
  if (!file) { importError.value = '请先选择文件'; return }
  importing.value = true
  importError.value = ''
  importResult.value = null
  try {
    importResult.value = await productApi.importExcel(file)
  } catch (e) {
    importError.value = e.response?.data?.detail || '导入失败，请检查文件格式'
  } finally {
    importing.value = false
    load()
  }
}

async function addCat() {
  const name = newCat.value.trim()
  if (!name) return
  await categoryApi.create({ name })
  newCat.value = ''
  loadCats()
}

async function delCat(c) {
  if (!confirm(`确定删除分类「${c.name}」吗？`)) return
  try {
    await categoryApi.remove(c.id)
    loadCats()
    if (filterCat.value == c.id) filterCat.value = 0
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

function openCat() {
  showCat.value = true
  loadCats()
}

onMounted(() => { load(); loadCats() })
</script>

<style scoped>
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
}
.thumb {
  width: 44px; height: 44px; object-fit: cover; border-radius: 8px;
  border: 1px solid var(--border); background: rgba(0,0,0,.25);
}
.modal {
  width: 560px; max-width: 92vw; max-height: 80vh; overflow: auto;
  background: var(--panel-strong);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 4px; letter-spacing: 1px; }
.modal input[type=text] {
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
.batch-head {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
}
.batch-table {
  border: 1px solid var(--border); border-radius: 10px; overflow: auto; max-height: 46vh;
}
.batch-tools {
  display: flex; align-items: center; gap: 12px; padding: 8px 12px;
  background: rgba(255,255,255,.04); border-bottom: 1px solid var(--border);
  font-size: 13px; position: sticky; top: 0; z-index: 2;
}
.mini-btn {
  height: 26px; padding: 0 10px; font-size: 12px;
  background: transparent; border: 1px solid var(--border); color: var(--text-2); cursor: pointer; border-radius: 6px;
}
.mini-btn:hover { color: var(--primary); border-color: var(--primary); }
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; white-space: nowrap;
}
.tag-hot { background: rgba(231,76,60,.18); color: #ff7b6b; }
.tag-warn { background: rgba(226,180,92,.16); color: var(--gold); }
</style>
