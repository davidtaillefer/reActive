<template>
  <BCard v-if="editable || localSets.length > 0" title="Workout Sets" class="mt-4 shadow-sm">
    <div class="d-flex justify-content-between p-2">
      <div>
        <BButton size="sm" variant="primary" v-if="editable" @click="addRow">Add Row</BButton>
      </div>
      <div>
        <BButton size="sm" variant="secondary" v-if="!editable" @click="startEdit">Edit</BButton>
        <div v-else>
          <BButton size="sm" variant="success" class="me-2" @click="saveSets">Save</BButton>
          <BButton size="sm" variant="danger" @click="cancelEdit">Cancel</BButton>
        </div>
      </div>
    </div>

    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0">
        <thead class="table-light">
          <tr>
            <th>Set</th>
            <th>Category</th>
            <th>Exercise</th>
            <th>Reps</th>
            <th>Weight</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(set, index) in localSets" :key="set._uid"
              @dragover.prevent="onDragOver($event, index)"
              @drop.prevent="onDrop($event, index)"
              :class="{ 'drag-over': dragOverIndex === index, 'dragging-row': dragIndex === index }">
            <td class="drag-handle-cell">
              <span v-if="editable" class="drag-handle" draggable="true" @dragstart="onDragStart($event, index)">≡</span>
              <span v-else class="drag-handle-placeholder">&nbsp;</span>
            </td>
            <td>{{ index + 1 }}</td>
            <td class="text-capitalize">
              <div v-if="!editable">{{ set.exercise_category || 'Strength' }}</div>
              <div v-else>
                <input class="form-control form-control-sm" v-model="set.exercise_category" />
              </div>
            </td>
            <td class="text-capitalize">
              <div v-if="!editable">{{ set.exercise_name || 'Strength' }}</div>
              <div v-else>
                <input class="form-control form-control-sm" v-model="set.exercise_name" />
              </div>
            </td>
            <td>
              <div v-if="!editable">{{ set.reps || 0 }}</div>
              <div v-else>
                <input type="number" min="0" class="form-control form-control-sm" v-model.number="set.reps" />
              </div>
            </td>
            <td>
              <div v-if="!editable">{{ set.weight || 0 }} kg</div>
              <div v-else>
                <input type="number" step="0.1" min="0" class="form-control form-control-sm" v-model.number="set.weight" />
              </div>
            </td>
            <td>
              <div v-if="!editable">{{ formatSeconds(set.duration) }}</div>
              <div v-else>
                <input type="number" min="0" class="form-control form-control-sm" v-model.number="set.duration" />
              </div>
            </td>
            <td class="text-end">
              <BButton size="sm" variant="danger" v-if="editable" @click="deleteRow(index)">Delete</BButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BCard>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

const props = defineProps({
  hrmData: { type: Object, required: true },
  hrmfile: { type: String, required: true }
});

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL


const sets = computed(() => {
  const data = Array.isArray(props.hrmData) ? props.hrmData[0] : props.hrmData;
  const rawSets = data?.sets;
  return rawSets ? Object.values(rawSets) : [];
});

// local editable copy
const localSets = ref([])
const editable = ref(false)
const dragIndex = ref(-1)
const dragOverIndex = ref(-1)
let uidCounter = 0

watch(() => sets.value, (v) => {
  // deep clone
  localSets.value = v.map(s => {
    const copy = { ...s };
    if (!copy._uid) {
      uidCounter += 1
      copy._uid = `set-${Date.now()}-${uidCounter}`
    }
    return copy
  })
}, { immediate: true })

function startEdit() {
  editable.value = true
}

function cancelEdit() {
  // revert
  localSets.value = sets.value.map(s => ({ ...s }))
  editable.value = false
}

async function saveSets() {
  try {
    const res = await fetch(apiBaseUrl + `hrm/${props.hrmfile}/sets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sets: localSets.value })
    })

    if (!res.ok) {
      const txt = await res.text()
      console.error('failed to save sets', res.status, txt)
      alert('Failed to save sets')
      return
    }

    editable.value = false
    // leave localSets as-is; parent can re-fetch as needed
    alert('Sets saved')
  } catch (err) {
    console.error('error saving sets', err)
    alert('Error saving sets')
  }
}

function addRow() {
  const newSet = {
    timestamp: new Date().toISOString(),
    reps: 0,
    weight: 0,
    duration: 0,
    exercise_category: 'Strength',
    subtype: null,
    exercise_name: ''
  }
  uidCounter += 1
  newSet._uid = `set-${Date.now()}-${uidCounter}`
  localSets.value.push(newSet)
}

function deleteRow(index) {
  if (index >= 0 && index < localSets.value.length) {
    localSets.value.splice(index, 1)
  }
}

function onDragStart(e, index) {
  dragIndex.value = index
  try { e.dataTransfer.setData('text/plain', String(index)) } catch {}
}

function onDragOver(e, index) {
  dragOverIndex.value = index
}

function onDrop(e, index) {
  const from = dragIndex.value
  let to = index
  if (from === -1 || to === -1 || from === to) {
    dragIndex.value = -1
    dragOverIndex.value = -1
    return
  }

  const item = localSets.value.splice(from, 1)[0]

  // If dragging from before the drop target, the target index shifts left by 1 after removal
  const insertIndex = from < to ? to - 1 : to
  const boundedIndex = Math.max(0, Math.min(localSets.value.length, insertIndex))
  localSets.value.splice(boundedIndex, 0, item)

  dragIndex.value = -1
  dragOverIndex.value = -1
}

function onDragEnd(e, index) {
  dragIndex.value = -1
  dragOverIndex.value = -1
}


const formatSeconds = (s: number) => {
  if (!s) return '0s';
  if (s < 60) return `${Math.floor(s)}s`;
  const mins = Math.floor(s / 60);
  const secs = Math.floor(s % 60).toString().padStart(2, '0');
  return `${mins}:${secs}`;
};
</script>

<style scoped>
.drag-over {
  background: rgba(0, 123, 255, 0.08);
}
.dragging-row {
  opacity: 0.6;
}
.drag-handle {
  cursor: grab;
  display: inline-block;
  padding: 0 6px;
}
.drag-handle:active { cursor: grabbing }
.drag-handle-placeholder { display:inline-block; width:1.5rem }

/* hide number input spinners */
input[type=number]::-webkit-outer-spin-button,
input[type=number]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
input[type=number] { -moz-appearance: textfield }
</style>
