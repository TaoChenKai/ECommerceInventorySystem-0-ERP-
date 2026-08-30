<template>
  <div>
    <h2>出入库流水</h2>
    <p class="desc">每一次扫码出入库都留痕，可随时追溯</p>

    <div class="toolbar">
      <select v-model="typeFilter" @change="load" style="min-width: 120px">
        <option value="">全部类型</option>
        <option value="in">入库</option>
        <option value="out">出库</option>
      </select>
      <select v-model="channelFilter" @change="load" style="min-width: 150px">
        <option value="">全部渠道</option>
        <option value="__none">未选渠道</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <span style="flex: 1"></span>
      <button @click="load">刷新</button>
    </div>

    <div class="panel" style="overflow: auto">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>类型</th>
            <th>商品</th>
            <th>渠道</th>
            <th>数量</th>
            <th>操作人</th>
            <th>备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in logs" :key="l.id">
            <td class="muted">{{ fmtTime(l.created_at) }}</td>
            <td>
              <span :class="l.log_type === 'in' ? 'tag-in' : 'tag-out'">
                {{ l.log_type === 'in' ? '入库' : '出库' }}
              </span>
            </td>
            <td>{{ l.sku_name }}</td>
            <td>{{ l.channel_name || '未选渠道' }}</td>
            <td :style="l.log_type === 'in' ? 'color:#5bd6a8' : 'color:var(--gold)'">
              {{ l.log_type === 'in' ? '+' : '-' }}{{ l.quantity }}
            </td>
            <td>{{ l.operator }}</td>
            <td class="muted">{{ l.remark || '—' }}</td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="7" class="empty">暂无流水记录</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pager">
      <button :disabled="page <= 1" @click="page--; load()">上一页</button>
      <span class="muted">第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
      <button :disabled="page >= totalPages" @click="page++; load()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { stockApi, channelApi } from '../api'

const logs = ref([])
const channels = ref([])
const typeFilter = ref('')
const channelFilter = ref('')
const page = ref(1)
const total = ref(0)
const pageSize = 20

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function load() {
  const params = { page: page.value, page_size: pageSize }
  if (typeFilter.value) params.log_type = typeFilter.value
  if (channelFilter.value === '__none') params.channel_id = -1
  else if (channelFilter.value) params.channel_id = channelFilter.value
  const r = await stockApi.logs(params)
  total.value = r.total
  logs.value = r.items
}

function fmtTime(s) {
  if (!s) return '—'
  return s.replace('T', ' ').slice(0, 19)
}

onMounted(async () => {
  channels.value = await channelApi.list()
  load()
})
</script>

<style scoped>
.tag-in {
  background: rgba(55, 179, 138, .15); color: #5bd6a8;
  padding: 2px 10px; border-radius: 6px; font-size: 13px;
}
.tag-out {
  background: rgba(226, 180, 92, .15); color: var(--gold);
  padding: 2px 10px; border-radius: 6px; font-size: 13px;
}
.pager {
  display: flex; align-items: center; justify-content: flex-end; gap: 14px; margin-top: 12px;
}
.pager button:disabled { opacity: .4; cursor: not-allowed; }
</style>
