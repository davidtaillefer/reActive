<template>
    <BCard title="Equipment" class="shadow-sm">

        <BFormGroup label="Sport">
            <BFormSelect v-model="selectedSportId" :options="sportOptions" @change="loadEquipment" />
        </BFormGroup>

        <BListGroup v-if="equipment.length">
                <BListGroupItem v-for="item in equipment" :key="item.equipmentId" button @click="goToDetail(item.equipmentId)"
                    class="d-flex align-items-center">
                    <!-- Thumbnail -->
                    <img v-if="item.photo" :src="thumbUrl(item.photo)" class="me-3 rounded"
                        style="width: 50px; height: 50px; object-fit: cover;" />

                    <!-- Fallback icon -->
                    <div v-else class="me-3 bg-light d-flex align-items-center justify-content-center rounded"
                        style="width: 50px; height: 50px;">
                        🛠
                    </div>

                    <!-- Name -->
                    <div>
                        {{ item.name }}
                    </div>
                </BListGroupItem>
        </BListGroup>

        <div v-else class="text-muted">No equipment found.</div>

        <BButton class="mt-3" variant="primary" @click="goToCreate">
            Add Equipment
        </BButton>

    </BCard>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { getSports, getEquipmentBySport } from '@/api/equipment';

const router = useRouter();

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

const sports = ref([]);
const selectedSportId = ref(null);
const equipment = ref([]);


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
};

onMounted(async () => {
    sports.value = await getSports();

    if (sports.value.length) {
        selectedSportId.value = sports.value[0].id;
        await loadEquipment();
    }
});

const goToDetail = (id) => {
    router.push(`/equipment/${id}`);
};

const goToCreate = () => {
    router.push('/equipment/new');
};
</script>