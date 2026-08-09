<template>
  <BNavbar class="navbar-dark bg-dark" expand="lg">
    <BContainer fluid class="d-flex align-items-center">

      <!-- Brand -->
      <BNavbarBrand class="me-3" style="color: #8e44ad; font-weight: bold; font-size: 1.2rem;">
        reActive
      </BNavbarBrand>

      <!-- Nav items -->
      <BCollapse id="nav-collapse" is-nav>
        <BNavbarNav class="align-items-center">
          <BNavItem to="/dashboard" tag="router-link">Dashboard</BNavItem>
          <BNavItem :to="{ name: 'Calendar', query: route.query }" tag="router-link">
            Calendar
          </BNavItem>
          <BNavItem to="/performance" tag="router-link">Condition</BNavItem>
          <BNavItem to="/health" tag="router-link">Health</BNavItem>
          <BNavItem to="/map" tag="router-link">Map</BNavItem>
          <BNavItem to="/season" tag="router-link">Season</BNavItem>
          <BNavItem to="/analysis" tag="router-link">Analysis</BNavItem>
          <BNavItem to="/equipment" tag="router-link">Equipment</BNavItem>
          <BNavItem to="/upload" tag="router-link">Upload</BNavItem>
        </BNavbarNav>
      </BCollapse>

      <!-- Sync Button (Far Right) -->
      <div class="ms-auto d-flex align-items-center gap-2">
        <BDropdown variant="outline-light" size="sm" class="text-light" v-if="username">
          <template #button-content>
            <i class="bi bi-person-circle me-1"></i>
            <span>{{ username }}</span>
          </template>
          <BDropdownItem @click="goToPreferences">Preferences</BDropdownItem>
          <BDropdownItem @click="logout">Logout</BDropdownItem>
        </BDropdown>
        <!-- <BButton variant="outline-info" size="sm" @click="handleSync" :disabled="isSyncing"
          class="d-flex align-items-center gap-2">
          <BSpinner v-if="isSyncing" small />
          <i v-else class="bi bi-arrow-repeat"></i>
          {{ isSyncing ? 'Syncing...' : 'Sync' }}
        </BButton> -->

        <!-- Keep the toggler to the right of the button on mobile if desired -->
        <BNavbarToggle target="nav-collapse" class="ms-2" />
      </div>

    </BContainer>
  </BNavbar>
</template>


<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const isSyncing = ref(false)
const username = ref(null)

const handleSync = async () => {
  isSyncing.value = true
  try {
    const response = await fetch(`${apiBaseUrl}sync/days/7`, {
      method: 'GET',
      credentials: 'include'
    })

    if (!response.ok) throw new Error('Sync failed')

    const data = await response.json()
    // sync complete
  } catch (err) {
    console.error('Error during sync:', err)
    alert('Failed to synchronize data.')
  } finally {
    isSyncing.value = false
  }
}

async function loadCurrentUser() {
  try {
    const res = await fetch(`${apiBaseUrl}auth/me`, { credentials: 'include' })
    if (!res.ok) return
    const obj = await res.json()
    if (obj && obj.user && obj.user.username) {
      username.value = obj.user.username
    } else {
      username.value = null
    }
  } catch (e) {
    console.error('Failed to load current user', e)
    username.value = null
  }
}

async function logout() {
  try {
    await fetch(`${apiBaseUrl}auth/logout`, { method: 'POST', credentials: 'include' })
  } catch (e) {
    console.error('Logout request failed', e)
  } finally {
    username.value = null
    router.push({ name: 'Login' })
  }
}

function goToPreferences() {
  router.push({ name: 'Settings' })
}

onMounted(() => {
  loadCurrentUser()
})
</script>
