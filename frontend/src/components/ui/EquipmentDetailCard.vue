<template>
    <BCard v-if="equipment" class="shadow-sm">

        <div class="d-flex justify-content-between align-items-center">
            <h4>{{ equipment.name }}</h4>

            <div>
                <BButton size="sm" class="me-2" @click="goToEdit">
                    Edit
                </BButton>

                <BButton size="sm" variant="secondary" class="me-2" @click="goToAddMaintenance">
                    Add Maintenance
                </BButton>

                <BButton size="sm" variant="danger" @click="confirmDelete">
                    Delete
                </BButton>
            </div>
        </div>
        <BRow class="mt-3">
            <BCol cols="4" v-if="equipment.photo">
                <img :src="photoUrl" class="img-fluid rounded" />
            </BCol>
            <BCol>
                <p><strong>Brand:</strong> {{ equipment.brand || '—' }}</p>
                <p><strong>Model:</strong> {{ equipment.model || '—' }}</p>
                <p><strong>Year:</strong> {{ equipment.year || '—' }}</p>
                <p><strong>Life span:</strong> {{ equipment.life_span || '—' }} km</p>
                <p><strong>Maintenance notes:</strong><br />{{ equipment.maintenance_notes || '—' }}</p>
            </BCol>
        </BRow>
        <div class="mt-4">
            <label class="form-label">Usage</label>

        </div>
        <BProgress :value="progressPercent" height="24px" :variant="progressVariant">
            <BProgressBar :value="progressPercent" :variant="progressVariant" animated>
                {{ usageLabel }} ({{ Math.round(progressPercent) }}%)
            </BProgressBar>
        </BProgress>
        <h5 class="mt-4">Maintenance History</h5>

        <BTable :items="maintenanceHistory" :fields="fields" small responsive>

            <!-- Date -->
            <template #cell(date)="data">
                <div v-if="editingId === data.item.id">
                    <BFormInput v-model="editRow.date" type="date" :state="editErrors.date ? false : null"
                        @input="clearEditError('date')" />
                    <BFormInvalidFeedback v-if="editErrors.date">
                        {{ editErrors.date }}
                    </BFormInvalidFeedback>
                </div>
                <div v-else>
                    {{ data.item.date }}
                </div>
            </template>

            <!-- Distance -->
            <template #cell(distance)="data">
                <div v-if="editingId === data.item.id">
                    <BFormInput v-model.number="editRow.distance" type="number"
                        :state="editErrors.distance ? false : null" @input="clearEditError('distance')" />
                    <BFormInvalidFeedback v-if="editErrors.distance">
                        {{ editErrors.distance }}
                    </BFormInvalidFeedback>
                </div>
                <div v-else>
                    {{ data.item.distance || '—' }}
                </div>
            </template>

            <!-- Type -->
            <template #cell(type)="data">
                <div v-if="editingId === data.item.id">
                    <BFormSelect v-model="editRow.type" :options="typeOptions" :state="editErrors.type ? false : null"
                        @change="clearEditError('type')" />
                    <BFormInvalidFeedback v-if="editErrors.type">
                        {{ editErrors.type }}
                    </BFormInvalidFeedback>
                </div>
                <div v-else>
                    {{ data.item.type || '—' }}
                </div>
            </template>

            <!-- Shop -->
            <template #cell(shop)="data">
                <div v-if="editingId === data.item.id">
                    <BFormInput v-model="editRow.shop" :state="editErrors.shop ? false : null"
                        @input="clearEditError('shop')" />
                    <BFormInvalidFeedback v-if="editErrors.shop">
                        {{ editErrors.shop }}
                    </BFormInvalidFeedback>
                </div>
                <div v-else>
                    {{ data.item.shop || '—' }}
                </div>
            </template>

            <!-- Notes -->
            <template #cell(notes)="data">
                <div v-if="editingId === data.item.id">
                    <BFormInput v-model="editRow.notes" :state="editErrors.notes ? false : null"
                        @input="clearEditError('notes')" />
                    <BFormInvalidFeedback v-if="editErrors.notes">
                        {{ editErrors.notes }}
                    </BFormInvalidFeedback>
                </div>
                <div v-else>
                    {{ data.item.notes || '—' }}
                </div>
            </template>

            <!-- Actions -->
            <template #cell(actions)="data">
                <div v-if="editingId === data.item.id">
                    <BButton size="sm" variant="success" @click="saveEdit(data.item.id)" :disabled="!isEditValid">
                        💾
                    </BButton>
                    <BButton size="sm" variant="secondary" @click="cancelEdit">❌</BButton>
                </div>
                <div v-else>
                    <BButton size="sm" variant="outline-primary" @click="startEdit(data.item)">✏️</BButton>
                    <BButton size="sm" variant="outline-danger" @click="deleteMaintenanceRecord(data.item.id)">🗑
                    </BButton>
                </div>
            </template>

        </BTable>
        <!-- Maintenance addition moved to EquipmentEditView -->
        <BModal v-model="showDeleteModal" title="Confirm Delete">
            <p>
                Delete <strong>{{ equipment.name }}</strong>?<br />
                This cannot be undone.
            </p>

            <template #footer>
                <BButton variant="secondary" @click="showDeleteModal = false">
                    Cancel
                </BButton>
                <BButton variant="danger" @click="doDelete">
                    Delete
                </BButton>
            </template>
        </BModal>
    </BCard>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getEquipmentById, deleteEquipment, getTotalDistance, getMaintenance, updateMaintenance, deleteMaintenance } from '@/api/equipment';

const props = defineProps({ equipmentId: { type: [String, Number], default: null } });

const route = useRoute();
const router = useRouter();

const equipment = ref(null);
const currentUsage = ref(0);
const maintenanceHistory = ref([]);

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

const currentId = computed(() => props.equipmentId ?? route.params.id);

const fields = [
    { key: 'date', label: 'Date' },
    { key: 'distance', label: 'Km' },
    { key: 'type', label: 'Type' },
    { key: 'shop', label: 'Shop' },
    { key: 'notes', label: 'Notes' },
    { key: 'actions', label: '' }
];

const editErrors = ref({});

const photoUrl = computed(() =>
    equipment.value?.photo
        ? `${apiBaseUrl}/images/equipment/${equipment.value.photo}`
        : null
);

const progressPercent = computed(() => {
    if (!equipment.value?.life_span) return 0;
    return Math.min(
        (currentUsage.value / equipment.value.life_span) * 100,
        100
    );
});

const loadDetails = async (id) => {
    if (!id) return;
    equipment.value = await getEquipmentById(id);
    currentUsage.value = await getTotalDistance(id) || 0;
    maintenanceHistory.value = await getMaintenance(id) || [];
};

onMounted(async () => {
    if (currentId.value) await loadDetails(currentId.value);
    console.log('Equipment Record Returned: ', equipment.value)
});

watch(() => props.equipmentId, async (val) => {
    if (val) await loadDetails(val);
}, { immediate: true });

watch(() => route.params.id, async (val) => {
    if (!props.equipmentId && val) await loadDetails(val);
});

const goToEdit = () => {
    if (!currentId.value) return;
    router.push(`/equipment/${currentId.value}/edit`);
};

const goToAddMaintenance = () => {
    if (!currentId.value) return;
    // navigate to edit view and scroll to maintenance section
    router.push({ path: `/equipment/${currentId.value}/edit`, hash: '#add-maintenance' });
};

const progressVariant = computed(() => {
    const p = progressPercent.value;

    if (p < 60) return 'success';
    if (p < 85) return 'warning';
    return 'danger';
});

const usageLabel = computed(() => {
    const used = Math.round(currentUsage.value);
    const total = Math.round(equipment.value?.life_span || 0);

    return `${used} / ${total} km`;
});

const typeOptions = [
    { value: null, text: 'Type' },
    { value: 'chain', text: 'Chain' },
    { value: 'tire', text: 'Tire' },
    { value: 'bar tape', text: 'Bar Tape' },
    { value: 'tune up', text: 'Tune Up' }
];

// Maintenance creation has been moved to the equipment edit view.

const editingId = ref(null);

const editRow = ref({
    date: '',
    distance: null,
    type: null,
    shop: '',
    notes: ''
});

const startEdit = (item) => {
    editingId.value = item.id;

    editRow.value = {
        date: item.date,
        distance: item.distance,
        type: item.type,
        shop: item.shop,
        notes: item.notes
    };
};

const cancelEdit = () => {
    editingId.value = null;
};

const saveEdit = async (id) => {
    if (!validateEdit()) return;

    await updateMaintenance(id, editRow.value);

    if (currentId.value) maintenanceHistory.value = await getMaintenance(currentId.value);

    editingId.value = null;
    editErrors.value = {};
};

const clearEditError = (field) => {
    if (editErrors.value[field]) {
        delete editErrors.value[field];
    }
};

const deleteMaintenanceRecord = async (id) => {
    if (!confirm('Delete this maintenance record?')) return;

    await deleteMaintenance(id);

    if (currentId.value) maintenanceHistory.value = await getMaintenance(currentId.value);
};

const validateEdit = () => {
    const errors = {};

    if (!editRow.value.date) {
        errors.date = 'Required';
    }

    if (!editRow.value.type) {
        errors.type = 'Required';
    }

    editErrors.value = errors;

    return Object.keys(errors).length === 0;
};

const isEditValid = computed(() => {
    return (
        editRow.value.date &&
        editRow.value.type &&
        Object.keys(editErrors.value).length === 0
    );
});

const showDeleteModal = ref(false);

const confirmDelete = () => {
    showDeleteModal.value = true;
};

const doDelete = async () => {
    try {
        if (!currentId.value) return;
        const res = await deleteEquipment(currentId.value);

        if (!res.ok) throw new Error();

        router.push('/equipment');
    } catch (err) {
        alert('Failed to delete equipment.');
        console.error(err);
    }
};

</script>
