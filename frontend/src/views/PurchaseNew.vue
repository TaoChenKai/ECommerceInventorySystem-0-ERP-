<template>
  <div>
    <h2>{{ isEdit ? (order.status === 'done' ? '采购单详情' : '编辑采购单') : '新建采购单' }}</h2>
    <p class="desc">扫条码加货 → 没扫到的现场建档 → 全部确认后统一入库，自动转入商品档案</p>

    <!-- 单头信息 -->
    <div class="panel head-panel">
      <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap">
        <b style="font-size: 16px; letter-spacing: 1px; color: var(--primary-2)">{{ order.order_no || '待保存生成单号' }}</b>
        <span v-if="order.status" :class="'tag tag-' + order.status">{{ statusName(order.status) }}</span>
        <span style="flex: 1"></span>
        <span v-if="order.operator" class="muted" style="font-size: 13px">经办：{{ order.operator }}</span>
      </div>

      <div class="head-grid" :class="{ readonly: order.status === 'done' }">
        <div class="fitem">
          <label>供应商（采购商）*</label>
          <div style="display: flex; gap: 6px">
            <select v-model="form.supplier_id">
              <option :value="null">请选择供应商</option>
              <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <button class="mini-btn" title="快捷新增供应商" @click="quickSup = true">+ 新增</button>
          </div>
        </div>
        <div class="fitem">
          <label>采购方式</label>
          <input v-model="form.purchase_method" list="methodList" placeholder="如：现货采购 / 定金订货 / 一件代发" />
          <datalist id="methodList">
            <option value="现货采购" />
            <option value="定金订货" />
            <option value="赊账采购" />
            <option value="一件代发" />
          </datalist>
        </div>
        <div class="fitem">
          <label>采购日期</label>
          <input v-model="form.order_date" type="date" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>备注</label>
          <input v-model="form.remark" placeholder="批次说明 / 到货说明等，可留空" />
        </div>
      </div>
    </div>

    <!-- 扫码区 -->
    <div class="scan-bar" v-if="order.status !== 'done'">
      <input
        ref="scanInput"
        v-model="scanText"
        placeholder="扫条码 / 输编号 / 输名称，回车加货；没扫到的货会提示现场建档"
        @keyup.enter="doScan"
      />
      <button @click="doScan">扫码加货</button>
    </div>
    <div v-if="scanMsg" :class="scanMsgType === 'ok' ? 'ok-msg' : 'err-msg'" style="margin: 6px 0 10px">{{ scanMsg }}</div>

    <!-- 明细 -->
    <div class="panel" style="overflow: auto">
      <div style="display: flex; align-items: center; margin-bottom: 10px">
        <b style="letter-spacing: 1px">采购明细（{{ items.length }} 项）</b>
        <span style="flex: 1"></span>
        <div class="muted" style="font-size: 13px">
          数量合计 <b style="color: var(--gold)">{{ totalQty }}</b>
          ｜ 金额合计 <b style="color: var(--gold)">¥{{ totalAmount }}</b>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th style="width: 50px">#</th>
            <th>货品</th>
            <th>条码</th>
            <th style="width: 90px">状态</th>
            <th style="width: 110px">数量</th>
            <th style="width: 130px">单价(¥)</th>
            <th style="width: 120px">金额</th>
            <th style="width: 150px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in items" :key="it._key">
            <td class="muted">{{ i + 1 }}</td>
            <td>
              <div style="font-weight: 600">{{ it.sku_name || it.draft_name || '未命名货品' }}</div>
              <div class="muted" style="font-size: 12px" v-if="it.draft_spec || it.sku_name">规格：{{ it.draft_spec || '—' }}</div>
            </td>
            <td class="muted">{{ it.barcode || it.draft_barcode || '—' }}</td>
            <td>
              <span :class="'tag ' + (it.status === 'draft' ? 'tag-draft' : 'tag-done')">
                {{ it.status === 'draft' ? '待建档' : '已在库' }}
              </span>
            </td>
            <td>
              <input v-if="order.status !== 'done'" v-model.number="it.quantity" type="number" min="1" style="width: 80px" />
              <span v-else>{{ it.quantity }}</span>
            </td>
            <td>
              <input v-if="order.status !== 'done'" v-model.number="it.unit_price" type="number" min="0" step="0.01" style="width: 100px" />
              <span v-else>¥{{ it.unit_price }}</span>
            </td>
            <td style="color: var(--gold)">¥{{ ((it.quantity || 0) * (it.unit_price || 0)).toFixed(2) }}</td>
            <td>
              <template v-if="order.status !== 'done'">
                <button v-if="it.status === 'draft'" class="mini-btn" @click="openForm(it)">补全档案</button>
                <button class="mini-btn danger" @click="removeItem(i)">移除</button>
              </template>
              <span v-else class="muted">—</span>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="8" class="empty">还没有明细，用上面的扫码框扫一件货开始</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 底部操作 -->
    <div class="foot-actions" v-if="order.status !== 'done'">
      <button class="btn-plain" @click="saveDraft">保存草稿</button>
      <button class="btn-confirm" @click="confirmIn" :disabled="confirming">
        {{ confirming ? '入库中...' : '确认入库（自动建档 + 加库存）' }}
      </button>
    </div>
    <div v-else class="muted" style="margin-top: 14px; font-size: 13px">
      该单已于 {{ order.confirmed_at }} 入库完成，如需补货请新建采购单。
    </div>

    <!-- 扫码未命中 → 询问是否新建 -->
    <div v-if="showAskNew" class="modal-mask" @click.self="showAskNew = false">
      <div class="modal" style="width: 460px">
        <h3 style="color: #ffd47e">未找到该货品</h3>
        <p style="margin: 14px 0 6px; line-height: 1.8">
          仓库里没有「<b>{{ scanText }}</b>」对应的货。你是要
        </p>
        <p class="muted" style="font-size: 13px; margin-bottom: 16px">现场给它建档吗？建档后回到本单直接入库。</p>
        <div class="modal-actions">
          <button class="btn-plain" @click="showAskNew = false">取消</button>
          <button @click="openFormForNew">新建货品并加入本单</button>
        </div>
      </div>
    </div>

    <!-- 建档弹窗（新建 / 补全档案） -->
    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal" style="width: 720px">
        <h3>{{ editingItem ? '补全货品档案' : '新建货品档案' }}</h3>
        <p class="muted" style="margin: 6px 0 14px; font-size: 13px">
          把货品信息填全，点「加入采购单」后进入明细；确认入库时自动建档并加库存。
        </p>

        <div class="form-grid">
          <div class="fitem" style="grid-column: 1 / -1">
            <ImageUploader v-model="formData.images" title="货品图片" hint="上传商品图片 / 样式图，多张不限" type="main" />
          </div>
          <div class="fitem">
            <label>货品名称 *</label>
            <input v-model="formData.name" placeholder="如：粉色兔耳朵钥匙扣" />
          </div>
          <div class="fitem">
            <label>货品编号</label>
            <input v-model="formData.code" placeholder="工厂一维码，可留空" />
          </div>
          <div class="fitem">
            <label>规格</label>
            <input v-model="formData.spec" placeholder="如：大号 / 红色" />
          </div>
          <div class="fitem">
            <label>条码</label>
            <input v-model="formData.barcode" placeholder="刚扫的码已带出，可改" />
          </div>
          <div class="fitem">
            <label>分类</label>
            <input v-model="formData.category_name" list="pf-cat-options" placeholder="未分类或输入新分类名称" />
            <datalist id="pf-cat-options">
              <option v-for="c in cats" :key="c.id" :value="c.name" />
            </datalist>
          </div>
          <div class="fitem">
            <label>单位</label>
            <input v-model="formData.unit" list="pf-unit-options" placeholder="件 / 个 / 键... 可直接输入新单位" />
            <datalist id="pf-unit-options">
              <option v-for="u in units" :key="u" :value="u" />
            </datalist>
          </div>
          <div class="fitem">
            <label>重量</label>
            <input v-model.number="formData.weight" type="number" step="0.01" min="0" />
          </div>
          <div class="fitem">
            <label>重量单位</label>
            <input v-model="formData.weight_unit" list="pf-wunit-options" placeholder="克 / 千克 / 吨 / 斤... 可直接输入新单位" />
            <datalist id="pf-wunit-options">
              <option v-for="w in weightUnits" :key="w" :value="w" />
            </datalist>
          </div>
          <div class="fitem">
            <label>数量 *</label>
            <input v-model.number="formData.quantity" type="number" min="1" />
          </div>
          <div class="fitem">
            <label>进价（单价）</label>
            <input v-model.number="formData.unit_price" type="number" min="0" step="0.01" />
          </div>
          <div class="fitem" style="grid-column: 1 / -1">
            <label>详细介绍 / 备注</label>
            <textarea v-model="formData.remark" rows="2" placeholder="材质 / 样式说明 / 厂家信息等"></textarea>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-plain" @click="showForm = false">取消</button>
          <button @click="saveFormItem">加入采购单</button>
        </div>
      </div>
    </div>

    <!-- 快捷新增供应商 -->
    <div v-if="quickSup" class="modal-mask" @click.self="quickSup = false">
      <div class="modal" style="width: 460px">
        <h3>新增供应商</h3>
        <div style="display: grid; gap: 10px; margin-top: 16px">
          <input v-model="supForm.name" placeholder="供应商名称 *" style="height: 38px; padding: 0 12px; border-radius: 9px; border: 1px solid var(--border); background: rgba(255,255,255,.06); color: var(--text); outline: none" />
          <input v-model="supForm.contact" placeholder="联系人（可留空）" style="height: 38px; padding: 0 12px; border-radius: 9px; border: 1px solid var(--border); background: rgba(255,255,255,.06); color: var(--text); outline: none" />
          <input v-model="supForm.phone" placeholder="联系电话（可留空）" style="height: 38px; padding: 0 12px; border-radius: 9px; border: 1px solid var(--border); background: rgba(255,255,255,.06); color: var(--text); outline: none" />
        </div>
        <div class="modal-actions">
          <button class="btn-plain" @click="quickSup = false">取消</button>
          <button @click="createSup">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stockApi, purchaseApi, supplierApi, categoryApi, unitApi, weightUnitApi } from '../api'
import ImageUploader from '../components/ImageUploader.vue'

const route = useRoute()
const router = useRouter()
const isEdit = route.params.id !== undefined && route.params.id !== 'new'
const orderId = isEdit ? Number(route.params.id) : null

const suppliers = ref([])
const cats = ref([])
const units = ref([])
const weightUnits = ref([])

const form = ref({ supplier_id: null, purchase_method: '', order_date: '', remark: '' })
const items = ref([])
const order = ref({ status: '', operator: '', confirmed_at: '', order_no: '' })

const scanInput = ref(null)
const scanText = ref('')
const scanMsg = ref('')
const scanMsgType = ref('ok')
const confirming = ref(false)

const showAskNew = ref(false)
const showForm = ref(false)
const editingItem = ref(null)
const formData = ref({ images: [] })

const quickSup = ref(false)
const supForm = ref({ name: '', contact: '', phone: '' })

let keySeq = 0
function newKey() { return 'k' + (++keySeq) + '_' + Date.now() }

function statusName(s) {
  return { draft: '草稿', done: '已入库', cancelled: '已取消' }[s] || s
}

const totalQty = computed(() => items.value.reduce((s, it) => s + (it.quantity || 0), 0))
const totalAmount = computed(() => items.value.reduce((s, it) => s + (it.quantity || 0) * (it.unit_price || 0), 0).toFixed(2))

function defaultFormData() {
  return {
    images: [], name: '', code: '', spec: '', barcode: '', category_name: '',
    unit: '件', weight: 0, weight_unit: '千克',
    quantity: 1, unit_price: 0, remark: ''
  }
}

async function loadDicts() {
  const [sup, cat, u, w] = await Promise.all([
    supplierApi.list(), categoryApi.list(), unitApi.list(), weightUnitApi.list()
  ])
  suppliers.value = sup
  cats.value = cat
  units.value = u.map(x => x.name)
  weightUnits.value = w.map(x => x.name)
}

async function load() {
  await loadDicts()
  if (!isEdit) return
  const o = await purchaseApi.get(orderId)
  order.value = o
  form.value = {
    supplier_id: o.supplier_id,
    purchase_method: o.purchase_method,
    order_date: o.order_date,
    remark: o.remark
  }
  items.value = (o.items || []).map(it => ({
    _key: newKey(), id: it.id, spu_id: it.spu_id, sku_id: it.sku_id,
    status: it.status, quantity: it.quantity, unit_price: it.unit_price,
    sku_name: it.sku_name, barcode: it.barcode, cur_stock: it.cur_stock,
    draft_name: it.draft_name, draft_code: it.draft_code, draft_spec: it.draft_spec,
    draft_barcode: it.draft_barcode, draft_category: it.draft_category,
    draft_unit: it.draft_unit, draft_weight: it.draft_weight,
    draft_weight_unit: it.draft_weight_unit, draft_remark: it.draft_remark,
    draft_images: it.draft_images || []
  }))
}

async function doScan() {
  const text = scanText.value.trim()
  if (!text) return
  scanMsg.value = ''
  try {
    const r = await stockApi.scan({ code: text })
    addHit(r)
    scanText.value = ''
    scanMsg.value = `已加入：${r.sku_name || r.spu_name}`
    scanMsgType.value = 'ok'
  } catch (e) {
    if (e.response?.status === 404) {
      showAskNew.value = true
    } else {
      scanMsg.value = e.response?.data?.detail || '查询失败'
      scanMsgType.value = 'err'
    }
  }
}

function addHit(r) {
  items.value.push({
    _key: newKey(), id: null, spu_id: r.spu_id, sku_id: r.sku_id,
    status: 'existing', quantity: 1, unit_price: r.cost_price || 0,
    sku_name: r.sku_name || r.spu_name, barcode: r.barcode || '', cur_stock: r.stock,
    draft_name: '', draft_code: '', draft_spec: '', draft_barcode: '',
    draft_category: '', draft_unit: '件', draft_weight: 0,
    draft_weight_unit: '千克', draft_remark: '', draft_images: []
  })
}

function removeItem(i) {
  if (!confirm('确定移除该项吗？')) return
  items.value.splice(i, 1)
}

function openForm(it) {
  editingItem.value = it
  formData.value = {
    images: (it.draft_images || []).map((url, i) => ({ id: null, url, img_type: 'main', sort: i })),
    name: it.draft_name, code: it.draft_code, spec: it.draft_spec,
    barcode: it.draft_barcode || it.barcode, category_name: it.draft_category,
    unit: it.draft_unit || '件', weight: it.draft_weight, weight_unit: it.draft_weight_unit || '千克',
    quantity: it.quantity, unit_price: it.unit_price, remark: it.draft_remark
  }
  showForm.value = true
}

function openFormForNew() {
  editingItem.value = null
  formData.value = defaultFormData()
  formData.value.barcode = scanText.value.trim()
  formData.value.quantity = 1
  showForm.value = true
  showAskNew.value = false
  nextTick(() => {
    const nameInput = document.querySelector('#pf-name')
    if (nameInput) nameInput.focus()
  })
}

function saveFormItem() {
  const d = formData.value
  if (!d.name.trim()) { alert('请填写货品名称'); return }
  if (!d.quantity || d.quantity <= 0) { alert('数量必须大于0'); return }
  if (editingItem.value) {
    const it = editingItem.value
    it.draft_name = d.name.trim()
    it.draft_code = d.code.trim()
    it.draft_spec = d.spec.trim()
    it.draft_barcode = d.barcode.trim()
    it.draft_category = d.category_name
    it.draft_unit = d.unit
    it.draft_weight = d.weight
    it.draft_weight_unit = d.weight_unit
    it.draft_remark = d.remark
    it.draft_images = d.images.map(x => x.url)
    it.quantity = d.quantity
    it.unit_price = d.unit_price
  } else {
    items.value.push({
      _key: newKey(), id: null, spu_id: null, sku_id: null,
      status: 'draft', quantity: d.quantity, unit_price: d.unit_price,
      sku_name: '', barcode: '', cur_stock: null,
      draft_name: d.name.trim(), draft_code: d.code.trim(), draft_spec: d.spec.trim(),
      draft_barcode: d.barcode.trim(), draft_category: d.category_name,
      draft_unit: d.unit, draft_weight: d.weight, draft_weight_unit: d.weight_unit,
      draft_remark: d.remark, draft_images: d.images.map(x => x.url)
    })
  }
  showForm.value = false
  scanText.value = ''
  nextTick(() => scanInput.value?.focus())
}

function buildBody() {
  return {
    supplier_id: form.value.supplier_id,
    purchase_method: form.value.purchase_method,
    order_date: form.value.order_date,
    remark: form.value.remark,
    items: items.value.map(it => ({
      id: it.id, spu_id: it.spu_id, sku_id: it.sku_id, status: it.status,
      quantity: it.quantity, unit_price: it.unit_price,
      draft_name: it.draft_name, draft_code: it.draft_code, draft_spec: it.draft_spec,
      draft_barcode: it.draft_barcode, draft_category: it.draft_category,
      draft_unit: it.draft_unit, draft_weight: it.draft_weight,
      draft_weight_unit: it.draft_weight_unit, draft_remark: it.draft_remark,
      draft_images: it.draft_images
    }))
  }
}

async function saveDraft() {
  if (!form.value.supplier_id) { alert('请先选择供应商'); return }
  if (!items.value.length) { alert('还没有明细，先扫一件货吧'); return }
  try {
    if (isEdit) {
      await purchaseApi.update(orderId, buildBody())
    } else {
      const o = await purchaseApi.create(buildBody())
      router.replace(`/purchase/${o.id}`)
    }
    alert('草稿已保存，可继续扫码加货')
    if (isEdit) load()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function confirmIn() {
  if (!form.value.supplier_id) { alert('请先选择供应商'); return }
  if (!items.value.length) { alert('还没有明细，先扫一件货吧'); return }
  if (!isEdit) {
    // 未保存过 → 先建单再入库
    try {
      const o = await purchaseApi.create(buildBody())
      router.replace(`/purchase/${o.id}`)
      orderIdForConfirm.value = o.id
      return doConfirm(o.id)
    } catch (e) {
      alert(e.response?.data?.detail || '创建采购单失败')
      return
    }
  }
  doConfirm(orderId)
}

const orderIdForConfirm = ref(null)

async function doConfirm(id) {
  confirming.value = true
  try {
    const r = await purchaseApi.confirm(id)
    alert(`入库成功！单号 ${r.order_no}，共 ${r.items} 项货品已建档并入库。`)
    await load()
    router.push('/purchase')
  } catch (e) {
    alert(e.response?.data?.detail || '入库失败，已回滚')
  } finally {
    confirming.value = false
  }
}

async function createSup() {
  const name = supForm.value.name.trim()
  if (!name) { alert('请填写供应商名称'); return }
  try {
    const s = await supplierApi.create({ name, contact: supForm.value.contact, phone: supForm.value.phone })
    suppliers.value.push(s)
    form.value.supplier_id = s.id
    quickSup.value = false
    supForm.value = { name: '', contact: '', phone: '' }
  } catch (e) {
    alert(e.response?.data?.detail || '新增失败')
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
.fitem input, .fitem select, .fitem textarea {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.fitem select { min-width: 0; }
.fitem select option, select option { background: #161b38; color: var(--text); }
.fitem textarea { height: auto; padding: 10px 12px; resize: vertical; font-family: inherit; }
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
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; border: 1px solid; }
.tag-draft { color: #e2b45c; border-color: rgba(226,180,92,.5); background: rgba(226,180,92,.12); }
.tag-done { color: #5bd6a8; border-color: rgba(91,214,168,.5); background: rgba(91,214,168,.12); }
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
  background: linear-gradient(135deg, #37b38a, #2a9d78); color: #fff;
}
.foot-actions .btn-confirm:disabled { opacity: .55; cursor: wait; }
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; z-index: 50;
}
.modal {
  width: 560px; max-width: 92vw; max-height: 84vh; overflow: auto;
  background: var(--panel-strong); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px; box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 4px; letter-spacing: 1px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.modal-actions button {
  height: 38px; padding: 0 22px; border: none; border-radius: 9px;
  color: #fff; font-size: 14px; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.modal-actions .btn-plain { background: transparent; border: 1px solid var(--border); color: var(--text-2); }
.form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px;
}
.form-grid .fitem input, .form-grid .fitem select, .form-grid .fitem textarea {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.form-grid .fitem textarea { height: auto; padding: 10px 12px; resize: vertical; font-family: inherit; }
.form-grid .fitem input:focus, .form-grid .fitem select:focus, .form-grid .fitem textarea:focus {
  border-color: var(--primary); box-shadow: 0 0 0 3px rgba(91,124,250,.18);
}
</style>
