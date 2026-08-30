import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

export const categoryApi = {
  list: () => api.get('/categories'),
  create: (data) => api.post('/categories', data),
  remove: (id) => api.delete(`/categories/${id}`)
}

export const uploadApi = {
  image: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/upload/image', fd)
  }
}

export const unitApi = {
  list: () => api.get('/units'),
  create: (data) => api.post('/units', data),
  update: (id, data) => api.put(`/units/${id}`, data),
  remove: (id) => api.delete(`/units/${id}`)
}

export const weightUnitApi = {
  list: () => api.get('/weight-units'),
  create: (data) => api.post('/weight-units', data),
  update: (id, data) => api.put(`/weight-units/${id}`, data),
  remove: (id) => api.delete(`/weight-units/${id}`)
}

export const productApi = {
  list: (params) => api.get('/spus', { params }),
  get: (id) => api.get(`/spus/${id}`),
  create: (data) => api.post('/spus', data),
  update: (id, data) => api.put(`/spus/${id}`, data),
  remove: (id) => api.delete(`/spus/${id}`),
  importExcel: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/import/excel', fd)
  }
}

// v1.3：回收站 + 批量删除 + 智能筛选
export const recycleApi = {
  analyze: (days) => api.get('/recycle/analyze', { params: { days } }),
  batchDelete: (spuIds) => api.post('/recycle/batch-delete', { spu_ids: spuIds }),
  list: () => api.get('/recycle/list'),
  restore: (spuIds) => api.post('/recycle/restore', { spu_ids: spuIds }),
  purge: (spuIds) => api.post('/recycle/purge', { spu_ids: spuIds })
}

export const channelApi = {
  list: () => api.get('/channels'),
  create: (data) => api.post('/channels', data),
  update: (id, data) => api.put(`/channels/${id}`, data),
  remove: (id) => api.delete(`/channels/${id}`)
}

export const stockApi = {
  scan: (params) => api.get('/stock/scan', { params }),
  stockIn: (data) => api.post('/stock/in', data),
  stockOut: (data) => api.post('/stock/out', data),
  logs: (params) => api.get('/stock/logs', { params }),
  channelStats: () => api.get('/stock/channel-stats'),
  summary: () => api.get('/stock/summary')
}

export const supplierApi = {
  list: () => api.get('/suppliers'),
  create: (data) => api.post('/suppliers', data),
  update: (id, data) => api.put(`/suppliers/${id}`, data),
  remove: (id) => api.delete(`/suppliers/${id}`)
}

export const purchaseApi = {
  list: (params) => api.get('/purchases', { params }),
  get: (id) => api.get(`/purchases/${id}`),
  create: (data) => api.post('/purchases', data),
  update: (id, data) => api.put(`/purchases/${id}`, data),
  confirm: (id) => api.post(`/purchases/${id}/confirm`),
  remove: (id) => api.delete(`/purchases/${id}`)
}

export const saleApi = {
  list: (params) => api.get('/sales', { params }),
  get: (id) => api.get(`/sales/${id}`),
  create: (data) => api.post('/sales', data),
  update: (id, data) => api.put(`/sales/${id}`, data),
  confirm: (id) => api.post(`/sales/${id}/confirm`),
  remove: (id) => api.delete(`/sales/${id}`)
}

export const financeApi = {
  summary: (params) => api.get('/finance/summary', { params }),
  byChannel: (params) => api.get('/finance/by-channel', { params }),
  orders: (params) => api.get('/finance/orders', { params }),
  orderDetail: (id) => api.get(`/finance/orders/${id}`)
}

export const analysisApi = {
  summary: () => api.get('/analysis/summary'),
  categoryStock: () => api.get('/analysis/category-stock'),
  stockRank: (params) => api.get('/analysis/stock-rank', { params }),
  sellingTop: (params) => api.get('/analysis/selling-top', { params }),
  slowMoving: (params) => api.get('/analysis/slow-moving', { params }),
  lowStock: (params) => api.get('/analysis/low-stock', { params }),
  trend: (params) => api.get('/analysis/trend', { params })
}

export const senderApi = {
  list: () => api.get('/senders'),
  create: (data) => api.post('/senders', data),
  update: (id, data) => api.put(`/senders/${id}`, data),
  remove: (id) => api.delete(`/senders/${id}`)
}

export const labelTemplateApi = {
  list: (type) => api.get('/label-templates', { params: { type } }),
  getDefault: (type) => api.get('/label-templates/default', { params: { type } }),
  create: (data) => api.post('/label-templates', data),
  update: (id, data) => api.put(`/label-templates/${id}`, data),
  remove: (id) => api.delete(`/label-templates/${id}`)
}

export const settingsApi = {
  preference: () => api.get('/settings/preference'),
  savePreference: (data) => api.put('/settings/preference', data),
  uploadBg: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/settings/preference/bg-image', fd)
  },
  removeBg: () => api.delete('/settings/preference/bg-image'),
  storage: () => api.get('/settings/storage'),
  migrate: (newDir) => api.post('/settings/storage/migrate', { new_dir: newDir }),
  cloudBackup: () => api.get('/settings/cloud-backup')
}
