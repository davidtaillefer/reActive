import { createRouter, createWebHistory } from 'vue-router'

import CalendarView from '../views/CalendarView.vue'
import MapView from '../views/MapView.vue'
import ColumnsView from '../views/ColumnsView.vue'
import MainLayout from '../layouts/MainLayout.vue'
import SeasonView from '../views/SeasonView.vue'
import AnalysisView from '../views/ActivityView.vue'
import UploadView from '../views/UploadView.vue'        
import DashboardView from '../views/DashboardView.vue'
import PerformanceView from '../views/PerformanceView.vue' 
import EquipmentListView from '../views/EquipmentListView.vue'
import EquipmentDetailCard from '@/components/ui/EquipmentDetailCard.vue'
import EquipmentEditView from '../views/EquipmentEditView.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'Calendar', component: CalendarView },
      { path: 'map', name: 'Map', component: MapView },
      { path: 'dashboard', name: 'Dashboard', component: DashboardView },
      { path: 'season', name: 'Season', component: () => import('../views/SeasonView.vue') },
      { path: 'analysis', name: 'Analysis', component: () => import('../views/AnalysisView.vue') },
      { path: 'upload', name: 'Upload', component: () => import('../views/UploadView.vue') },
      { path: '/activity/:id', name: 'activity', component: () => import('../views/ActivityView.vue'), props: true,},
      { path: '/health/:id', name: 'health', component: () => import('../views/HealthRecordView.vue'), props: true },
      { path: 'health', name: 'Health', component: () => import('../views/HealthRecordView.vue') },
      { path: '/activity/:id/edit', name: 'activity-edit', component: () => import('@/views/ActivityEdit.vue'),},
      { path: 'settings', name: 'Settings', component: () => import('../views/SettingsView.vue') },
      { path: '/performance', name: 'Condition', component: PerformanceView},
      { path: '/equipment', name: 'Equipment', component: EquipmentListView},
      { path: '/equipment/new', name: 'EquipmentCreate', component: EquipmentEditView},
      { path: '/equipment/:id', name: 'EquipmentDetail', component: EquipmentDetailCard},
      { path: '/equipment/:id/edit', name: 'EquipmentEdit', component: EquipmentEditView}
    ]
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})