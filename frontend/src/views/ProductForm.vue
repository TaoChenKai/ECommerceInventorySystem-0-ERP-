<template>
  <div>
    <h2>{{ isEdit ? '编辑商品' : '新建商品' }}</h2>
    <p class="desc">款式(SPU)信息 + 规格(SKU)列表，规格可自由增删；主图/详情图多张不限</p>

    <div class="panel" style="max-width: 960px">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px">
        <div class="fitem">
          <label>商品名称 *</label>
          <input v-model="form.name" placeholder="如：纯棉短袖T恤" />
        </div>
        <div class="fitem">
          <label>商品编号</label>
          <input v-model="form.code" placeholder="对得上工厂一维码，可留空" />
        </div>
        <div class="fitem">
          <label>分类</label>
          <input v-model="form.categoryText" list="cat-options" placeholder="未分类或输入新分类名称" />
          <datalist id="cat-options">
            <option v-for="c in cats" :key="c.id" :value="c.name" />
          </datalist>
        </div>
        <div class="fitem">
          <label>单位</label>
          <div class="unit-row">
            <input v-model="form.unit" list="unit-options" placeholder="件 / 个 / 键... 可直接输入新单位" />
            <datalist id="unit-options">
              <option v-for="u in units" :key="u" :value="u" />
            </datalist>
            <button class="mini-btn" title="管理单位（新增/改名/删除）" @click="openUnitMgr('unit')">管理</button>
          </div>
        </div>
        <div class="fitem">
          <label>重量</label>
          <input v-model.number="form.weight" type="number" step="0.01" min="0" placeholder="0" />
        </div>
        <div class="fitem">
          <label>重量单位</label>
          <div class="unit-row">
            <input v-model="form.weight_unit" list="wunit-options" placeholder="克 / 千克 / 吨 / 斤... 可直接输入新单位" />
            <datalist id="wunit-options">
              <option v-for="w in weightUnits" :key="w" :value="w" />
            </datalist>
            <button class="mini-btn" title="管理重量单位（新增/改名/删除）" @click="openUnitMgr('weight')">管理</button>
          </div>
        </div>
        <div class="fitem">
          <label>设计者</label>
          <input v-model="form.designer" placeholder="如：0号仓库工作室（用于标签打印）" />
        </div>
        <div class="fitem">
          <label>生产日期</label>
          <input v-model="form.production_date" type="date" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>材质</label>
          <input v-model="form.material" placeholder="如：纯棉 / 聚酯纤维（用于标签打印）" />
        </div>
        <div class="fitem" style="grid-column: 1 / -1">
          <label>备注</label>
          <textarea v-model="form.remark" rows="2" placeholder="产地 / 说明等"></textarea>
        </div>
      </div>

      <div style="margin: 20px 0 0">
        <div style="margin-bottom: 14px">
          <ImageUploader v-model="form.images_main" title="美工图（主图）"
            hint="多张不限，上传后可拖动排序，第一张作为列表缩略图" type="main" />
        </div>
        <div style="margin-bottom: 20px">
          <ImageUploader v-model="form.images_detail" title="商品详情介绍图"
            hint="类电商详情页大图，想传几张传几张，无限制" type="detail" />
        </div>
      </div>

      <div style="display: flex; align-items: center; margin: 8px 0 10px">
        <b style="letter-spacing: 1px">规格列表（SKU）</b>
        <span style="flex: 1"></span>
        <button style="background: linear-gradient(135deg,#37b38a,#2a9d78); height: 34px" @click="addSku">+ 添加规格</button>
      </div>

      <table>
        <thead>
          <tr>
            <th style="width: 170px">规格名 *</th>
            <th>SKU编码</th>
            <th>条码</th>
            <th style="width: 100px">进价</th>
            <th style="width: 100px">售价</th>
            <th style="width: 100px">初始库存</th>
            <th style="width: 60px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(s, i) in form.skus" :key="i">
            <td><input v-model="s.spec_name" placeholder="红色 / XL" /></td>
            <td><input v-model="s.sku_code" placeholder="可留空" /></td>
            <td><input v-model="s.barcode" placeholder="可留空" /></td>
            <td><input v-model.number="s.cost_price" type="number" step="0.01" min="0" /></td>
            <td><input v-model.number="s.sale_price" type="number" step="0.01" min="0" /></td>
            <td><input v-model.number="s.stock" type="number" min="0" /></td>
            <td style="text-align: center"><button @click="form.skus.splice(i, 1)">删</button></td>
          </tr>
          <tr v-if="!form.skus.length">
            <td colspan="7" class="empty">还没有规格，点击右上角「+ 添加规格」</td>
          </tr>
        </tbody>
      </table>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px">
        <button style="background: transparent; border: 1px solid var(--border); color: var(--text-2)" @click="router.back()">取消</button>
        <button @click="save" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
      </div>
    </div>

    <!-- 单位管理弹窗 -->
    <div v-if="showUnitMgr" class="modal-mask" @click.self="closeUnitMgr">
      <div class="modal">
        <h3>{{ unitMgrKind === 'unit' ? '单位管理' : '重量单位管理' }}</h3>
        <p class="muted" style="margin: 8px 0 14px; font-size: 13px">
          {{ unitMgrKind === 'unit' ? '卖啥单位用啥：件 / 个 / 键 / 套... 想改成啥就改成啥，没有就自己加' : '克 / 千克 / 吨 / 斤 / 磅... 可自由增删改' }}
        </p>
        <div style="display: flex; gap: 8px; margin-bottom: 14px">
          <input v-model="newUnitName" placeholder="输入新单位名称，如：键" style="flex: 1" @keyup.enter="addUnit" />
          <button @click="addUnit">新增</button>
        </div>
        <table>
          <thead>
            <tr><th>名称</th><th style="width: 200px">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="u in unitList" :key="u.id">
              <td>
                <input v-model="u.editName" style="width: 130px" @keyup.enter="saveUnit(u)" />
              </td>
              <td>
                <button class="mini-btn" @click="saveUnit(u)">保存</button>
                <button class="mini-btn danger" @click="delUnit(u)">删除</button>
              </td>
            </tr>
            <tr v-if="!unitList.length"><td colspan="2" class="empty">暂无单位，先添加一个</td></tr>
          </tbody>
        </table>
        <div class="modal-actions">
          <button class="btn-plain" @click="closeUnitMgr">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productApi, categoryApi, unitApi, weightUnitApi } from '../api'
import ImageUploader from '../components/ImageUploader.vue'

const route = useRoute()
const router = useRouter()
const isEdit = route.params.id !== undefined && route.params.id !== 'new'
const saving = ref(false)
const cats = ref([])

const units = ref([])         // 计数单位字典
const weightUnits = ref([])   // 重量单位字典

const form = ref({
  name: '',
  code: '',
  categoryText: '',      // 分类输入框文本：空=未分类；填已有分类名/新分类名均可
  category_id: null,
  unit: '件',
  weight: 0,
  weight_unit: '千克',
  designer: '',
  production_date: '',   // YYYY-MM-DD，空则不填
  material: '',
  remark: '',
  images_main: [],
  images_detail: [],
  skus: []
})

function addSku() {
  form.value.skus.push({ id: null, spec_name: '', sku_code: '', barcode: '', cost_price: 0, sale_price: 0, stock: 0 })
}

async function loadUnits() {
  const [u, w] = await Promise.all([unitApi.list(), weightUnitApi.list()])
  units.value = u.map(x => x.name)
  weightUnits.value = w.map(x => x.name)
}

async function load() {
  cats.value = await categoryApi.list()
  await loadUnits()
  if (isEdit) {
    const p = await productApi.get(route.params.id)
    form.value = {
      name: p.name,
      code: p.code,
      categoryText: p.category_name || '',
      category_id: p.category_id,
      unit: p.unit,
      weight: p.weight,
      weight_unit: p.weight_unit || '千克',
      designer: p.designer || '',
      production_date: p.production_date || '',
      material: p.material || '',
      remark: p.remark,
      images_main: (p.images || []).filter(i => i.img_type === 'main').map(i => ({ id: i.id, url: i.url, img_type: 'main' })),
      images_detail: (p.images || []).filter(i => i.img_type === 'detail').map(i => ({ id: i.id, url: i.url, img_type: 'detail' })),
      skus: p.skus.map(s => ({
        id: s.id, spec_name: s.spec_name, sku_code: s.sku_code,
        barcode: s.barcode, cost_price: s.cost_price, sale_price: s.sale_price, stock: s.stock
      }))
    }
    // 旧数据 image_url 兼容：主图为空时补一张
    if (!form.value.images_main.length && p.image_url) {
      form.value.images_main.push({ id: null, url: p.image_url, img_type: 'main' })
    }
    if (!units.value.includes(form.value.unit)) units.value.push(form.value.unit)
    if (!weightUnits.value.includes(form.value.weight_unit)) weightUnits.value.push(form.value.weight_unit)
  } else {
    addSku()
  }
}

async function save() {
  if (!form.value.name.trim()) { alert('请填写商品名称'); return }
  const images = [
    ...form.value.images_main.map((im, i) => ({ id: im.id, url: im.url, img_type: 'main', sort: i })),
    ...form.value.images_detail.map((im, i) => ({ id: im.id, url: im.url, img_type: 'detail', sort: i }))
  ]
  // 分类：输入文本匹配到已有分类 → 传 id；否则作为新分类名传给后端自动建档
  const catName = (form.value.categoryText || '').trim()
  const matchedCat = cats.value.find(c => c.name === catName)
  const body = {
    name: form.value.name,
    code: form.value.code,
    category_id: matchedCat ? matchedCat.id : null,
    category_name: matchedCat ? '' : catName,
    unit: (form.value.unit || '').trim() || '件',
    weight: form.value.weight,
    weight_unit: (form.value.weight_unit || '').trim() || '千克',
    designer: (form.value.designer || '').trim(),
    production_date: form.value.production_date ? form.value.production_date : null,
    material: (form.value.material || '').trim(),
    remark: form.value.remark,
    image_url: '',
    images,
    skus: form.value.skus.map(s => ({ ...s }))
  }
  saving.value = true
  try {
    if (isEdit) {
      await productApi.update(route.params.id, body)
    } else {
      await productApi.create(body)
    }
    await loadUnits()   // 新输入的单位/重量单位已自动补录字典，刷新候选列表
    router.push('/products')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ============ 单位管理弹窗 ============
const showUnitMgr = ref(false)
const unitMgrKind = ref('unit')
const newUnitName = ref('')
const unitList = ref([])

function openUnitMgr(kind) {
  unitMgrKind.value = kind
  newUnitName.value = ''
  unitList.value = (kind === 'unit'
    ? units.value.map(n => ({ id: null, name: n, editName: n }))
    : weightUnits.value.map(n => ({ id: null, name: n, editName: n })))
  showUnitMgr.value = true
}

function closeUnitMgr() {
  showUnitMgr.value = false
  // 重新拉取最新字典
  loadUnits()
}

async function addUnit() {
  const name = newUnitName.value.trim()
  if (!name) return
  const api = unitMgrKind.value === 'unit' ? unitApi : weightUnitApi
  try {
    await api.create({ name })
    newUnitName.value = ''
    await refreshUnitList()
  } catch (e) {
    alert(e.response?.data?.detail || '新增失败')
  }
}

async function saveUnit(u) {
  const name = u.editName.trim()
  if (!name) { alert('名称不能为空'); return }
  const api = unitMgrKind.value === 'unit' ? unitApi : weightUnitApi
  try {
    if (u.id) {
      await api.update(u.id, { name })
    } else {
      // 新建商品页本地新增的单位还没有 id，需先建后改
      const created = await api.create({ name: u.name })
      await api.update(created.id, { name })
    }
    await refreshUnitList()
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function delUnit(u) {
  if (!confirm(`确定删除单位「${u.name}」吗？正在被商品使用的不能删`)) return
  const api = unitMgrKind.value === 'unit' ? unitApi : weightUnitApi
  try {
    if (u.id) await api.remove(u.id)
    await refreshUnitList()
  } catch (e) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

async function refreshUnitList() {
  if (unitMgrKind.value === 'unit') {
    unitList.value = (await unitApi.list()).map(x => ({ id: x.id, name: x.name, editName: x.name }))
  } else {
    unitList.value = (await weightUnitApi.list()).map(x => ({ id: x.id, name: x.name, editName: x.name }))
  }
}

onMounted(load)
</script>

<style scoped>
.fitem { display: flex; flex-direction: column; gap: 6px; }
.fitem label { font-size: 13px; color: var(--text-2); }
.fitem input, .fitem select, .fitem textarea {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.fitem input:focus, .fitem select:focus, .fitem textarea:focus {
  border-color: var(--primary); box-shadow: 0 0 0 3px rgba(91,124,250,.18);
}
.fitem textarea { height: auto; padding: 10px 12px; resize: vertical; font-family: inherit; }
.fitem select option { background: #161b38; color: var(--text); }
.unit-row { display: flex; gap: 6px; align-items: center; }
.unit-row select { flex: 1; }
.mini-btn {
  height: 34px; padding: 0 12px; border-radius: 8px;
  border: 1px solid rgba(91,124,250,.5); background: transparent;
  color: var(--primary); font-size: 13px; cursor: pointer;
}
.mini-btn.danger { border-color: rgba(255,92,92,.5); color: #ff7b7b; }
table input {
  width: 100%; height: 34px; padding: 0 10px; border-radius: 7px;
  border: 1px solid var(--border); background: rgba(255,255,255,.05);
  color: var(--text); font-size: 13px; outline: none;
}
table input:focus { border-color: var(--primary); }
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(5, 7, 18, 0.72); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center; z-index: 50;
}
.modal {
  width: 520px; max-width: 92vw; max-height: 80vh; overflow: auto;
  background: var(--panel-strong); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px; box-shadow: 0 24px 70px rgba(0,0,0,.6);
}
.modal h3 { margin-bottom: 4px; letter-spacing: 1px; }
.modal input[type=text] {
  height: 38px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--border); background: rgba(255,255,255,.06);
  color: var(--text); font-size: 14px; outline: none;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.modal-actions button {
  height: 38px; padding: 0 22px; border: none; border-radius: 9px;
  color: #fff; font-size: 14px; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
}
.modal-actions .btn-plain { background: transparent; border: 1px solid var(--border); color: var(--text-2); }
</style>
