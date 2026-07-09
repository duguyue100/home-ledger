import { createRouter, createWebHistory } from 'vue-router'
import DailyView from './views/DailyView.vue'
import ReportsView from './views/ReportsView.vue'
import SettingsView from './views/SettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/daily' },
    { path: '/daily', name: 'daily', component: DailyView },
    { path: '/reports', name: 'reports', component: ReportsView },
    { path: '/dashboard', redirect: '/reports' },
    { path: '/report', redirect: '/reports' },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})
