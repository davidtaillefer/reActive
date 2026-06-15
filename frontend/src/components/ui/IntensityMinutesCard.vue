<template>
  <BCard class="h-100 shadow-sm">
    <BCardBody>
      <div class="card-header-row">
        <div class="card-title">
          <IBiFire />
          Weekly Intensity Minutes
        </div>
      </div>
      <div class="card-top">
        <div class="donut-container">
          <Doughnut v-if="currentWeek.weighted > 0" :data="donutData" :options="donutOptions" />
          <div class="donut-center">
            <div class="current-value">{{ currentWeek.weighted }}</div>
          </div>
        </div>
      <div class="card-visual"></div>
      <div class="card-metrics">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <div class="current-big">{{ currentWeek.weighted }} / {{ GOAL_MINUTES }}</div>
            <div class="status-pill" :class="statusClass">{{ statusText }}</div>
          </div>
          <div class="d-flex align-items-center gap-2 flex-wrap mt-1">
            <div class="summary-text text-muted">
              {{ percent.toFixed(0) }}% of weekly goal
            </div>
            <div v-if="streak > 0" class="text-success small">
              🔥 {{ streak }} wk streak
            </div>
          </div>
        </div>
      </div>
    <div class="card-bottom">
        <Bar v-if="weeklyData.length" :data="intensityData" :options="barChartOptions" :plugins="[goalLinePlugin]" />
        <div v-else class="text-muted text-center p-4">
          No intensity data available
        </div>
      </div>

    </BCardBody>
  </BCard>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js'
import { useStats } from '@/composables/useStats'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

const { stats, loading, error, fetchStats } = useStats()

const GOAL_MINUTES = 150
const WEEKS = 26

onMounted(() => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - WEEKS * 7)

  fetchStats({ startDate: start, endDate: end })
})

// Prop to allow switching week start easily: 'monday' or 'sunday'
const props = withDefaults(defineProps<{ weekStart?: 'monday' | 'sunday' }>(), {
  weekStart: 'monday'
})

// 0 = Sunday, 1 = Monday
const WEEK_START_DAY = props.weekStart === 'monday' ? 0 : -1

// Return a key for the week based on the configured week start.
// Key is the ISO date (YYYY-MM-DD) of the week's start day.
const getWeekKey = (date: Date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)

  const day = d.getDay() // 0-6
  // how many days to subtract to reach the week start
  const diff = (day - WEEK_START_DAY + 7) % 7

  const weekStart = new Date(d)
  weekStart.setDate(d.getDate() - diff)
  weekStart.setHours(0, 0, 0, 0)

  // Shift week start forward by one day to align with data (see notes)
  weekStart.setDate(weekStart.getDate() + 1)

  // Build local YYYY-MM-DD string from local components to avoid
  // timezone/UTC parsing shifting the date by one day.
  const yyyy = weekStart.getFullYear()
  const mm = String(weekStart.getMonth() + 1).padStart(2, '0')
  const dd = String(weekStart.getDate()).padStart(2, '0')

  return `${yyyy}-${mm}-${dd}`
}

const weeklyData = computed(() => {
  if (!stats.value) return []

  const map: Record<string, any> = {}

  stats.value.forEach(r => {
    const d = new Date(r.date)
    const key = getWeekKey(d)

    // Determine the canonical week-start date for this key using local date constructor
    const [y, m, dStr] = key.split('-')
    const weekStartDate = new Date(Number(y), Number(m) - 1, Number(dStr))

    if (!map[key]) {
      map[key] = { moderate: 0, vigorous: 0, weighted: 0, date: weekStartDate }
    }

    const moderate = r.moderate_intensity || 0
    const vigorous = r.vigorous_intensity || 0

    map[key].moderate += moderate
    map[key].vigorous += vigorous
    map[key].weighted += moderate + (vigorous * 2)
  })

  return Object.values(map)
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .slice(-WEEKS)
})

const currentWeek = computed(() => {
  return weeklyData.value.at(-1) || { weighted: 0, moderate: 0, vigorous: 0 }
})

/**
 * % progress
 */
const percent = computed(() =>
  Math.min(100, (currentWeek.value.weighted / GOAL_MINUTES) * 100)
)

/**
 * Status
 */
const statusText = computed(() => {
  if (percent.value >= 100) return 'Goal Achieved'
  if (percent.value >= 75) return 'On Track'
  return 'Needs Improvement'
})

const statusClass = computed(() => {
  if (percent.value >= 100) return 'bg-success text-white'
  if (percent.value >= 75) return 'bg-warning text-dark'
  return 'bg-danger text-white'
})

/**
 * Streak calculation
 */
const streak = computed(() => {
  let count = 0

  for (let i = weeklyData.value.length - 1; i >= 0; i--) {
    if (weeklyData.value[i].weighted >= GOAL_MINUTES) count++
    else break
  }

  return count
})

/**
 * Doughnut
 */
const donutData = computed(() => ({
  datasets: [
    {
      data: [
        Math.min(currentWeek.value.weighted, GOAL_MINUTES),
        Math.max(0, GOAL_MINUTES - currentWeek.value.weighted)
      ],
      backgroundColor: [
        percent.value >= 100 ? '#198754' :
          percent.value >= 75 ? '#ffc107' :
            '#dc3545',
        '#e9ecef'
      ],
      borderWidth: 0,
      cutout: '70%',
      borderRadius: 6
    }
  ]
}))

const donutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  rotation: -90,
  circumference: 180,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  }
}

/**
 * Chart
 */
const intensityData = computed(() => {
  let lastMonth = ''

  const labels = weeklyData.value.map(w => {
    const month = new Intl.DateTimeFormat('en-CA', {
      month: 'short'
    }).format(w.date)

    if (month === lastMonth) return ''
    lastMonth = month
    return month
  })

  return {
    labels,
    datasets: [
      {
        label: 'Vigorous (×2)',
        data: weeklyData.value.map(w => w.vigorous * 2),
        backgroundColor: '#dc3545'
      },
      {
        label: 'Moderate',
        data: weeklyData.value.map(w => w.moderate),
        backgroundColor: '#ffc107'
      }
    ]
  }
})

const goalLinePlugin = {
  id: 'goalLine',
  afterDraw(chart: any) {
    const { ctx, chartArea, scales } = chart
    if (!chartArea) return

    const y = scales.y.getPixelForValue(GOAL_MINUTES)

    ctx.save()
    ctx.strokeStyle = '#198754'
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(chartArea.left, y)
    ctx.lineTo(chartArea.right, y)
    ctx.stroke()
    ctx.restore()
  }
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const
    }
  },
  scales: {
    x: {
      stacked: true,
      grid: { display: false },
      ticks: {
        maxRotation: 0,
        minRotation: 0,
        autoSkip: false
      }
    },
    y: {
      stacked: true,
      beginAtZero: true
    }
  }
}
</script>

<style scoped>

.donut-container {
  position: relative;
  width: 120px;
  height: 80px;
}

.donut-container canvas {
  width: 100% !important;
  height: 100% !important;
}

.donut-center {
  position: absolute;
  left: 50%;
  top: 65%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.current-value {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1;
}

.info-panel {
  flex: 1;
}

.current-big {
  font-size: 1.2rem;
  font-weight: 600;
}

.status-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  margin: 6px 0;
}

.summary-text {
  font-size: 0.85rem;
}
</style>