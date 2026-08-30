<template>
  <div>
    <h2>欢迎回来，{{ auth.user?.nickname || auth.user?.username }}！</h2>
    <p class="desc">0号仓库库存管理系统地基已就位（v1.3.1），商品档案、扫码出入库等功能将在后续版本上线。</p>
    <div class="panel">
      <div class="cards">
        <div class="card"><div class="num">-</div><div class="label">商品款式（SPU）</div></div>
        <div class="card"><div class="num">-</div><div class="label">规格（SKU）</div></div>
        <div class="card"><div class="num">-</div><div class="label">库存总量</div></div>
        <div class="card"><div class="num">-</div><div class="label">销售渠道</div></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>
