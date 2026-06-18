<template>
    <BCard class="h-100">
        <BCardBody class="pt-3 pb-2">
            <div class="d-flex align-items-center justify-content-between mb-0">
                <div class="d-flex align-items-center gap-2">
                    <IBiCalendarEvent class="text-primary fs-3" />
                    <h6 class="card-title mb-0 fw-semibold">Training Status</h6>
                </div>

                <div class="text-end">
                    <div v-if="loading">
                        <BSpinner />
                        <div class="mt-2 text-muted" style="font-size:0.75rem;">Loading...</div>
                    </div>
                    <div v-else-if="error" class="text-danger">{{ error }}</div>
                    <div v-else-if="current">
                        <p :class="`h4 mb-0 fw-bold text-${current.color}`">{{ current.label }}</p>
                        <p class="text-muted mb-0" style="font-size: 0.75rem;">{{ current.description }}</p>
                    </div>
                </div>
            </div>

            <div v-if="timeline && timeline.length" class="timeline-container">
                <div class="timeline-row" role="list">
                    <div
                        v-for="(d, i) in timeline"
                        :key="i"
                        :class="['timeline-segment', statusBgClass(d.status)]"
                        :style="{ flex: d.width }"
                        :title="`${statusMap[d.status]?.label || 'Unknown'} from ${d.startDate} to ${d.endDate}`"
                    >
                    </div>
                </div>
                <div class="timeline-legend mt-1 d-flex justify-content-between small text-muted">
                    <div>Start: {{ startLabel }}</div>
                    <div>End: {{ endLabel }}</div>
                </div>
            </div>
            <div v-else class="text-muted text-center">No training status history available</div>
        </BCardBody>
    </BCard>
</template>

<script setup>
import { computed, onMounted, watch, toRef } from 'vue'
import { useStats } from '@/composables/useStats'

const { stats, loading, error, fetchStats, getTodayStats } = useStats()

// Small status mapping for label & colours (matches TrainingStatusCard)
const statusMap = {
    1: { label: 'Detraining', color: 'secondary', description: 'Your fitness is declining. Consider increasing activity.' },
    5: { label: 'Recovery', color: 'info', description: 'Your body is recovering—this is a good time to rest.' },
    4: { label: 'Maintaining', color: 'primary', description: 'You are maintaining your current fitness level.' },
    7: { label: 'Productive', color: 'success', description: 'Your fitness is improving—keep it up!' },
    2: { label: 'Overreaching', color: 'warning', description: 'You may be pushing too hard—consider recovery.' },
    0: { label: 'Unproductive', color: 'danger', description: 'Your training is not producing expected gains.' },
    8: { label: 'Strained', color: 'strained', description: 'Your body is under excessive stress—immediate recovery needed.' }
}

const DAYS = 90

// Accept the viewed month from parent (CalendarWrapper)
const props = defineProps({
    month: { type: Object, default: () => new Date() }
})

const monthRef = toRef(props, 'month')

const fetchForCurrentOrMonth = (m) => {
    const now = new Date()
    const isCurrentMonth = m.getFullYear() === now.getFullYear() && m.getMonth() === now.getMonth()

    if (isCurrentMonth) {
        const end = new Date()
        const start = new Date()
        start.setDate(end.getDate() - DAYS)
        fetchStats({ startDate: start, endDate: end })
    } else {
        // For previous months, fetch only that month
        const start = new Date(m.getFullYear(), m.getMonth(), 1)
        const end = new Date(m.getFullYear(), m.getMonth() + 1, 0)
        fetchStats({ startDate: start, endDate: end })
    }
}

onMounted(() => {
    fetchForCurrentOrMonth(monthRef.value || new Date())
})

// React to changes in viewed month
watch(monthRef, (nv) => {
    if (!nv) return
    fetchForCurrentOrMonth(nv)
})


const timeline = computed(() => {
    if (!stats.value || !Array.isArray(stats.value) || !stats.value.length) return []

    // Ensure sorted ascending by date
    const arr = stats.value.slice().sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

    // Convert to day buckets; combine consecutive equal statuses into segments
    const days = arr.map(d => ({ date: d.date, status: d.training_status ?? null }))

    if (!days.length) return []

    // Build segments: consecutive same status grouped
    const segments = []
    let cur = { status: days[0].status, length: 1, startIndex: 0, endIndex: 0 }
    for (let i = 1; i < days.length; i++) {
        if (days[i].status === cur.status) {
            cur.length++
            cur.endIndex = i
        } else {
            segments.push(cur)
            cur = { status: days[i].status, length: 1, startIndex: i, endIndex: i }
        }
    }
    segments.push(cur)

    // Convert lengths to flex proportions and include start/end dates per segment
    const total = segments.reduce((s, x) => s + x.length, 0)
    return segments.map(s => ({
        status: s.status,
        width: s.length / total,
        startDate: days[s.startIndex].date,
        endDate: days[s.endIndex].date
    }))
})

const isViewingCurrentMonth = computed(() => {
    const now = new Date()
    const m = monthRef.value || now
    return m.getFullYear() === now.getFullYear() && m.getMonth() === now.getMonth()
})

const current = computed(() => {
    if (!stats.value || !Array.isArray(stats.value) || !stats.value.length) return null

    if (isViewingCurrentMonth.value) {
        // Determine latest stat by date
        const latest = stats.value.slice().sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()).pop()
        if (!latest) return null
        return statusMap[latest.training_status] || { label: 'Unknown', color: 'dark', description: '' }
    }

    // For previous months: pick the status that occurs on the most days (mode)
    const counts = {}
    for (const s of stats.value) {
        if (s.training_status == null) continue
        const key = String(s.training_status)
        counts[key] = (counts[key] || 0) + 1
    }

    const entries = Object.entries(counts)
    if (!entries.length) return { label: 'No data', color: 'secondary', description: 'No stats available for this month.' }

    // Find the status with the highest count
    entries.sort((a, b) => b[1] - a[1])
    const mostStatusKey = entries[0][0]
    const intStatus = Number(mostStatusKey)
    return statusMap[intStatus] || { label: 'Unknown', color: 'dark', description: '' }
})

const startLabel = computed(() => {
    if (!stats.value || !stats.value.length) {
        // If we have no stats, show the month start when viewing a past month
        if (!monthRef.value) return ''
        const s = new Date(monthRef.value.getFullYear(), monthRef.value.getMonth(), 1)
        return s.toLocaleDateString()
    }

    if (!isViewingCurrentMonth.value) {
        const s = new Date(monthRef.value.getFullYear(), monthRef.value.getMonth(), 1)
        return s.toLocaleDateString()
    }

    const d = new Date(stats.value.slice().sort((a, b) => new Date(a.date) - new Date(b.date))[0].date)
    return d.toLocaleDateString()
})

const endLabel = computed(() => {
    if (!stats.value || !stats.value.length) {
        if (!monthRef.value) return ''
        const e = new Date(monthRef.value.getFullYear(), monthRef.value.getMonth() + 1, 0)
        return e.toLocaleDateString()
    }

    if (!isViewingCurrentMonth.value) {
        const e = new Date(monthRef.value.getFullYear(), monthRef.value.getMonth() + 1, 0)
        return e.toLocaleDateString()
    }

    const d = new Date(stats.value.slice().sort((a, b) => new Date(b.date) - new Date(a.date))[0].date)
    return d.toLocaleDateString()
})

const timelineTitle = computed(() => {
    const statusLabel = current.value ? current.value.label : 'Training status'
    return `${statusLabel} from ${startLabel.value} to ${endLabel.value}`
})

const statusBgClass = (status) => {
    const s = statusMap[status]
    const color = s ? s.color : 'secondary'
    return `bg-${color}`
}
</script>

<style scoped>
.timeline-container {
    width: 100%;
}

.timeline-row {
    display: flex;
    height: 18px;
    border-radius: 6px;
    overflow: hidden;
    margin-top: 6px;
}

.timeline-segment {
    height: 100%;
}

.timeline-container { margin-bottom: 0; margin-top: 30px;}
.timeline-legend { margin-bottom: 0; }

/* Custom colour for 'Strained' status (medium purple) */
.bg-strained { background-color: #7e57c2 !important; }
.text-strained { color: #6f42c1 !important; }
</style>
