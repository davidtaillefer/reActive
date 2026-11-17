<template>
  <div class="map-wrapper" :style="{ height: resolvedHeight }">
    <button type="button" class="map-reset-button" @click="resetMapView">Reset view</button>
    <div ref="mapContainer" class="map-container" :style="{ height: resolvedHeight }"></div>
    <div v-if="showLegend" class="map-legend">
        <select v-model="colourMode">
          <option value="none">Solid</option>
          <option value="grade">Grade</option>
          <option :disabled="!available.hr" value="hr">Heart Rate</option>
          <option :disabled="!available.speed" value="speed">Speed</option>
          <option :disabled="!available.power" value="power">Power</option>
        </select>

        <div v-if="colourMode === 'grade'" class="legend-bar">
          <span>-10%</span>
          <div class="gradient"></div>
          <span>+10%</span>
        </div>

        <div v-else-if="colourMode !== 'none'" class="legend-bar">
          <span class="legend-min">{{ legendMinLabel }}</span>
          <div :style="legendGradientStyle" class="gradient"></div>
          <span class="legend-max">{{ legendMaxLabel }}</span>
        </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch, nextTick, onUnmounted, toRaw, computed } from 'vue'
import { findNearestPoint } from '@/composables/useHoverMatch'
import { getGradeColour, sanitizeTrackPoints } from '@/utils/climbUtils'
import { getMetricColour as getZoneMetricColour, getMetricLegendStops } from '@/utils/metricColours'
import { usePreferencesStore } from '@/stores/preferences'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const colourMode = ref('none')
const metricBounds = ref({ min: null, max: null })
const available = ref({ hr: false, speed: false, power: false })
const metricContext = ref({ max_hr: null, ftp: null })
const preferences = usePreferencesStore()

const props = defineProps({
  hrmData: [Object, Array], // Support both single object or array
  activity: { type: Object, default: null },
  climbs: { type: Array, default: () => [] },
  height: { type: String, default: '420px' },
  showLegend: { type: Boolean, default: true },
  hoveredPoint: { type: Object, default: null },
  selectedClimbIndex: { type: Number, default: null },
  showClimbIndicators: { type: Boolean, default: true },
  showClimbMarkers: { type: Boolean, default: true },
  showClimbExtent: { type: Boolean, default: true }
});

const resolvedHeight = computed(() => props.height || '420px')

const emit = defineEmits(['point-hover','point-leave','climb-selected'])

const mapContainer = ref(null);
let map = null;
let polylineGroup = L.featureGroup(); // Use a Group to manage multiple routes
let fullTrack = []
let hoverMarker = null
let pendingPolylines = []
let tileLayer = null
let hasAppliedInitialBounds = false

const addOrQueue = (pl) => {
  try {
    if (map && map._loaded) {
      pl.addTo(polylineGroup)
    } else {
      pendingPolylines.push(pl)
    }
  } catch (e) {
    console.error('RouteMap: addOrQueue failed', e)
  }
}

const normalizeClimbs = (source) => {
  if (!source) return []
  if (Array.isArray(source)) return source.filter(Boolean)
  if (typeof source === 'object') {
    return Object.values(source).filter(Boolean)
  }
  return []
}

const initMap = () => {
  if (!mapContainer.value || map) return;

  const explicitHeight = Number.parseInt(props.height, 10)
  const fallbackMinHeight = Number.isFinite(explicitHeight) && explicitHeight > 0 ? explicitHeight : 160
  const parentHeight = mapContainer.value.parentElement?.clientHeight || fallbackMinHeight
  const targetHeight = Math.max(fallbackMinHeight, Math.round(parentHeight))
  mapContainer.value.style.height = `${targetHeight}px`

  map = L.map(mapContainer.value, {
    zoomControl: true,
    attributionControl: false,
    preferCanvas: true,
    worldCopyJump: false,
    fadeAnimation: true
  });

  tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
  tileLayer.addTo(map);
  polylineGroup.addTo(map);
  map.whenReady(() => {
    setTimeout(() => map?.invalidateSize(), 50)
  })
  // (debug probes removed)
  // flush pending polylines when map is ready
  try {
    if (map && typeof map.whenReady === 'function') {
      map.whenReady(() => {
        try {
          requestAnimationFrame(() => {
            try { map.invalidateSize() } catch(e){}
          })
          pendingPolylines.forEach(p => { try { p.addTo(polylineGroup) } catch(e){} })
          pendingPolylines = []
        } catch (e) { /* ignore */ }
      })
    }

    // Flush queued polylines when tiles finish loading
    try {
      if (tileLayer && tileLayer.on) {
        tileLayer.on('load', () => {
          try {
            setTimeout(() => { try { map.invalidateSize() } catch(e){} }, 50)
            pendingPolylines.forEach(p => { try { p.addTo(polylineGroup) } catch(e){} })
            pendingPolylines = []
          } catch (e) { /* ignore */ }
        })
      }
    } catch (e) {}

    // (removed periodic debug probe)
  } catch (e) {}
  // Ensure routes are added even if tile load event doesn't fire
  setTimeout(() => {
    try { pendingPolylines.forEach(p => { try { p.addTo(polylineGroup) } catch(e){} }); pendingPolylines = [] } catch(e){}
  }, 500)
  // trigger a resize/invalidation in case container sizes changed
  setTimeout(() => { try { requestAnimationFrame(() => map?.invalidateSize()) } catch(e){/*ignore*/} }, 300)

  // (removed verbose debug logs)

  // create a single hover marker we can move around
  hoverMarker = L.circleMarker([0,0], { radius: 6, color: '#000', weight: 2, fillColor: '#fff', fillOpacity: 0.9 })
  hoverMarker.addTo(map)
  hoverMarker.setStyle({ opacity: 0, fillOpacity: 0 })

  // map mouse handlers to emit hover events
  map.on('mousemove', (ev) => {
    if (!fullTrack || fullTrack.length === 0) return
    // find nearest point by lat/lng (linear scan - acceptable for moderate sizes)
    let bestIdx = -1
    let bestDist = Infinity
    const mouseLatLng = ev.latlng
    for (let i = 0; i < fullTrack.length; i++){
      const p = fullTrack[i]
      if (p.position_lat == null || p.position_long == null) continue
      const d = mouseLatLng.distanceTo(L.latLng(p.position_lat, p.position_long))
      if (d < bestDist){ bestDist = d; bestIdx = i }
    }
    if (bestIdx >= 0){
      const pt = fullTrack[bestIdx]
      emit('point-hover', { index: bestIdx, timestamp: pt.timestamp, source: 'RouteMap' })
    }
  })

  map.on('mouseout', () => {
    emit('point-leave')
  })
};

const buildRouteBounds = (points) => {
  const coords = sanitizeTrackPoints(points)
    .map((point) => [Number(point.position_lat), Number(point.position_long)])

  if (coords.length < 2) return null
  return L.latLngBounds(coords)
}

const resetMapView = () => {
  if (!map || !fullTrack.length) return

  const routeBounds = buildRouteBounds(fullTrack)
  if (!routeBounds || !routeBounds.isValid || !routeBounds.isValid()) return

  map.fitBounds(routeBounds, { padding: [25, 25], maxZoom: 16 })
}

const shouldShowClimbMarkers = computed(() => props.showClimbIndicators !== false && props.showClimbMarkers !== false)
const shouldShowClimbExtent = computed(() => props.showClimbIndicators !== false && props.showClimbExtent !== false && colourMode.value === 'none')

const drawClimbHighlights = (trackArray, climbList) => {
  if (!trackArray?.length || !Array.isArray(climbList) || !climbList.length) return
  if (!shouldShowClimbMarkers.value && !shouldShowClimbExtent.value) return

  climbList.forEach((climb, idx) => {
    const startIndex = Number(climb.start_index ?? 0)
    const endIndex = Number(climb.end_index ?? startIndex)
    const subset = trackArray.slice(Math.max(0, startIndex), Math.min(trackArray.length, endIndex + 1))
    if (subset.length < 2) return

    const sanitizedSubset = sanitizeTrackPoints(subset)
    const climbLatLngs = sanitizedSubset
      .map((point) => [Number(point.position_lat), Number(point.position_long)])

    if (climbLatLngs.length < 2) return

    const colour = getGradeColour(Number(climb.avg_grade_pct ?? 0))

    if (shouldShowClimbExtent.value) {
      const highlight = L.polyline(climbLatLngs, {
        color: colour,
        weight: 7,
        opacity: 0.95,
        lineCap: 'round',
        lineJoin: 'round',
        className: 'climb-highlight-line'
      })

      highlight.bindTooltip(`Climb ${idx + 1}: ${Number(climb.avg_grade_pct ?? 0).toFixed(1)}% avg grade`)
      addOrQueue(highlight)
    }

    if (!shouldShowClimbMarkers.value) return

    const startPoint = sanitizedSubset[0]
    const startLat = Number(startPoint.position_lat)
    const startLon = Number(startPoint.position_long)
    if (!Number.isFinite(startLat) || !Number.isFinite(startLon)) return

    const startMarker = L.marker([startLat, startLon], {
      icon: L.divIcon({
        className: 'climb-start-icon',
        html: `<div class="climb-start-marker" style="--marker-color:${colour};"><span>⛰</span></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      }),
      keyboard: false,
    })

    startMarker.on('click', () => {
      if (!map) return

      // if (preferences.climbFocusSync) {
      const climbBounds = L.latLngBounds(climbLatLngs)
      if (climbBounds.isValid && climbBounds.isValid()) {
        map.fitBounds(climbBounds, { padding: [30, 30], maxZoom: 16 })
      }

      emit('climb-selected', {
        index: idx,
        climb,
        startIndex,
        endIndex,
        latlngs: climbLatLngs,
      })
      // }
    })

    startMarker.bindTooltip(`Climb ${idx + 1} start`)
    addOrQueue(startMarker)
  })
}

const drawRoute = () => {
  try {
    if (!map) return;

    const sourceActivities = []
    if (Array.isArray(props.hrmData)) {
      sourceActivities.push(...props.hrmData.filter(Boolean))
    } else if (props.hrmData) {
      sourceActivities.push(props.hrmData)
    }
    if (props.activity && !sourceActivities.includes(props.activity)) {
      sourceActivities.push(props.activity)
    }
    if (!sourceActivities.length) return

    const validSourceTracks = sourceActivities
      .map((activityEntry) => activityEntry?.track ?? activityEntry?.hrmData?.track)
      .filter((track) => track && (Array.isArray(track) || typeof track === 'object'))

    const routeTrackSets = validSourceTracks
      .map((rawTrack) => sanitizeTrackPoints(Array.isArray(rawTrack) ? rawTrack : Object.values(toRaw(rawTrack) || {})))
      .filter((track) => track.length >= 2)

    if (!routeTrackSets.length) return

    fullTrack = routeTrackSets.flat()

    const climbSource = normalizeClimbs(
      props.climbs?.length ? props.climbs : (props.activity?.climbs ?? sourceActivities[0]?.climbs ?? [])
    )

    const currentActivity = sourceActivities[0]
    detectAvailableMetrics(fullTrack, currentActivity)

    if (colourMode.value === 'none') {
      for (const track of routeTrackSets) {
        const trackArray = downsample(track, 5)
        if (trackArray.length < 2) continue

        const latlngs = trackArray
          .map((point) => [Number(point.position_lat), Number(point.position_long)])
          .filter(([lat, lon]) => Number.isFinite(lat) && Number.isFinite(lon))

        if (latlngs.length >= 2) {
          try {
            const poly = L.polyline(latlngs, {
              color: 'red',
              weight: 3,
              opacity: 0.7
            })

            const pts = (poly.getLatLngs && typeof poly.getLatLngs === 'function') ? poly.getLatLngs() : []
            const flat = (arr) => arr.flat ? arr.flat(Infinity) : arr.reduce((acc, item) => acc.concat(item), [])
            const validated = flat(pts || []).filter((latLng) => latLng && Number.isFinite(latLng.lat) && Number.isFinite(latLng.lng))

            if (validated.length >= 2) {
              addOrQueue(poly)
            }
          } catch (e) {
            console.error('RouteMap: failed to create/add polyline', e, { latlngs })
          }
        }
      }
    } else {
      const metricTracks = routeTrackSets.map((track) => downsample(track, 5))
      const allMetricValues = metricTracks.flatMap((trackArray) => trackArray.map((point) => getMetricValue(point, colourMode.value)).filter((value) => value != null && !Number.isNaN(value)))
      if (allMetricValues.length) {
        metricBounds.value = {
          min: Math.min(...allMetricValues),
          max: Math.max(...allMetricValues),
        }
      }

      for (const trackArray of metricTracks) {
        if (trackArray.length < 2) continue

        const pts = trackArray
          .map((point) => ({
            lat: Number(point.position_lat),
            lon: Number(point.position_long),
            elev: point.enhanced_altitude != null
              ? Number(point.enhanced_altitude)
              : (point.elevation != null ? Number(point.elevation) : (point.altitude ?? null)),
            raw: point
          }))
          .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon))

        if (pts.length < 2) continue

        try {
          const groups = []
          let currentGroup = null

          for (let i = 0; i < pts.length - 1; i++) {
            const a = pts[i]
            const b = pts[i + 1]
            if (a.lat === b.lat && a.lon === b.lon) continue

            let metricVal = null
            if (colourMode.value === 'grade') {
              if (a.elev != null && b.elev != null) {
                const distance = L.latLng(a.lat, a.lon).distanceTo(L.latLng(b.lat, b.lon))
                if (distance > 0) metricVal = ((b.elev - a.elev) / distance) * 100
              }
            } else {
              const v1 = getMetricValue(a.raw, colourMode.value)
              const v2 = getMetricValue(b.raw, colourMode.value)
              if (v1 != null && v2 != null) metricVal = (v1 + v2) / 2
              else metricVal = v1 != null ? v1 : v2
            }

            const colour = getMetricColour(colourMode.value, metricVal, metricBounds.value.min, metricBounds.value.max)

            if (currentGroup && currentGroup.colour === colour) {
              currentGroup.latlngs.push([b.lat, b.lon])
            } else {
              if (currentGroup) groups.push(currentGroup)
              currentGroup = { colour, latlngs: [[a.lat, a.lon], [b.lat, b.lon]] }
            }
          }

          if (currentGroup) groups.push(currentGroup)

          for (const group of groups) {
            const polyline = L.polyline(group.latlngs, { color: group.colour, weight: 4, opacity: 0.95 })
            addOrQueue(polyline)
          }
        } catch (e) {
          console.error('RouteMap: failed to create segmented polylines', e)
        }
      }
    }

    drawClimbHighlights(fullTrack, climbSource)

    try {
      const routeBounds = buildRouteBounds(fullTrack)
      if (routeBounds && !hasAppliedInitialBounds) {
        setTimeout(() => {
          try {
            map.invalidateSize()
            if (routeBounds.isValid && routeBounds.isValid()) {
              map.fitBounds(routeBounds, { padding: [25, 25], maxZoom: 16 })
              hasAppliedInitialBounds = true
            }
          } catch (e) {
            console.error('RouteMap: fitBounds failed', e)
          }
        }, 80)
      }
    } catch (e) {
      console.error('RouteMap: center/fitBounds wrapper failed', e)
    }
  } catch (err) {
    console.error('RouteMap.drawRoute error', err)
  }
};

// const getGradeColour = (grade) => {
//   if (grade == null) return '#999'

//   // Clamp
//   const g = Math.max(-10, Math.min(10, grade))

//   // Gradient:
//   // downhill = blue, flat = yellow, uphill = red
//   if (g < 0) {
//     const t = Math.abs(g) / 10
//     return `rgb(${0}, ${Math.round(150 * (1 - t))}, ${255})`
//   } else {
//     const t = g / 10
//     return `rgb(${255}, ${Math.round(200 * (1 - t))}, ${0})`
//   }
// }

// Return a numeric value for the chosen metric from a track point
const getMetricValue = (pt, metric) => {
  if (!pt) return null

  const tryKeys = (keys) => {
    for (const k of keys) {
      if (pt[k] != null) return pt[k]
    }
    return null
  }

  if (metric === 'hr') {
    return tryKeys(['heart_rate', 'heart_rate_bpm', 'hr', 'heartrate', 'heartRate', 'avg_heart_rate'])
  }

  if (metric === 'power') {
    return tryKeys(['power', 'power_smooth', 'watts', 'avg_power'])
  }

  if (metric === 'speed') {
    // Convert m/s -> km/h for display and mapping if likely in m/s
    const v = tryKeys(['enhanced_speed', 'speed', 'speed_smooth', 'velocity_smooth', 'velocity'])
    if (v == null) return null
    // If the value looks like m/s (small number), convert
    if (Math.abs(v) < 30) return v * 3.6
    return v
  }

  if (metric === 'grade') {
    return tryKeys(['grade_smooth', 'grade', 'avg_grade', 'grade_pct'])
  }

  return null
}

const computeMetricBounds = (trackArray, metric) => {
  const vals = trackArray.map(p => getMetricValue(p, metric)).filter(v => v != null && !isNaN(v))
  if (vals.length === 0) {
    metricBounds.value = { min: null, max: null }
  } else {
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    // If min == max provide a small buffer so gradient still shows
    metricBounds.value = { min: min === max ? min - 1 : min, max: min === max ? max + 1 : max }
  }
}

const detectAvailableMetrics = (trackArray, activity) => {
  // Prefer server-provided metadata when available
  const metrics = activity?.metricsAvailability || (Array.isArray(props.hrmData) ? (props.hrmData[0] && props.hrmData[0].metricsAvailability) : (props.hrmData && props.hrmData.metricsAvailability))
  if (metrics && typeof metrics === 'object') {
    available.value = {
      hr: !!metrics.heartRate,
      speed: !!metrics.speed,
      power: !!metrics.power,
    }
  } else {
    const hr = trackArray.some(p => getMetricValue(p, 'hr') != null)
    const speed = trackArray.some(p => getMetricValue(p, 'speed') != null)
    const power = trackArray.some(p => getMetricValue(p, 'power') != null)
    available.value = { hr, speed, power }
  }

  metricContext.value = {
    max_hr: activity?.hr_zones?.max_hr ?? activity?.max_heart_rate ?? null,
    ftp: activity?.power_zones?.ftp ?? null,
  }
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

const getMetricColour = (metric, val) => {
  if (val == null) return '#999'

  const options = {}
  if (metric === 'hr' && metricContext.value.max_hr != null) {
    options.max_hr = metricContext.value.max_hr
  }
  if (metric === 'power' && metricContext.value.ftp != null) {
    options.ftp = metricContext.value.ftp
  }

  if (metric === 'grade') {
    return getGradeColour(Number(val), -10, 10)
  }

  return getZoneMetricColour(metric, Number(val), options)
}

const formatMetric = (metric, v) => {
  if (v == null) return '-'
  if (metric === 'hr') return `${Math.round(v)} bpm`
  if (metric === 'power') return `${Math.round(v)} W`
  if (metric === 'speed') return `${(Math.round(v * 10) / 10).toFixed(1)} km/h`
  return String(v)
}

const legendGradientStyle = computed(() => {
  const metric = colourMode.value === 'none' ? 'hr' : colourMode.value
  const stops = getMetricLegendStops(metric)
  return {
    background: `linear-gradient(to right, ${stops.join(', ')})`
  }
})

const legendMinLabel = computed(() => formatMetric(colourMode.value, metricBounds.value.min))
const legendMaxLabel = computed(() => formatMetric(colourMode.value, metricBounds.value.max))

onMounted(() => {
  nextTick(() => {
    const hasTrack = Array.isArray(props.hrmData)
      ? props.hrmData.some((entry) => (entry?.track && (Array.isArray(entry.track) || typeof entry.track === 'object')))
      : !!(props.hrmData?.track || props.activity?.track)

    if (hasTrack) {
      initMap();
      drawRoute();
      requestAnimationFrame(() => map?.invalidateSize())
      setTimeout(() => map?.invalidateSize(), 500);
    }
  });
});

// Watch for data changes (e.g. when the API fetch finishes)
watch(
  () => [props.hrmData, props.activity],
  () => {
    const hasTrack = Array.isArray(props.hrmData)
      ? props.hrmData.some((entry) => (entry?.track && (Array.isArray(entry.track) || typeof entry.track === 'object')))
      : !!(props.hrmData?.track || props.activity?.track)

    if (!hasTrack) return

    hasAppliedInitialBounds = false

    nextTick(() => {
      if (!map) initMap();
      if (map) {
        requestAnimationFrame(() => map.invalidateSize())
      }
      drawRoute();
    })
  },
  { immediate: true, deep: true }
);

// Respond to hoveredPoint updates from parent
watch(() => props.hoveredPoint, (hp) => {
  if (!map || !hp) {
    // hide marker
    hoverMarker?.setStyle({ opacity: 0, fillOpacity: 0 })
    return
  }

  // match against fullTrack (unsampled)
  const match = findNearestPoint(fullTrack, hp, { toleranceMs: 1000 })
  if (match && match.point && match.point.position_lat != null && match.point.position_long != null) {
    const lat = match.point.position_lat
    const lon = match.point.position_long
    hoverMarker.setLatLng([lat, lon])
    hoverMarker.setStyle({ opacity: 1, fillOpacity: 0.9 })
  } else {
    hoverMarker.setStyle({ opacity: 0, fillOpacity: 0 })
  }

}, { immediate: false })

watch(colourMode, () => {
  drawRoute()
})

watch(
  () => props.selectedClimbIndex,
  (nextIndex) => {
    if (!map || !Number.isInteger(nextIndex) || nextIndex < 0 || !Array.isArray(props.climbs) || props.climbs.length === 0) return

    const climb = props.climbs[nextIndex]
    if (!climb) return

    const startIndex = Number(climb.start_index ?? 0)
    const endIndex = Number(climb.end_index ?? startIndex)
    const subset = fullTrack.slice(Math.max(0, startIndex), Math.min(fullTrack.length, endIndex + 1))
    const sanitizedSubset = sanitizeTrackPoints(subset)
    const climbLatLngs = sanitizedSubset.map((point) => [Number(point.position_lat), Number(point.position_long)])

    if (climbLatLngs.length < 2) return

    const bounds = L.latLngBounds(climbLatLngs)
    if (bounds.isValid && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 16 })
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (map) map.remove();
});

const downsample = (arr, step = 5) => {
  return arr.filter((_, i) => i % step === 0);
};
</script>

<style scoped>
.map-container {

  width: 100%;
  background: #f8f9fa;
}

.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 160px;
  flex: 1 1 auto;
  overflow: hidden;
}

.map-reset-button {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.96);
  color: #1f2937;
  font-size: 0.8rem;
  line-height: 1;
  padding: 7px 10px;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 160px;
}

:deep(.leaflet-container) {
  width: 100% !important;
  height: 100% !important;
}

.map-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 1000;            /* ensure above tiles */
  pointer-events: auto;

  background: rgba(255,255,255,0.95);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}

:deep(.climb-start-icon) {
  background: transparent;
  border: none;
}

:deep(.climb-start-marker) {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.95);
  background: rgba(255,255,255,0.94);
  color: var(--marker-color);
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
}


.legend-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.gradient {
  width: 100px;
  height: 8px;
  background: linear-gradient(to right, blue, yellow, red);
  border-radius: 4px;
}
</style>
