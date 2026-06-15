<template>
    <BCard class="shadow-sm">

        <h4>{{ isEdit ? 'Edit Equipment' : 'New Equipment' }}</h4>

        <BForm @submit.prevent="save">

            <!-- Sport Select -->
            <BFormGroup label="Sport" class="mb-3">
                <BFormSelect v-model.number="form.sportid" :options="sportOptions" @change="clearError('sportid')"
                    :state="errors.sportid ? false : null" />
                <BFormInvalidFeedback v-if="errors.sportid">
                    {{ errors.sportid }}
                </BFormInvalidFeedback>
            </BFormGroup>

            <BFormInput v-model="form.name" placeholder="Name" @input="clearError('name')"
                :state="errors.name ? false : null" />

            <BFormInvalidFeedback v-if="errors.name">
                {{ errors.name }}
            </BFormInvalidFeedback>
            <BFormInput v-model="form.brand" placeholder="Brand" class="mb-2" />
            <BFormInput v-model="form.model" placeholder="Model" class="mb-2" />
            <BFormInput v-model="form.year" type="number" placeholder="Year" :state="errors.year ? false : null" />

            <BFormInvalidFeedback v-if="errors.year">
                {{ errors.year }}
            </BFormInvalidFeedback>
            <BFormInput v-model="form.life_span" type="number" placeholder="Life span (km)"
                :state="errors.life_span ? false : null" />

            <BFormInvalidFeedback v-if="errors.life_span">
                {{ errors.life_span }}
            </BFormInvalidFeedback>
            <BFormTextarea v-model="form.maintenance_notes" placeholder="Maintenance notes" class="mb-3" />

            <!-- Photo Upload -->
            <BFormFile v-model="photoFile" @change="onPhotoChange" />
            <BFormInvalidFeedback v-if="errors.photo">
                {{ errors.photo }}
            </BFormInvalidFeedback>

            <!-- Preview -->
            <div v-if="previewUrl" class="mb-2">
                <img :src="previewUrl" class="img-fluid rounded" style="max-height:200px;" />

                <div class="mt-2">
                    <BButton size="sm" variant="outline-danger" @click="markRemovePhoto">
                        Remove Photo
                    </BButton>
                </div>
            </div>
            <div class="drop-zone" @dragover.prevent @drop.prevent="onDrop">
                <p>Drag & drop photo here or click to upload</p>

                <input type="file" @change="onFileSelect" hidden ref="fileInput" />

                <BButton size="sm" @click="$refs.fileInput.click()">
                    Choose File
                </BButton>
            </div>
            <BAlert v-if="Object.keys(errors).length" variant="danger">
                <ul class="mb-0">
                    <li v-for="(msg, field) in errors" :key="field">
                        {{ field }}: {{ msg }}
                    </li>
                </ul>
            </BAlert>

            <BButton type="submit" variant="success" :disabled="!isValid">
                Save
            </BButton>

        </BForm>

    </BCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
    getEquipmentById,
    createEquipment,
    updateEquipment,
    getSports
} from '@/api/equipment';

const route = useRoute();
const router = useRouter();

const form = ref({
    sportid: null,
    name: '',
    brand: '',
    model: '',
    year: null,
    life_span: null,
    maintenance_notes: ''
});

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

const photoFile = ref(null);
const previewUrl = ref(null);
const removePhoto = ref(false);
const errors = ref({});
const sports = ref([]);
const loadingSports = ref(true);

const isEdit = computed(() => !!route.params.id);

const sportOptions = computed(() => [
    { value: null, text: 'Select a sport...' },
    ...sports.value.map(sport => ({
        value: sport.id,
        text: sport.name
    }))
]);

onMounted(async () => {
    // Load sports
    try {
        sports.value = await getSports();
    } catch (err) {
        console.error('Error loading sports:', err);
    } finally {
        loadingSports.value = false;
    }

    // Load equipment if editing
    if (isEdit.value) {
        const data = await getEquipmentById(route.params.id);
        form.value = {
            sportid: data.sportid,
            name: data.name,
            brand: data.brand,
            model: data.model,
            year: data.year,
            life_span: data.life_span,
            maintenance_notes: data.maintenance_notes
        };

        if (data.photo) {
            previewUrl.value = `${apiBaseUrl}/images/equipment/${data.photo}`;
        }
    }
});

const save = async () => {
    errors.value = {}; // reset

    const fd = new FormData();

    Object.entries(form.value).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
            fd.append(key, value);
        }
    });

    // Replace photo
    if (photoFile.value) {
        fd.append('photo', photoFile.value);
    }

    // Explicit remove
    if (removePhoto.value) {
        fd.append('remove_photo', '1');
    }
    if (photoFile.value) {
        fd.append('photo', photoFile.value);
    }

    try {
        let res;

        if (isEdit.value) {
            res = await updateEquipment(route.params.id, fd);
        } else {
            res = await createEquipment(fd);
        }

        if (!res.ok) {
            const data = await res.json();
            if (data.errors) {
                errors.value = data.errors;
                return; // stop navigation
            }
            throw new Error('Unknown error');
        }

        router.push('/equipment');

    } catch (err) {
        console.error(err);
    }
};

const clearError = (field) => {
    if (errors.value[field]) {
        delete errors.value[field];
    }
};

const isValid = computed(() => {
    return (
        form.value.name?.trim().length > 0 &&
        Number.isFinite(form.value.sportid) &&
        (!form.value.year || form.value.year >= 1900) &&
        Object.keys(errors.value).length === 0
    );
});

const onSportChange = (val) => {
    form.value.sportid = val ? Number(val) : null;
    clearError('sportid');
};

const onPhotoChange = (file) => {
    if (file) {
        previewUrl.value = URL.createObjectURL(file);
        removePhoto.value = false; // replacing overrides removal
    }
};

const markRemovePhoto = () => {
    photoFile.value = null;
    previewUrl.value = null;
    removePhoto.value = true;
};

const handleFile = (file) => {
    if (!file) return;

    photoFile.value = file;
    previewUrl.value = URL.createObjectURL(file);
};

const onDrop = (e) => {
    const file = e.dataTransfer.files[0];
    handleFile(file);
};

const onFileSelect = (e) => {
    const file = e.target.files[0];
    handleFile(file);
};
</script>

<style scoped>
.drop-zone {
    border: 2px dashed #ccc;
    padding: 20px;
    text-align: centre;
    border-radius: 8px;
    cursor: pointer;
}

.drop-zone:hover {
    background: #f8f9fa;
}
</style>