<template>
  <div>
    <h2>账号与权限</h2>
    <p class="desc">老板/管理员可添加员工或管理员账号（老板账号唯一且不可删）；删除账号仅老板可用。</p>
    <div class="panel">
      <div class="toolbar">
        <input v-model="form.username" placeholder="用户名" />
        <input v-model="form.password" placeholder="密码" />
        <input v-model="form.nickname" placeholder="昵称" />
        <select v-model="form.role">
          <option value="staff">员工</option>
          <option value="admin">管理员</option>
        </select>
        <button @click="createUser">添加账号</button>
      </div>
      <p v-if="msg" class="msg">{{ msg }}</p>
      <table>
        <thead>
          <tr><th>ID</th><th>用户名</th><th>昵称</th><th>角色</th><th>状态</th><th>创建时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.nickname }}</td>
            <td>{{ roleName(u.role) }}</td>
            <td>{{ u.is_active ? '启用' : '停用' }}</td>
            <td>{{ fmt(u.created_at) }}</td>
            <td>
              <button v-if="isBoss && u.role !== 'boss'" @click="deleteUser(u.id)">删除</button>
              <span v-else style="color:#8b93a7;font-size:12px">{{ u.role === 'boss' ? '超管' : '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const isBoss = computed(() => auth.isBoss)

const users = ref([])
const msg = ref('')
const form = ref({ username: '', password: '', nickname: '', role: 'staff' })

const roleName = (r) => ({ boss: '老板', admin: '管理员', staff: '员工' }[r] || r)
const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '')

async function load() {
  users.value = await api.get('/users')
}
async function createUser() {
  msg.value = ''
  if (!form.value.username || !form.value.password) {
    msg.value = '用户名和密码不能为空'
    return
  }
  try {
    await api.post('/users', form.value)
    msg.value = '添加成功'
    form.value = { username: '', password: '', nickname: '', role: 'staff' }
    load()
  } catch (e) {
    msg.value = e.response?.data?.detail || '添加失败'
  }
}
async function deleteUser(id) {
  if (!confirm('确定删除该账号？删除后不可恢复。')) return
  try {
    await api.delete(`/users/${id}`)
    load()
  } catch (e) {
    msg.value = e.response?.data?.detail || '删除失败'
  }
}
onMounted(load)
</script>
