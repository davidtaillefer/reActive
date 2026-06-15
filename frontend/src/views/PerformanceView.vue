<template>
    <BContainer fluid class="p-3">
        <BRow class="g-3">

            <!-- LEFT: Muscle Fatigue Map -->
            <BCol cols="12" lg="8" class="d-flex flex-column">
                <BCard class="shadow-sm flex-grow-1">
                    <BCardBody class="d-flex flex-column">
                        <h5 class="mb-3">Muscle Fatigue</h5>

                        <MuscleMap v-if="hasFatigue"
                            :muscleData="{ load: (performance.ratios && Object.keys(performance.ratios).length) ? performance.ratios : performance.fatigue }"
                            mode="fatigue" class="flex-grow-1" />

                        <div v-else class="text-center text-muted">
                            No muscle fatigue data available
                        </div>
                    </BCardBody>
                </BCard>
            </BCol>

            <!-- RIGHT: Performance Metrics -->
            <BCol cols="12" lg="4" class="d-flex flex-column gap-3">

                <!-- Recovery -->
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <div class="d-flex align-items-center gap-2">
                                <component :is="icon" :class="iconColor" />
                                <h6 class="card-title mb-0 fw-semibold">Recovery</h6>
                            </div>

                            <div class="text-end">
                                <p class="h4 mb-0 fw-bold">{{ cardioPercent }}%</p>
                                <p class="text-muted mb-0" style="font-size: 0.75rem;">Cardio</p>
                            </div>
                            <div class="text-end">
                                <p class="h4 mb-0 fw-bold">{{ strengthPercent }}%</p>
                                <p class="text-muted mb-0" style="font-size: 0.75rem;">Strength</p>
                            </div>
                        </div>
                        <div class="donut-container">
                            <Doughnut :data="donutData" :options="donutOptions" />
                            <div class="donut-center">
                                <div class="recoveryColour current-value">{{ recoveryPercent }}%</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Injury Risk -->
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <div class="d-flex align-items-center gap-2">
                                <component :is="icon" :class="iconColor" />
                                <h6 class="card-title mb-0 fw-semibold">Injury Risk</h6>
                            </div>
                        </div>
                        <div class="donut-container">
                            <Doughnut :data="injuryData" :options="injuryOptions" />
                            <div class="donut-center">
                                <h3 :class="injuryColour">{{ injuryLabel }}</h3>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Training Load -->
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <div class="d-flex align-items-center gap-2">
                                <component :is="icon" :class="iconColor" />
                                <h6 class="card-title mb-0 fw-semibold">Training Load</h6>
                            </div>

                            <div class="text-end">
                                <p class="h4 mb-0 fw-bold">{{ performance.atl.toFixed(0) }}</p>
                                <p class="text-muted mb-0" style="font-size: 0.75rem;">ATL</p>
                            </div>
                            <div class="text-end">
                                <p class="h4 mb-0 fw-bold">{{ performance.ctl.toFixed(0) }}</p>
                                <p class="text-muted mb-0" style="font-size: 0.75rem;">CTL</p>
                            </div>
                        </div>
                        <div class="donut-container">
                            <Doughnut :data="ratioData" :options="ratioOptions" />
                            <div class="donut-center">
                                <div class="current-value">{{ (performance.atl /
                                    performance.ctl).toFixed(1) }}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Training Status -->
                <TrainingStatusCard />

            </BCol>

        </BRow>
    </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { BContainer, BRow, BCol, BCard, BCardBody } from 'bootstrap-vue-next'
import { Doughnut } from 'vue-chartjs'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js'
import MuscleMap from '@/components/ui/MuscleMap.vue'
import TrainingStatusCard from '@/components/ui/TrainingStatusCard.vue'

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
)

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

const performance = ref({
    fatigue: {},
    baselines: {},
    ratio: {},
    atl: 0,
    ctl: 0,
    form: 0,
    injury_risk: 0,
    recovery: {
        cardio: 0,
        strength: 0,
        overall: 0
    }
})

// Load data
onMounted(async () => {
    try {
        const res = await fetch(`${apiBaseUrl}performance`)
        if (!res.ok) throw new Error('Failed to fetch performance')

        const data = await res.json()
        performance.value = data

    } catch (err) {
        console.error('Error loading performance data:', err)
    }
})

const hasFatigue = computed(() =>
    performance.value.fatigue &&
    Object.keys(performance.value.fatigue).length > 0
)

const recoveryPercent = computed(() =>
    Math.round((performance.value.recovery.overall || 0) * 100)
)

const cardioPercent = computed(() =>
    Math.round((performance.value.recovery.cardio || 0) * 100)
)

const strengthPercent = computed(() =>
    Math.round((performance.value.recovery.strength || 0) * 100)
)

const recoveryColour = computed(() => {
    const r = performance.value.recovery.overall || 0

    if (r > 0.75) return 'green'
    if (r > 0.5) return 'yellow'
    return 'red'
})

const donutData = computed(() => {
    const val = Math.min(recoveryPercent.value, 100)

    return {
        datasets: [
            {
                data: [val, 100 - val],
                backgroundColor: [recoveryColour.value, '#e9ecef'],
                borderWidth: 0,
                cutout: '70%',
                borderRadius: 6
            }
        ]
    }
})

const donutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    rotation: -90,
    circumference: 180,
    plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
    }
}

const injuryLabel = computed(() => {
    const r = performance.value.injury_risk || 0

    if (r < 0.3) return 'Low'
    if (r < 0.7) return 'Moderate'
    return 'High'
})

const injuryColour = computed(() => {
    const r = performance.value.injury_risk || 0

    if (r < 0.3) return 'text-success'
    if (r < 0.7) return 'text-warning'
    return 'text-danger'
})

const injuryDoughnutColour = computed(() => {
    const r = performance.value.injury_risk || 0

    if (r < 0.3) return 'green'
    if (r < 0.7) return 'yellow'
    return 'red'
})

const injuryData = computed(() => {
    const val = Math.min(performance.value.injury_risk * 100 || 0, 100)

    return {
        datasets: [
            {
                data: [val, 100 - val],
                backgroundColor: [injuryDoughnutColour.value, '#e9ecef'],
                borderWidth: 0,
                cutout: '70%',
                borderRadius: 6
            }
        ]
    }
})

const injuryOptions = {
    responsive: true,
    maintainAspectRatio: false,
    rotation: -90,
    circumference: 180,
    plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
    }
}

const ratioDoughnutColour = computed(() => {
    const r = performance.value.atl / performance.value.ctl

    if (r < 0.8) return 'yellow'
    if (r < 1.2) return 'green'
    return 'red'
})

const ratioData = computed(() => {
    const val = performance.value.atl / performance.value.ctl

    return {
        datasets: [
            {
                data: [val, 2 - val],
                backgroundColor: [ratioDoughnutColour.value, '#e9ecef'],
                borderWidth: 0,
                cutout: '70%',
                borderRadius: 6
            }
        ]
    }
})

const ratioOptions = {
    responsive: true,
    maintainAspectRatio: false,
    rotation: -90,
    circumference: 180,
    plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
    }
}

</script>

<style scoped>
/* Ensure MuscleMap fills card nicely (scope to muscle-map to avoid affecting other SVGs) */
:deep(.muscle-map svg) {
    width: 100%;
    height: 100%;
}

.donut-container {
    position: relative;
    width: 180px;
    height: 120px;
    margin: 0 auto;
    display: block;
    text-align: center;
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
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1;
}
</style>