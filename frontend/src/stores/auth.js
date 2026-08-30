import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isBoss: (s) => s.user?.role === 'boss',
    isAdmin: (s) => s.user?.role === 'admin',
    roleName: (s) => ({ boss: '老板', admin: '管理员', staff: '员工' }[s.user?.role] || '')
  },
  actions: {
    async login(username, password) {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const data = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }
})
