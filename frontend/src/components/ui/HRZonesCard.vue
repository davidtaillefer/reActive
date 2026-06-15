<template>
  <MetricCard title="Time in HR Zones" icon="i-bi-heart-pulse" icon-color="text-danger" value1="" unit1=""
    :value2="maxHr.toString()" unit2="Max BPM">
    <Bar v-if="hasData" :data="chartData" :options="chartOptions" />
    <div v-else class="text-center p-5 text-muted">No HR Zone data available</div>
  </MetricCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import MetricCard from './MetricCard.vue'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps({
  hrmData: { type: Object, required: true }
})

const finalZones = computed(() => {
  const src = zones.value;

  // always return 5 zones
  const result = [
    { zone: 1, minutes: 0, label: '' },
    { zone: 2, minutes: 0, label: '' },
    { zone: 3, minutes: 0, label: '' },
    { zone: 4, minutes: 0, label: '' },
    { zone: 5, minutes: 0, label: '' }
  ];

  const getMinutes = z => z.minutes ?? z.time ?? 0;

  src.forEach((z, index) => {
    if (index === 0) return; // drop zone 0

    const minutes = getMinutes(z);

    if (index >= 1 && index <= 4) {
      // Zones 1–4 map directly
      result[index - 1].minutes += minutes / 60;
      result[index - 1].label =
        `${Math.round(z.min)}–${Math.round(z.max)}`;
    } else if (index >= 5) {
      // collapse everything above into Zone 5
      result[4].minutes += minutes / 60;

      if (!result[4].label) {
        result[4].label = `${Math.round(z.min)}+`;
      }
    }
  });

  return result;
});

const zones = computed(() =>
  (props.hrmData?.hr_zones?.zones || [])
    .slice()
    .sort((a, b) => a.zone - b.zone)
)
const maxHr = computed(() => props.hrmData?.hr_zones?.max_hr || 'N/A')

const hasData = computed(() =>
  Array.isArray(zones.value) && zones.value.length > 0
)

const hrColours = [
  '#007bff', // Zone 1 - blue
  '#28a745', // Zone 2 - green
  '#ffc107', // Zone 3 - yellow
  '#fd7e14', // Zone 4 - orange
  '#dc3545'  // Zone 5 - red
];

const chartData = computed(() => {
  if (!finalZones.value.length) return { labels: [], datasets: [] };

  const labels = finalZones.value.map(z =>
    `Zone ${z.zone} (${z.label})`
  );

  return {
    labels,
    datasets: [{
      label: 'Time in Zone (min)',
      data: finalZones.value.map(z => z.minutes),
      backgroundColor: hrColours.slice(0, 5)
    }]
  };
});

const chartOptions = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const z = finalZones.value[ctx.dataIndex];
          return `Time in Zone ${z.zone}: ${formatDuration(z.minutes)}`;
        }
      }
    },
    legend: { display: false }
  },
  scales: {
    x: { beginAtZero: true, title: { display: true, text: 'Minutes' } }
  }
}

const formatDuration = (minutes) => {
  const totalSeconds = Math.round(minutes * 60);

  const hours = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  const pad = (n) => n.toString().padStart(2, '0');

  if (hours > 0) {
    return `${hours}:${pad(mins)}:${pad(secs)}`;
  }

  return `${mins}:${pad(secs)}`;
};
</script>
