import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

import './assets/styles/main.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css'
import './chartjs-setup'

import {
  BContainer,
  BRow,
  BCol,
  BNavbar,
  BNavbarBrand,
  BNavbarToggle,
  BNavbarNav,
  BNavItem,
  BCollapse,
  BDropdown,
  BDropdownItem
} from 'bootstrap-vue-next'

// Ensure all fetch requests include cookies for authenticated backend routes.
const originalFetch = window.fetch.bind(window)
window.fetch = (input, init = {}) => {
  const finalInit = { credentials: 'include', ...init }
  return originalFetch(input, finalInit)
}

const app = createApp(App)

app.use(router)
app.use(createPinia())

// Manually register components
app.component('BContainer', BContainer)
app.component('BRow', BRow)
app.component('BCol', BCol)
app.component('BNavbar', BNavbar)
app.component('BNavbarBrand', BNavbarBrand)
app.component('BNavbarToggle', BNavbarToggle)
app.component('BNavbarNav', BNavbarNav)
app.component('BNavItem', BNavItem)
app.component('BCollapse', BCollapse)
app.component('BDropdown', BDropdown)
app.component('BDropdownItem', BDropdownItem)

app.mount('#app')
