import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    children: [
      { path: '', component: () => import('../views/Dashboard.vue'), meta: { title: '首页' } },
      { path: 'products', component: () => import('../views/Products.vue'), meta: { title: '商品档案' } },
      { path: 'recycle', component: () => import('../views/Recycle.vue'), meta: { title: '回收站', roles: ['boss', 'admin'] } },
      { path: 'products/new', component: () => import('../views/ProductForm.vue'), meta: { title: '新建商品' } },
      { path: 'products/:id', component: () => import('../views/ProductForm.vue'), meta: { title: '编辑商品' } },
      { path: 'stock', component: () => import('../views/StockInOut.vue'), meta: { title: '扫码出入库' } },
      { path: 'stock/logs', component: () => import('../views/StockLogs.vue'), meta: { title: '出入库流水' } },
      { path: 'purchase', component: () => import('../views/PurchaseOrders.vue'), meta: { title: '采购入库' } },
      { path: 'purchase/new', component: () => import('../views/PurchaseNew.vue'), meta: { title: '新建采购单' } },
      { path: 'purchase/:id', component: () => import('../views/PurchaseNew.vue'), meta: { title: '采购单详情' } },
      { path: 'sales', component: () => import('../views/SalesOrders.vue'), meta: { title: '销售出库' } },
      { path: 'sales/new', component: () => import('../views/SalesNew.vue'), meta: { title: '新建销售单' } },
      { path: 'sales/:id', component: () => import('../views/SalesNew.vue'), meta: { title: '销售单详情' } },
      { path: 'channels', component: () => import('../views/Channels.vue'), meta: { title: '渠道追踪' } },
      { path: 'finance', component: () => import('../views/Finance.vue'), meta: { title: '财务对账', roles: ['boss', 'admin'] } },
      { path: 'analysis', component: () => import('../views/Analysis.vue'), meta: { title: '库存分析' } },
      { path: 'label-print', component: () => import('../views/LabelPrint.vue'), meta: { title: '标签打印' } },
      { path: 'users', component: () => import('../views/UserManage.vue'), meta: { title: '账号权限', roles: ['boss', 'admin'] } },
      { path: 'audits', component: () => import('../views/AuditLog.vue'), meta: { title: '操作日志', roles: ['boss', 'admin'] } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) return '/login'
  if (to.path === '/login' && auth.isLoggedIn) return '/'
  if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) return '/'
  return true
})

export default router
