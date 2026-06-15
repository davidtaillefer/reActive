<template>
  <!-- Force values to strings to fix the Prop Type warning -->
  <MetricCard title="Acute Training Load" :value1="currentATL.toString()" unit1="Current ATL"
    :value2="peakATL.toString()" unit2="Peak ATL" icon="i-bi-graph-up-arrow" icon-color="text-primary">
    <!-- Use a key to force chart refresh when data arrives -->
    <Line v-if="chartData.datasets[0].data.length > 0" :data="chartData" :options="chartOptions"
      :key="chartData.datasets[0].data.length" />
  </MetricCard>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import MetricCard from './MetricCard.vue'

// REGISTER ChartJS modules
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps({
  activities: { type: Array, required: false, default: () => [] },
  month: { type: Date, required: true }
})

const performanceHistory = ref<any[]>([])
const isLoadingHistory = ref(false)

const toLocalDateString = (date: Date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const fetchPerformanceHistory = async () => {
  isLoadingHistory.value = true
  try {
    const startDate = new Date(props.month.getFullYear(), props.month.getMonth(), 1)
    // Request a full-year warm-up so CTL has long-term context
    startDate.setDate(startDate.getDate() - 365)
    const endDate = new Date(props.month.getFullYear(), props.month.getMonth() + 1, 0)

    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}performance?history=true&start=${toLocalDateString(startDate)}&end=${toLocalDateString(endDate)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    performanceHistory.value = data.history || []
  } catch (err) {
    console.error('TrainingLoadCard: failed to load performance history', err)
    performanceHistory.value = []
  } finally {
    isLoadingHistory.value = false
  }
}

onMounted(fetchPerformanceHistory)
watch(() => props.month, fetchPerformanceHistory)

const daysInMonth = computed(() => {
  const year = props.month.getFullYear()
  const month = props.month.getMonth()
  const days = []
  const date = new Date(year, month, 1)
  while (date.getMonth() === month) {
    days.push(date.toISOString().split('T')[0])
    date.setDate(date.getDate() + 1)
  }
  return days
})

const historyMap = computed(() => {
  const map: Record<string, { load: number; atl: number; ctl: number }> = {}

  performanceHistory.value.forEach((entry: any) => {
    const dateValue = entry.date || entry.day || entry.activity_date
    if (!dateValue) return

    const d = dateValue.toString().split('T')[0]
    map[d] = {
      load: Number(entry.load || 0),
      atl: Number(entry.atl ?? entry.ATL ?? 0),
      ctl: Number(entry.ctl ?? entry.CTL ?? 0)
    }
  })

  return map
})

const atlData = computed(() => {
  if (performanceHistory.value.length > 0) {
    const history: Record<string, number> = {}
    daysInMonth.value.forEach(day => {
      history[day] = Number((historyMap.value[day]?.atl || 0).toFixed(1))
    })
    return history
  }

  const dailyLoads: Record<string, number> = {}

  props.activities.forEach((act: any) => {
    // Use the pre-normalized date from our new parent logic
    const d = act.normalizedDate
    dailyLoads[d] = (dailyLoads[d] || 0) + (parseFloat(act.training_load) || 0)
  })

  // Start 30 days before current month
  const startDate = new Date(props.month.getFullYear(), props.month.getMonth(), 1)
  startDate.setDate(startDate.getDate() - 30)

  let rollingATL = 0
  const history: Record<string, number> = {}

  // Calculate for 30 buffer days + days in current month
  const daysInView = new Date(props.month.getFullYear(), props.month.getMonth() + 1, 0).getDate()
  const totalDays = 30 + daysInView

  const tempDate = new Date(startDate)
  for (let i = 0; i < totalDays; i++) {
    const dStr = tempDate.toISOString().split('T')[0] // YYYY-MM-DD
    const load = dailyLoads[dStr] || 0

    rollingATL = (load * 1.025) + (0.836 * rollingATL)
    history[dStr] = Number(rollingATL.toFixed(1))

    tempDate.setDate(tempDate.getDate() + 1)
  }
  return history
})

const chartPoints = computed(() => daysInMonth.value.map(day => atlData.value[day] || 0))
const ctlPoints = computed(() => daysInMonth.value.map(day => historyMap.value[day]?.ctl || 0))
const currentATL = computed(() => {
  const now = new Date();
  const isCurrentMonth = props.month.getMonth() === now.getMonth() &&
    props.month.getFullYear() === now.getFullYear();

  if (isCurrentMonth) {
    const todayStr = now.toISOString().split('T')[0];
    // Return today's calculated value, or the last available if today isn't calculated yet
    return atlData.value[todayStr] || chartPoints.value[now.getDate() - 1] || 0;
  }

  // Default behaviour for previous months: return the final day's value
  return chartPoints.value[chartPoints.value.length - 1] || 0;
});
const peakATL = computed(() => Math.max(...chartPoints.value, 0))

const chartData = computed(() => ({
  labels: daysInMonth.value.map(d => d.split('-')[2]), // Show just the day DD
  datasets: [
    {
      label: 'ATL',
      data: chartPoints.value,
      borderColor: '#0d6efd',
      backgroundColor: 'rgba(13, 110, 253, 0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 0
    },
    {
      label: 'CTL',
      data: ctlPoints.value,
      borderColor: '#fd7e14',
      backgroundColor: 'rgba(253, 126, 20, 0.1)',
      fill: false,
      borderDash: [4, 4],
      tension: 0.3,
      pointRadius: 0
    }
  ]
}))

// DEFINE chartOptions so the template can see it
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  // Hide the legend to save space; CTL is still rendered as a dashed orange line
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true }
  }
}
</script>
