<template>
    <div class="h-100 bg-light overflow-auto">
        <BContainer fluid class="py-4 px-4 h-100">
            <BCard class="shadow-sm h-100 d-flex flex-column">
                <BCardBody class="p-4 d-flex flex-column overflow-hidden">
                    <div class="d-flex align-items-center justify-content-between mb-4">
                        <div class="d-flex align-items-center gap-3">
                            <h3 class="mb-0">Equipment</h3>
                        </div>
                    </div>

                    <BRow class="g-3 flex-fill overflow-hidden">
                        <!-- Left: selectors + list -->
                        <BCol cols="12" md="4" lg="3">
                            <div class="d-flex flex-column gap-3 h-100 overflow-auto">
                                <BCard class="p-3">
                                    <BFormGroup label="Sport">
                                        <BFormSelect v-model="selectedSportId" :options="sportOptions" @change="loadEquipment" size="sm" />
                                    </BFormGroup>

                                    <BListGroup v-if="equipment.length" class="mt-2">
                                        <BListGroupItem v-for="item in equipment" :key="item.equipmentId" button @click="selectEquipment(item.equipmentId)"
                                            :active="item.equipmentId === selectedEquipmentId" class="d-flex align-items-center">
                                            <img v-if="item.photo" :src="thumbUrl(item.photo)" class="me-3 rounded"
                                                style="width: 50px; height: 50px; object-fit: cover;" />

                                            <div v-else class="me-3 bg-light d-flex align-items-center justify-content-center rounded"
                                                style="width: 50px; height: 50px;">
                                                🛠
                                            </div>

                                            <div>
                                                {{ item.name }}
                                            </div>
                                        </BListGroupItem>
                                    </BListGroup>

                                    <div v-else class="text-muted">No equipment found.</div>

                                    <BButton class="mt-3" variant="primary" @click="goToCreate" size="sm">
                                        Add Equipment
                                    </BButton>
                                </BCard>
                            </div>
                        </BCol>

                        <!-- Right: detail -->
                        <BCol cols="12" md="8" lg="9" class="d-flex flex-column">
                            <BCardBody class="p-0 position-relative flex-fill d-flex flex-column">
                                <EquipmentDetailCard v-if="selectedEquipmentId" :equipmentId="selectedEquipmentId" key="detail-" />
                                <div v-else class="p-4 text-muted">Select equipment to view details.</div>
                            </BCardBody>
                        </BCol>
                    </BRow>
                </BCardBody>
            </BCard>
        </BContainer>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { getSports, getEquipmentBySport } from '@/api/equipment';
import EquipmentDetailCard from '@/components/ui/EquipmentDetailCard.vue';

const router = useRouter();

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

const sports = ref([]);
const selectedSportId = ref(null);
const equipment = ref([]);
const selectedEquipmentId = ref(null);


const thumbUrl = (photo) =>
    photo
        ? `${apiBaseUrl}/images/equipment/thumbs/${photo}`
        : null;

const sportOptions = computed(() =>
    sports.value.map(s => ({
        value: s.id,
        text: s.name
    }))
);

const loadEquipment = async () => {
    if (!selectedSportId.value) return;
    equipment.value = await getEquipmentBySport(selectedSportId.value);
    if (equipment.value && equipment.value.length) {
        selectedEquipmentId.value = equipment.value[0].equipmentId;
    } else {
        selectedEquipmentId.value = null;
    }
};

onMounted(async () => {
    sports.value = await getSports();

    if (sports.value.length) {
        selectedSportId.value = sports.value[0].id;
        await loadEquipment();
    }
});

const selectEquipment = (id) => {
    selectedEquipmentId.value = id;
};

const goToDetail = (id) => {
    router.push(`/equipment/${id}`);
};

const goToCreate = () => {
    router.push('/equipment/new');
};
</script>