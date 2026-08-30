<template>
  <canvas ref="cv" class="star-field" aria-hidden="true"></canvas>
</template>

<script setup>
// 轻量粒子星云背景：低粒子数 + 低帧率，按当前主题强调色取色，随主题切换换色
import { ref, onMounted, onBeforeUnmount } from 'vue'

const cv = ref(null)
let ctx = null
let raf = 0
let W = 0
let H = 0
let dpr = 1
let particles = []
let nebulae = []
let observer = null
let running = false

function hexToRgb(hex, fallback) {
  const h = (hex || fallback).trim().replace('#', '')
  if (h.length !== 6 && h.length !== 3) return [91, 124, 250]
  const m = h.length === 3 ? h.split('').map((c) => c + c) : [h.slice(0, 2), h.slice(2, 4), h.slice(4, 6)]
  return m.map((x) => parseInt(x, 16))
}

function themeColors() {
  const cs = getComputedStyle(document.documentElement)
  return {
    primary: hexToRgb(cs.getPropertyValue('--primary'), '#5b7cfa'),
    gold: hexToRgb(cs.getPropertyValue('--gold'), '#e2b45c'),
    text: hexToRgb(cs.getPropertyValue('--text'), '#eef0ff')
  }
}

function init() {
  const canvas = cv.value
  if (!canvas) return
  dpr = Math.min(window.devicePixelRatio || 1, 1.5)
  W = window.innerWidth
  H = window.innerHeight
  canvas.width = W * dpr
  canvas.height = H * dpr
  canvas.style.width = W + 'px'
  canvas.style.height = H + 'px'
  ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const colors = themeColors()
  const count = Math.min(90, Math.floor((W * H) / 22000))
  particles = []
  for (let i = 0; i < count; i++) {
    const pick = Math.random()
    const c = pick < 0.55 ? colors.primary : pick < 0.85 ? colors.gold : colors.text
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.6 + 0.4,
      c,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      tw: Math.random() * Math.PI * 2,
      tws: 0.008 + Math.random() * 0.02
    })
  }
  nebulae = []
  for (let i = 0; i < 3; i++) {
    nebulae.push({
      x: Math.random() * W,
      y: Math.random() * H,
      r: 160 + Math.random() * 220,
      c: colors.primary
    })
  }
}

function draw() {
  if (!ctx) return
  ctx.clearRect(0, 0, W, H)
  // 星云柔光斑
  for (const n of nebulae) {
    const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r)
    g.addColorStop(0, `rgba(${n.c[0]},${n.c[1]},${n.c[2]},0.05)`)
    g.addColorStop(1, 'rgba(0,0,0,0)')
    ctx.fillStyle = g
    ctx.fillRect(n.x - n.r, n.y - n.r, n.r * 2, n.r * 2)
  }
  // 粒子
  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < -10) p.x = W + 10
    if (p.x > W + 10) p.x = -10
    if (p.y < -10) p.y = H + 10
    if (p.y > H + 10) p.y = -10
    p.tw += p.tws
    const alpha = 0.22 + Math.sin(p.tw) * 0.16
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${p.c[0]},${p.c[1]},${p.c[2]},${alpha.toFixed(3)})`
    ctx.fill()
  }
  raf = requestAnimationFrame(draw)
}

function onResize() {
  init()
}

onMounted(() => {
  init()
  running = true
  raf = requestAnimationFrame(draw)
  window.addEventListener('resize', onResize)
  // 主题切换时自动换色
  observer = new MutationObserver(() => init())
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})

onBeforeUnmount(() => {
  running = false
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.star-field {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
</style>
