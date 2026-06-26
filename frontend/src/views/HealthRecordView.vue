<template>
    <div class="h-100 bg-light overflow-auto">
        <BContainer fluid class="py-4 px-4 h-100">
            <BCard class="shadow-sm h-100 d-flex flex-column">
                <BCardBody class="p-4 d-flex flex-column overflow-hidden">
                    <div class="d-flex align-items-center justify-content-between mb-4">
                        <div class="d-flex align-items-center gap-3">
                            <h3 class="mb-0">Health Records</h3>
                        </div>
                        <div>
                            <BButton variant="primary" @click="creating = true">New Health Record</BButton>
                        </div>
                    </div>

                    <BRow class="g-3 flex-fill overflow-hidden">
                        <BCol cols="12" md="4" lg="3">
                            <div class="d-flex flex-column gap-3 h-100 overflow-auto">
                                <BCard class="p-3">
                                    <BListGroup v-if="records.length" class="mt-2">
                                        <BListGroupItem v-for="item in records" :key="item.id" button
                                            @click="selectRecord(item)" :active="selectedId === item.id"
                                            class="d-flex align-items-center justify-content-between">
                                            <div>
                                                <div class="fw-bold">{{ formatDate(item.date) }}</div>
                                                <div class="text-muted small">{{ item.provider }}</div>
                                            </div>
                                        </BListGroupItem>
                                    </BListGroup>

                                    <div v-else class="text-muted">No health records found.</div>
                                </BCard>
                            </div>
                        </BCol>

                        <BCol cols="12" md="8" lg="9" class="d-flex flex-column">
                            <BCardBody class="p-0 position-relative flex-fill d-flex flex-column">
                                <div v-if="creating" class="p-3">
                                    <BCard class="mb-3">
                                        <BCardBody>
                                            <form @submit.prevent="createRecord">
                                                <div class="mb-2">
                                                    <label class="form-label">Date</label>
                                                    <input class="form-control" type="date" v-model="form.date"
                                                        required />
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Type</label>
                                                    <BFormSelect v-model="form.type" :options="typeOptions" />
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Provider</label>
                                                    <input class="form-control" type="text" v-model="form.provider" />
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Description</label>
                                                    <textarea class="form-control"
                                                        v-model="form.description"></textarea>
                                                </div>
                                                <div class="mb-2">
                                                    <label class="form-label">Data (JSON or text)</label>
                                                    <textarea class="form-control monospace"
                                                        v-model="form.data"></textarea>
                                                </div>
                                                <div class="d-flex gap-2">
                                                    <BButton type="submit" variant="success">Save</BButton>
                                                    <BButton type="button" variant="secondary" @click="cancelCreate">
                                                        Cancel</BButton>
                                                </div>
                                            </form>
                                        </BCardBody>
                                    </BCard>
                                </div>

                                <BRow>
                                    <BCol cols="12" md="8">
                                        <div v-if="!selectedRecord" class="text-muted">Select a health record to
                                            view details.</div>
                                        <div v-else>
<div v-if="!creating">
                                            <BCard class=mb-3>
                                                <BCardBody>
                                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                                        <h4 class="mb-0">Record: {{ formatDate(selectedRecord.date) }}
                                                        </h4>
                                                        <div>
                                                            <BButton size="sm" variant="outline-primary" class="me-2"
                                                                @click="startEdit">Edit</BButton>
                                                            <BButton size="sm" variant="danger" @click="confirmDelete">
                                                                Delete</BButton>
                                                        </div>
                                                    </div>

                                                    <div v-if="editing">
                                                        <BCard class="mb-3">
                                                            <BCardBody>
                                                                <form @submit.prevent="updateRecord">
                                                                    <div class="mb-2">
                                                                        <label class="form-label">Date</label>
                                                                        <input class="form-control" type="date"
                                                                            v-model="editForm.date" required />
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <label class="form-label">Type</label>
                                                                        <BFormSelect v-model="editForm.type"
                                                                            :options="typeOptions" />
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <label class="form-label">Provider</label>
                                                                        <input class="form-control" type="text"
                                                                            v-model="editForm.provider" />
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <label class="form-label">Description</label>
                                                                        <textarea class="form-control"
                                                                            v-model="editForm.description"></textarea>
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <label class="form-label">Data (JSON or
                                                                            text)</label>
                                                                        <textarea class="form-control monospace"
                                                                            v-model="editForm.data"></textarea>
                                                                    </div>
                                                                    <div class="d-flex gap-2">
                                                                        <BButton type="submit" variant="success"
                                                                            size="sm">Save</BButton>
                                                                        <BButton type="button" variant="secondary"
                                                                            size="sm" @click="cancelEdit">Cancel
                                                                        </BButton>
                                                                    </div>
                                                                </form>
                                                            </BCardBody>
                                                        </BCard>
                                                    </div>

                                                    <div v-if="!editing">
                                                        <p><strong>Type:</strong> {{ selectedRecord.type }}</p>
                                                        <p><strong>Provider:</strong> {{ selectedRecord.provider }}</p>
                                                        <p><strong>Description:</strong> {{ selectedRecord.description
                                                            }}</p>
                                                        <div v-if="selectedRecord.data">
                                                            <pre
                                                                style="white-space:pre-wrap">{{ selectedRecord.data }}</pre>
                                                        </div>

                                                    </div>
                                                </BCardBody>
                                            </BCard>

                                            <div class="mt-3">
                                                <BCard>
                                                    <BCardBody>
                                                <h5>Document viewer</h5>
                                                <div v-if="!selectedDocument" class="text-muted">Select a document to
                                                    view below.</div>
                                                <div v-else class="mt-2">
                                                    <template v-if="isPdf(selectedDocument.filename)">
                                                        <iframe :src="docFileUrl(selectedDocument)"
                                                            style="width:100%;height:600px;border:0"></iframe>
                                                    </template>
                                                    <template v-else-if="isImage(selectedDocument.filename)">
                                                        <img :src="docFileUrl(selectedDocument)"
                                                            style="max-width:100%;height:auto" />
                                                    </template>
                                                    <template v-else>
                                                        <div>
                                                            <p>Cannot preview this file type in-browser.</p>
                                                            <a :href="docFileUrl(selectedDocument)" target="_blank"
                                                                rel="noopener">Download</a>
                                                        </div>
                                                    </template>
                                                </div>
                                                    </BCardBody>
                                                </BCard>
                                            </div>
                                            </div>
                                        </div>
                                    </BCol>

                                    <BCol cols="12" md="4">
                                        <div v-if="!creating">
                                        <BCard class="p-3">
                                            <h6>Documents</h6>
                                            <div class="mb-2">
                                                <div class="upload-zone" :class="{ 'drag-active': dragActive }"
                                                    @dragenter.prevent="handleDrag" @dragleave.prevent="handleDrag"
                                                    @dragover.prevent="handleDrag" @drop.prevent="handleDrop">
                                                    <i class="bi bi-upload"
                                                        :class="dragActive ? 'text-primary' : 'text-muted'"
                                                        style="font-size: 2rem;" />
                                                    <p class="mt-2 mb-1">Drag & drop a document here, or</p>
                                                    <label class="btn btn-primary mb-0">
                                                        Browse Files
                                                        <input type="file" class="d-none" @change="onFileSelected"
                                                            :disabled="!selectedRecord || uploadInProgress"
                                                            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" />
                                                    </label>
                                                </div>
                                            </div>

                                            <BListGroup v-if="documents.length" class="mt-2">
                                                <BListGroupItem v-for="doc in documents" :key="doc.id" button
                                                    @click="viewDocument(doc)"
                                                    :active="selectedDocument && selectedDocument.id === doc.id">
                                                    <div class="d-flex flex-column">
                                                        <div class="fw-bold small text-truncate">{{ doc.filename }}
                                                        </div>
                                                        <div class="small text-muted">{{ formatDate(doc.created_at) }}
                                                        </div>
                                                    </div>
                                                </BListGroupItem>
                                            </BListGroup>
                                            <div v-else class="text-muted small mt-2">No documents attached.</div>
                                        </BCard>
                                        </div>
                                    </BCol>
                                </BRow>
                            </BCardBody>
                        </BCol>
                    </BRow>
                </BCardBody>
            </BCard>
        </BContainer>
    </div>

    <BModal v-model="showDeleteModal" title="Confirm Delete">
        <p>Delete this health record? This cannot be undone.</p>
        <template #footer>
            <BButton variant="secondary" @click="showDeleteModal = false">Cancel</BButton>
            <BButton variant="danger" @click="doDelete">Delete</BButton>
        </template>
    </BModal>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BContainer, BCard, BCardBody, BButton, BListGroup, BListGroupItem, BRow, BCol, BFormSelect, BModal } from 'bootstrap-vue-next'

const route = useRoute()
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const records = ref([] as any[])
const selectedRecord = ref(null as any)
const selectedId = ref(null as any)
const creating = ref(false)
const router = useRouter()

const form = ref({ date: '', type: 'doctor', provider: '', description: '', data: '' })

const typeOptions = [
    { value: 'doctor', text: 'doctor' },
    { value: 'diagnostics', text: 'diagnostics' },
    { value: 'treatment', text: 'treatment' },
    { value: 'injury', text: 'injury' },
    { value: 'vaccination', text: 'vaccination' }
]

const documents = ref([] as any[])
const selectedDocument = ref(null as any)
const uploadFile = ref<File | null>(null)
const uploadInProgress = ref(false)

const dragActive = ref(false)

const handleDrag = (e: any) => {
    // toggle drag-active state depending on event type
    if (e.type === 'dragenter' || e.type === 'dragover') {
        dragActive.value = true
    } else if (e.type === 'dragleave') {
        dragActive.value = false
    }
}

const handleDrop = (e: any) => {
    dragActive.value = false
    const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]
    uploadFile.value = f || null
    if (f && selectedRecord.value) {
        // kick off immediate upload
        uploadDocument()
    }
}

const docFileUrl = (doc) => `${apiBaseUrl}health_documents/file/${doc.id}`

const loadDocuments = async (healthRecordId) => {
    try {
        const res = await fetch(`${apiBaseUrl}health_documents/${healthRecordId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const all = await res.json()
        documents.value = all
        selectedDocument.value = null
    } catch (err) {
        console.error('Failed to load documents', err)
        documents.value = []
    }
}

const viewDocument = (doc) => {
    selectedDocument.value = doc
}

const onFileSelected = (ev) => {
    const f = ev.target.files && ev.target.files[0]
    uploadFile.value = f || null
    if (f && selectedRecord.value) {
        // immediately upload when the user picks a file
        uploadDocument()
    }
}

const uploadDocument = async () => {
    if (!selectedRecord.value || !uploadFile.value) return
    uploadInProgress.value = true
    try {
        const fd = new FormData()
        fd.append('file', uploadFile.value, uploadFile.value.name)

        const res = await fetch(`${apiBaseUrl}health_documents/${selectedRecord.value.id}`, {
            method: 'POST',
            body: fd
        })

        if (!res.ok) {
            const txt = await res.text()
            throw new Error(`HTTP ${res.status}: ${txt}`)
        }

        // refresh documents
        uploadFile.value = null
        await loadDocuments(selectedRecord.value.id)
    } catch (err) {
        console.error('Failed to upload document', err)
        alert('Failed to upload document: ' + err.message)
    } finally {
        uploadInProgress.value = false
    }
}

const showDeleteModal = ref(false)

const confirmDelete = () => {
    showDeleteModal.value = true
}

const doDelete = async () => {
    if (!selectedRecord.value) return
    try {
        const res = await fetch(`${apiBaseUrl}health_records/${selectedRecord.value.id}`, { method: 'DELETE' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        showDeleteModal.value = false
        selectedDocument.value = null
        selectedRecord.value = null
        selectedId.value = null
        await loadRecords()
    } catch (err) {
        console.error('Failed to delete health record', err)
        alert('Failed to delete record: ' + err.message)
    }
}

// Editing selected record
const editing = ref(false)
const editForm = ref({ date: '', type: 'doctor', provider: '', description: '', data: '' })

const startEdit = () => {
    if (!selectedRecord.value) return
    editing.value = true
    // populate edit form from selectedRecord
    const r = selectedRecord.value
    // Ensure date input is YYYY-MM-DD
    const d = new Date(r.date)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    editForm.value = {
        date: `${y}-${m}-${day}`,
        type: r.type || 'doctor',
        provider: r.provider || '',
        description: r.description || '',
        data: r.data || ''
    }
    // clear any open document preview
    selectedDocument.value = null
}

const cancelEdit = () => {
    editing.value = false
}

const updateRecord = async () => {
    if (!selectedRecord.value) return
    try {
        const payload = {
            date: editForm.value.date,
            type: editForm.value.type,
            provider: editForm.value.provider,
            description: editForm.value.description,
            data: editForm.value.data
        }

        const res = await fetch(`${apiBaseUrl}health_records/${selectedRecord.value.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            const text = await res.text()
            throw new Error(`HTTP ${res.status}: ${text}`)
        }

        editing.value = false
        // Refresh list and re-select updated record
        await loadRecords()
        const updated = records.value.find(r => r.id === selectedRecord.value.id)
        if (updated) selectRecord(updated)
    } catch (err) {
        console.error('Failed to update health record', err)
        alert('Failed to update record: ' + err.message)
    }
}

const isPdf = (filename) => {
    if (!filename) return false
    return filename.toLowerCase().endsWith('.pdf')
}

const isImage = (filename) => {
    if (!filename) return false
    const ext = filename.split('.').pop().toLowerCase()
    return ['jpg', 'jpeg', 'png', 'gif'].includes(ext)
}

const cancelCreate = () => {
    creating.value = false
    form.value = { date: '', type: '', provider: '', description: '', data: '' }
}

const loadRecords = async () => {
    try {
        const res = await fetch(`${apiBaseUrl}health_records`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const all = await res.json()
        // API already returns desc order; ensure parsed dates
        records.value = all.map(r => ({ ...r }))
        if (records.value.length && !selectedRecord.value) {
            selectRecord(records.value[0])
        }
    } catch (err) {
        console.error('Failed to load health records list', err)
    }
}

const selectRecord = (item: any) => {
    // Clear any open document preview immediately when switching records
    selectedDocument.value = null
    selectedRecord.value = item
    selectedId.value = item.id
    // update route for deep-linking
    router.replace({ name: 'health', params: { id: item.id } }).catch(() => { })
    // load attached documents for this health record
    loadDocuments(item.id)
}

// Clear selected document when navigating away or when the route id changes
watch(() => route.name, (newName) => {
    if (newName !== 'health') {
        selectedDocument.value = null
    }
})

watch(() => route.params.id, (newId, oldId) => {
    if (!newId || newId !== String(selectedId.value)) {
        selectedDocument.value = null
    }
})

const createRecord = async () => {
    try {
        const payload = {
            date: form.value.date,
            type: form.value.type,
            provider: form.value.provider,
            description: form.value.description,
            data: form.value.data
        }

        const res = await fetch(`${apiBaseUrl}health_records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            const text = await res.text()
            throw new Error(`HTTP ${res.status}: ${text}`)
        }

        // Refresh list and select latest
        creating.value = false
        form.value = { date: '', type: '', provider: '', description: '', data: '' }
        await loadRecords()
    } catch (err) {
        console.error('Failed to create health record', err)
        alert('Failed to create record: ' + err.message)
    }
}

const id = route.params.id

onMounted(async () => {
    await loadRecords()
    // If route has id, try to select it
    if (id) {
        try {
            const res = await fetch(`${apiBaseUrl}health_records/${id}`)
            if (res.ok) {
                const r = await res.json()
                selectRecord(r)
            }
        } catch (err) {
            console.error('Failed to load health record by id', err)
        }
    }
})

const formatDate = (d) => {
    if (!d) return ''
    try {
        const dt = new Date(d)
        return dt.toLocaleDateString()
    } catch (e) { return d }
}
</script>
