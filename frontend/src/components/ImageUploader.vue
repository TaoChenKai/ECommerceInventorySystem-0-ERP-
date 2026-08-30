<template>
  <div class="img-uploader">
    <div class="iu-head">
      <b>{{ title }}</b>
      <span class="iu-hint">{{ hint }}</span>
      <span style="flex: 1"></span>
      <button class="iu-add" :disabled="uploading" @click="pick">
        {{ uploading ? '上传中...' : '+ 添加图片' }}
      </button>
      <input ref="fileInput" type="file" accept="image/*" multiple style="display: none" @change="onPick" />
    </div>

    <div v-if="imgs.length" class="iu-grid">
      <div v-for="(im, i) in imgs" :key="im.url + i" class="iu-cell">
        <img :src="im.url" alt="" />
        <div class="iu-mask">
          <button class="iu-btn" title="上移" :disabled="i === 0" @click="move(i, -1)">↑</button>
          <button class="iu-btn" title="下移" :disabled="i === imgs.length - 1" @click="move(i, 1)">↓</button>
          <button class="iu-btn iu-del" title="删除" @click="remove(i)">×</button>
        </div>
      </div>
    </div>
    <div v-else class="iu-empty">还没有图片，点击右上角「+ 添加图片」</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { uploadApi } from '../api'

const props = defineProps({
  title: { type: String, default: '商品图片' },
  hint: { type: String, default: '支持 png / jpg / webp 等，多张不限' },
  type: { type: String, default: 'main' }
})
const imgs = defineModel({ type: Array, default: () => [] })

const fileInput = ref(null)
const uploading = ref(false)

function pick() {
  fileInput.value?.click()
}

async function onPick(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploading.value = true
  try {
    for (const f of files) {
      try {
        const res = await uploadApi.image(f)
        imgs.value.push({ id: null, url: res.url, img_type: props.type })
      } catch (err) {
        alert((err.response?.data?.detail) || `「${f.name}」上传失败`)
      }
    }
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

function remove(i) {
  imgs.value.splice(i, 1)
}

function move(i, dir) {
  const j = i + dir
  if (j < 0 || j >= imgs.value.length) return
  const arr = imgs.value
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}
</script>

<style scoped>
.img-uploader {
  border: 1px dashed var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(255,255,255,.03);
}
.iu-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.iu-head b { font-size: 14px; letter-spacing: 1px; }
.iu-hint { font-size: 12px; color: var(--text-2); }
.iu-add {
  height: 30px; padding: 0 14px; border: none; border-radius: 7px;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff; font-size: 13px; cursor: pointer;
}
.iu-add:disabled { opacity: .5; cursor: wait; }
.iu-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px;
}
.iu-cell {
  position: relative; aspect-ratio: 1/1; border-radius: 9px; overflow: hidden;
  border: 1px solid var(--border); background: rgba(0,0,0,.25);
}
.iu-cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
.iu-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  gap: 6px; background: rgba(5,7,18,.55); opacity: 0; transition: opacity .15s;
}
.iu-cell:hover .iu-mask { opacity: 1; }
.iu-btn {
  width: 28px; height: 28px; border-radius: 6px; border: none;
  background: rgba(255,255,255,.85); color: #1a1f3d; font-size: 15px; cursor: pointer;
  line-height: 1;
}
.iu-btn:disabled { opacity: .35; cursor: not-allowed; }
.iu-del { background: #ff5c5c; color: #fff; }
.iu-empty {
  font-size: 13px; color: var(--text-2); padding: 14px 0; text-align: center;
}
</style>
