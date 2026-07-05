import { createRouter, createWebHistory } from 'vue-router'
import DailyView from './views/DailyView.vue'
import DashboardView from './views/DashboardView.vue'
import ReportView from './views/ReportView.vue'
import SettingsView from './views/SettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/daily' },
    { path: '/daily', name: 'daily', component: DailyView },
    { path: '/dashboard', name: 'dashboard', component: DashboardView },
    { path: '/report', name: 'report', component: ReportView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})
