<template>
  <div class="card shadow-sm">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h6 class="mb-0 fw-semibold">{{ climbNumberLabel }} - {{ climbTitle }}</h6>
          <small class="text-muted">Avg {{ avgGradeLabel }} · Max {{ maxGradeLabel }}</small>
        </div>

        <div v-if="climbs.length > 1" class="d-flex align-items-center gap-2">
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="goToPrevious" aria-label="Previous climb">
            ‹
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="goToNext" aria-label="Next climb">
            ›
          </button>
        </div>
      </div>

      <div v-if="selectedClimb && profile.datasets.length" class="chart-wrap">
        <Line :data="chartData" :options="chartOptions" />
      </div>
      <div v-else class="text-muted small py-3">No climb data available.</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { Line } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { buildClimbProfile, formatDistanceLabel, formatGradeValue } from '@/utils/climbUtils';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const props = defineProps({
  activity: { type: Object, default: null },
  hrmData: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: 0 },
});

const emit = defineEmits(['climb-selected']);

const activeIndex = ref(props.selectedIndex ?? 0);

const climbs = computed(() => {
  const source = props.activity?.climbs ?? props.hrmData?.[0]?.climbs ?? [];
  return Array.isArray(source) ? source.filter(Boolean) : [];
});

watch(
  () => climbs.value.length,
  () => {
    if (climbs.value.length === 0) return;
    if (activeIndex.value >= climbs.value.length) {
      activeIndex.value = 0;
    }
    if (activeIndex.value < 0) {
      activeIndex.value = climbs.value.length - 1;
    }
  },
  { immediate: true },
);

watch(
  () => props.selectedIndex,
  (nextIndex) => {
    if (!Number.isInteger(nextIndex) || nextIndex < 0 || nextIndex >= climbs.value.length) return;
    activeIndex.value = nextIndex;
  },
  { immediate: true },
);

const selectedClimb = computed(() => climbs.value[activeIndex.value] || null);

const trackPoints = computed(() => {
  const track = props.hrmData?.[0]?.track ?? props.activity?.track ?? [];
  return Array.isArray(track) ? track : Object.values(track || {});
});

const profile = computed(() => {
  if (!selectedClimb.value) {
    return { points: [], datasets: [], totalDistance: 0 };
  }
  return buildClimbProfile(selectedClimb.value, trackPoints.value);
});

const chartData = computed(() => ({
  datasets: profile.value.datasets,
}));

const climbNumberLabel = computed(() => {
  if (!selectedClimb.value) return 'No climb';
  return `Climb ${activeIndex.value + 1}`;
});

const climbTitle = computed(() => {
  if (!selectedClimb.value) return 'No climb';
  return selectedClimb.value.category || 'Climb profile';
});

const avgGradeLabel = computed(() => {
  if (!selectedClimb.value) return '-';
  return `${Number(selectedClimb.value.avg_grade_pct ?? 0).toFixed(1)}%`;
});

const maxGradeLabel = computed(() => {
  if (!selectedClimb.value) return '-';
  return `${Number(selectedClimb.value.max_grade_pct ?? selectedClimb.value.avg_grade_pct ?? 0).toFixed(1)}%`;
});

const getGradeAtPoint = (context) => {
  const parsedX = Number(context?.parsed?.x ?? 0);
  const points = profile.value.points || [];

  if (!points.length) return 0;

  let nearest = points[0];
  let shortestDelta = Number.POSITIVE_INFINITY;

  for (const point of points) {
    const delta = Math.abs(Number(point.distanceMeters ?? 0) - parsedX);
    if (delta < shortestDelta) {
      shortestDelta = delta;
      nearest = point;
    }
  }

  return Number(nearest.grade ?? 0);
};

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  interaction: {
    mode: 'nearest',
    intersect: false,
  },
  elements: {
    point: {
      radius: 0,
    },
    line: {
      borderWidth: 6,
      cubicInterpolationMode: 'default',
      tension: 0,
      fill: true,
    },
  },
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      callbacks: {
        title: (items) => {
          const item = items?.[0];
          const xValue = Number(item?.parsed?.x ?? 0);
          return `Distance: ${formatDistanceLabel(xValue)}`;
        },
        label: (context) => {
          const parsed = context?.parsed ?? {};
          const elevation = Number(parsed.y ?? 0);
          const grade = getGradeAtPoint(context);
          return `Elevation: ${elevation.toFixed(0)} m · Grade: ${formatGradeValue(grade, 1)}`;
        },
      },
    },
  },
  scales: {
    x: {
      type: 'linear',
      min: 0,
      max: Math.max(Math.round(profile.value.totalDistance || 0), 1),
      ticks: {
        maxTicksLimit: 6,
        callback: (value) => formatDistanceLabel(value),
      },
      title: {
        display: true,
        text: 'Distance',
      },
    },
    y: {
      title: {
        display: true,
        text: 'Elevation (m)',
      },
    },
  },
}));

const activeLabel = computed(() => {
  if (!selectedClimb.value) return 'No climbs';
  return `${activeIndex.value + 1} of ${climbs.value.length}`;
});

function syncActiveClimb(nextIndex) {
  if (!climbs.value.length) return;
  activeIndex.value = nextIndex;
  emit('climb-selected', {
    index: nextIndex,
    climb: climbs.value[nextIndex] || null,
  });
}

function goToPrevious() {
  if (!climbs.value.length) return;
  const nextIndex = (activeIndex.value - 1 + climbs.value.length) % climbs.value.length;
  syncActiveClimb(nextIndex);
}

function goToNext() {
  if (!climbs.value.length) return;
  const nextIndex = (activeIndex.value + 1) % climbs.value.length;
  syncActiveClimb(nextIndex);
}
</script>

<style scoped>
.chart-wrap {
  position: relative;
  height: 220px;
}
</style>
