<template>
  <div>
    <h2>回收站</h2>
    <p class="desc">已删除的货品将在此保留 {{ RETENTION }} 天，到期自动清理；也可手动还原或彻底删除</p>

    <div class="toolbar">
      <button @click="load">刷新</button>
      <span style="flex: 1"></span>
      <template v-if="isBossOrAdmin">
        <button style="background: linear-gradient(135deg,#37b38a,#2a9d78)" :disabled="!selectedIds.length" @click="confirmRestore">还原所选（{{ selectedIds.length }}）</button>
        <button style="background: linear-gradient(135deg,#c0392b,#96281b)" :disabled="!selectedIds.length" @click="confirmPurge">彻底删除所选（{{ selectedIds.length }}）</button>
      </template>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th v-if="isBossOrAdmin" style="width: 44px">选</th>
            <th>编号</th>
            <th>名称</th>
            <th>分类</th>
            <th>规格数</th>
            <th>总库存</th>
            <th>删除时间</th>
            <th>剩余清理天数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td v-if="isBossOrAdmin"><input type="checkbox" :value="it.id" v-model="selectedIds" /></td>
            <td class="muted">{{ it.code || '—' }}</td>
            <td>{{ it.name }}</td>
            <td>{{ it.category_name || '—' }}</td>
            <td>{{ it.sku_count }}</td>
            <td style="color: var(--gold)">{{ it.total_stock }}</td>
            <td class="muted">{{ fmtTime(it.deleted_at) }}</td>
            <td>
              <span :style="{ color: it.remain_days <= 0 ? 'var(--danger)' : 'var(--gold)' }">
                {{ it.remain_days <= 0 ? '已过期，待自动清理' : `${it.remain_days} 天` }}
              </span>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td :colspan="isBossOrAdmin ? 8 : 7" class="empty">回收站是空的</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { recycleApi } from '../api'
import { useAuthStore } from '../stores/auth'

const RETENTION = 30
const auth = useAuthStore()
const isBossOrAdmin = computed(() => auth.isBoss || auth.isAdmin)

const items = ref([])
const selectedIds = ref([])

async function load() {
  const data = await recycleApi.list()
  items.value = data.items || []
  const valid = new Set(items.value.map((i) => i.id))
  selectedIds.value = selectedIds.value.filter((id) => valid.has(id))
}

async function confirmRestore() {
  if (!selectedIds.value.length) return
  if (!confirm(`确定还原所选 ${selectedIds.value.length} 条货品吗？还原后将恢复为正常商品。`)) return
  try {
    await recycleApi.restore(selectedIds.value)
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '还原失败')
  }
}

async function confirmPurge() {
  if (!selectedIds.value.length) return
  const names = items.value.filter((i) => selectedIds.value.includes(i.id)).map((i) => i.name).join('、')
  if (!confirm(`确定彻底删除所选 ${selectedIds.value.length} 条货品吗？此操作不可恢复，其历史出入库、采购、销售记录将一并清除。\n\n${names}`)) return
  try {
    await recycleApi.purge(selectedIds.value)
    load()
  } catch (e) {
    alert(e.response?.data?.detail || '彻底删除失败')
  }
}

function fmtTime(t) {
  if (!t) return '—'
  const d = new Date(t)
  if (isNaN(d.getTime())) return '—'
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(load)
</script>
