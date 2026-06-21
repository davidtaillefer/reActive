<template>
  <div class="bg-light">

    <!-- Upload Section -->
    <div class="container py-4" style="max-width: 900px;">
      <div class="card shadow-sm">
        <div class="card-body p-4">

          <!-- Header -->
          <div class="d-flex align-items-center gap-3 mb-4">
            <IBiupload class="text-purple fs-4" />
            <h2 class="mb-0">Upload Activity</h2>
          </div>
          <div v-if="activities.length === 0">
          <!-- Formats -->
          <div class="row g-3 mt-3 mb-3">
            <div class="col-md-4">
              <button type="button" class="card bg-light text-center w-100 p-0 position-relative" @click="handleGarminSync"
                :disabled="isGarminSyncing" style="border: none;">
                <!-- Token status badge (upper-right) -->
                <div class="position-absolute top-0 end-0 p-2">
                  <span v-if="tokenStatus.has_tokens" class="badge bg-success">Connected</span>
                  <span v-else-if="tokenStatus.has_env_credentials" class="badge bg-warning text-dark">Env Creds</span>
                  <span v-else class="badge bg-secondary">No Creds</span>
                </div>
                <div class="card-body">
                  <div v-if="isGarminSyncing" class="spinner-border spinner-border-sm mb-2" />
                  <img v-else :src="GarminLogo" width="96" height="96" class="mb-2" alt="Garmin logo" />
                  <div class="d-flex align-items-center justify-content-center">
                    <h6 class="mt-2 mb-1">Garmin Connect Sync</h6>
                  </div>
                  <div class="mt-2 text-center">
                    <button class="btn btn-sm btn-outline-secondary" @click.stop.prevent="showLogoutConfirm = true">Logout / Clear Tokens</button>
                  </div>
                </div>
              </button>
            </div>

            <!-- Credential / MFA Modals -->
            <BModal v-model="showCredentialsModal" title="Garmin Connect Login">
              <div class="mb-3">
                <label class="form-label">Email</label>
                <input v-model="credEmail" class="form-control" placeholder="you@example.com" />
              </div>
              <div class="mb-3">
                <label class="form-label">Password</label>
                <input v-model="credPassword" type="password" class="form-control" />
              </div>
              <template #footer>
                <BButton variant="secondary" @click="showCredentialsModal = false">Cancel</BButton>
                <BButton variant="primary" @click="submitCredentials" :disabled="credSubmitting">
                  <span v-if="credSubmitting" class="spinner-border spinner-border-sm"></span>
                  <span v-else>Submit</span>
                </BButton>
              </template>
            </BModal>

            <BModal v-model="showMfaModal" title="Multi-Factor Authentication">
              <div class="mb-3">
                <label class="form-label">Enter code</label>
                <input v-model="mfaCode" class="form-control" placeholder="123456" />
              </div>
              <template #footer>
                <BButton variant="secondary" @click="showMfaModal = false">Cancel</BButton>
                <BButton variant="primary" @click="submitMfa" :disabled="mfaSubmitting">
                  <span v-if="mfaSubmitting" class="spinner-border spinner-border-sm"></span>
                  <span v-else>Submit Code</span>
                </BButton>
              </template>
            </BModal>

            <BModal v-model="showLogoutConfirm" title="Confirm Logout">
              <p>Clear stored Garmin tokens? This will require re-authentication to sync.</p>
              <template #footer>
                <BButton variant="secondary" @click="showLogoutConfirm = false">Cancel</BButton>
                <BButton variant="danger" @click="() => { showLogoutConfirm = false; handleGarminLogout(); }">Clear Tokens</BButton>
              </template>
            </BModal>
          </div>

          <!-- Upload UI -->


          <div class="upload-zone" :class="{ 'drag-active': dragActive }" @dragenter.prevent="handleDrag"
            @dragleave.prevent="handleDrag" @dragover.prevent="handleDrag" @drop.prevent="handleDrop">
            <i class="bi bi-upload" :class="dragActive ? 'text-primary' : 'text-muted'" style="font-size: 4rem;" />
            <h5 class="mt-3 mb-2">Drop your activity files here</h5>
            <p class="text-muted mb-3">Supports .gpx, .fit, .tcx files</p>

            <label class="btn btn-primary">
              Browse Files
              <input type="file" class="d-none" multiple accept=".gpx,.fit,.tcx" @change="handleFileInput" />
            </label>
          </div>

          <!-- Formats -->
          <div class="row g-3 mt-3">
            <FormatCard title=".GPX" text="GPS Exchange Format" colour="primary" />
            <FormatCard title=".FIT" text="Garmin Activity" colour="success" />
            <FormatCard title=".TCX" text="Training Center XML" colour="purple" />
          </div>

        </div>
      </div>
    </div>
  </div>

  <!-- Activities Editor -->
  <div v-if="activities.length > 0" class="container-fluid pb-4">

    <div class="card shadow-sm">
      <div class="card-body">

        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5>Edit Uploaded Activities</h5>

          <button class="btn btn-success d-flex align-items-center gap-2" @click="saveAllActivities"
            :disabled="isSaving || !isFormValid">
            <div v-if="isSaving" class="spinner-border spinner-border-sm" />
            <IBiCloudArrowUpFill v-else />
            {{ isSaving ? 'Saving...' : 'Save All to Database' }}
          </button>
        </div>

        <div v-for="(act, index) in activities" :key="index" class="card border-primary mb-3">
          <div class="card-header bg-primary text-white d-flex align-items-center gap-2">
            <input type="checkbox" v-model="act.checked" class="form-check-input" style="margin: 0;" />
            <span>File: {{ act.hrmfile }}</span>
          </div>

          <div class="card-body overflow-auto p-3">

            <div class="d-flex gap-3" style="min-width: 1200px;">
              <Field label="Name">
                <BFormInput v-model="act.name" size="sm" />
              </Field>

              <Field label="Date">
                <BFormInput v-model="act.date" size="sm" />
              </Field>

              <Field label="Sport">
                <BFormSelect v-model="act.sport" size="sm" @change="handleSportChange(act)">
                  <option :value="null">-- Select Sport --</option>
                  <option v-for="s in sports" :key="s.id" :value="s.id">
                    {{ s.name }}
                  </option>
                </BFormSelect>
              </Field>

              <Field label="Subsport">
                <BFormSelect v-model="act.subsport" size="sm" :disabled="!act.subsportOptions.length">
                  <option :value="null">-- Select Subsport --</option>
                  <option v-for="ss in act.subsportOptions" :key="ss.id" :value="ss.id">
                    {{ ss.name }}
                  </option>
                </BFormSelect>
              </Field>

              <Field label="Duration">
                <BFormInput type="text" size="sm"
                  :state="/^(\d{1,2}):(\d{1,2}):(\d{1,2})$/.test(secondsToHMS(act.duration))"
                  :value="secondsToHMS(act.duration)"
                  @blur="act.duration = hmsToSeconds($event.target.value, act.duration)" />
              </Field>

              <Field label="Intensity">
                <select v-model="act.intensity" class="form-select form-select-sm">
                  <option :value="null">-- Optional --</option>
                  <option :value="1">Recovery</option>
                  <option :value="2">Base</option>
                  <option :value="3">Tempo</option>
                  <option :value="5">Threshold</option>
                  <option :value="6">VO2 Max</option>
                  <option :value="7">Anaerobic</option>
                  <option :value="4">Sprint</option>
                </select>
              </Field>

              <Field label="Distance">
                <BFormInput type="number" step="0.01" size="sm" :value="metersToKm(act.distance)"
                  @blur="act.distance = kmToMeters($event.target.value, act.distance)" />
              </Field>

              <Field label="Speed">
                <BFormInput type="number" step="0.1" size="sm" :value="msToKmh(act.avgspeed)"
                  @blur="act.avgspeed = kmhToMs($event.target.value, act.avgspeed)" />
              </Field>

              <Field label="Latitude">
                <input type="number" v-model.number="act.latitude" class="form-control form-control-sm" />
              </Field>

              <Field label="Longitude">
                <input type="number" v-model.number="act.longitude" class="form-control form-control-sm" />
              </Field>

              <Field label="Equipment">
                <select v-model="act.equipment" class="form-select form-select-sm"
                  :disabled="!act.equipmentOptions.length">
                  <option :value="null">-- Select Equipment --</option>
                  <option v-for="e in act.equipmentOptions" :key="e.idk" :value="e.idk">
                    {{ e.name }}
                  </option>
                </select>
              </Field>

              <Field label="Avg HR">
                <input type="number" v-model.number="act.heartrate" class="form-control form-control-sm" />
              </Field>

              <Field label="Notes">
                <input type="number" v-model.number="act.comments" class="form-control form-control-sm" />
              </Field>

              <Field label="Ascent">
                <input type="number" v-model.number="act.ascent" class="form-control form-control-sm" />
              </Field>

              <Field label="Calories">
                <input type="number" v-model.number="act.calories" class="form-control form-control-sm" />
              </Field>

              <Field label="Cadence">
                <input type="number" v-model.number="act.avgcadence" class="form-control form-control-sm" />
              </Field>

              <Field label="Power">
                <input type="number" v-model.number="act.avgpower" class="form-control form-control-sm" />
              </Field>

              <Field label="Aerobic TE">
                <input type="number" v-model.number="act.ate" class="form-control form-control-sm" />
              </Field>

              <Field label="Anaerobic TE">
                <input type="number" v-model.number="act.ante" class="form-control form-control-sm" />
              </Field>

              <Field label="Load">
                <input type="number" v-model.number="act.training_load" class="form-control form-control-sm" />
              </Field>

              <Field label="Feel">
                <input type="number" v-model.number="act.workout_feel" class="form-control form-control-sm" />
              </Field>

              <Field label="RPE">
                <input type="number" v-model.number="act.workout_rpe" class="form-control form-control-sm" />
              </Field>

              <Field label="Device">
                <input type="number" v-model.number="act.device" class="form-control form-control-sm" />
              </Field>

              <Field label="Offset">
                <input type="number" v-model.number="act.tzoffset" class="form-control form-control-sm" />
              </Field>

            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Field from '@/components/ui/Field.vue'
import FormatCard from '@/components/ui/FormatCard.vue'
import GarminLogo from '@/assets/garmin_logo.svg'



const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const hrmData = ref([])
const dragActive = ref(false);
const uploadedFiles = ref<{ file: File, name: string, status: 'pending' | 'uploading' | 'success' | 'error' }[]>([]);
const activities = ref([]);
const sports = ref<any[]>([]);

onMounted(async () => {
  const res = await fetch(apiBaseUrl + 'sports');
  if (res.ok) sports.value = await res.json();
});

const createActivityTemplate = () => ({
  checked: true,
  hrmfile: '', name: '', date: '', sport: null, subsport: null, subsportOptions: [], duration: 0,
  intensity: null, distance: 0.0, avgspeed: 0.0, latitude: 0.0, longitude: 0.0,
  secondhrmfile: '', equipment: null, equipmentOptions: [], heartrate: 0, comments: '', ascent: 0,
  calories: 0, avgcadence: 0, avgpower: 0, device: 'test', ate: 0.0, ante: 0.0,
  training_load: 0, workout_feel: 0, workout_rpe: 0, offset: 0
});

const fetchHrmData = async (hrmfile: string) => {
  try {
    const res = await fetch(apiBaseUrl + `hrm/${encodeURIComponent(hrmfile)}`);
    if (!res.ok) {
      console.error('Failed to fetch HRM data for', hrmfile, res.status);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.error('Error fetching HRM data for', hrmfile, err);
    return null;
  }
};

const appendHrmDataToActivities = async (hrmfile: string, rawData: any) => {
  if (!rawData || typeof rawData !== 'object') return;

  hrmData.value.push(rawData);
  const newActivity = createActivityTemplate();
  newActivity.hrmfile = hrmfile;
  newActivity.name = rawData.workout_name || '';
  newActivity.date = rawData.start_time || '';
  newActivity.sport = rawData.sport || 0;
  newActivity.subsport = rawData.sub_sport || 0;
  newActivity.duration = Math.floor(rawData.total_elapsed_time || 0);
  newActivity.intensity = rawData.intensity || '';
  newActivity.distance = rawData.total_distance || 0;
  newActivity.avgspeed = rawData.avg_speed || 0;
  newActivity.latitude = rawData.start_position_lat || null;
  newActivity.longitude = rawData.start_position_long || null;
  newActivity.equipment = rawData.equipment || '';
  newActivity.heartrate = rawData.avg_heart_rate || 0;
  newActivity.avgcadence = rawData.avg_cadence || 0;
  newActivity.ascent = rawData.total_ascent || 0;
  newActivity.calories = rawData.total_calories || 0;
  newActivity.avgpower = rawData.avg_power || 0;
  newActivity.device = rawData.device || '';
  newActivity.ate = rawData.total_training_effect || 0.0;
  newActivity.ante = rawData.total_anaerobic_training_effect || 0.0;
  newActivity.training_load = rawData.training_load_peak || 0;
  newActivity.workout_feel = rawData.workout_feel || 0;
  newActivity.workout_rpe = rawData.workout_rpe || 0;
  newActivity.offset = rawData.tzoffset || 0;

  const garminSportName = (rawData.sport || '').toLowerCase();
  const garminSubsportName = (rawData.sub_sport || '').toLowerCase();

  const matchedSport = sports.value.find(
    s => s.garmin_name?.toLowerCase() === garminSportName
  );

  if (matchedSport) {
    newActivity.sport = matchedSport.id;
    await handleSportChange(newActivity);

    const matchedSubsport = newActivity.subsportOptions.find(
      ss => ss.garmin_name?.toLowerCase() === garminSubsportName
    );
    const matchedEq = newActivity.equipmentOptions.find(
      e => e.garmin_name?.toLowerCase() === rawData.equipment?.toLowerCase()
    );
    if (matchedSubsport) {
      newActivity.subsport = matchedSubsport.id;
    }
    if (matchedEq) {
      newActivity.equipment = matchedEq.id;
    }
  }

  activities.value.push(newActivity);
};

const uploadFile = async (fileItem: any) => {
  fileItem.status = 'uploading';
  const formData = new FormData();
  formData.append('file', fileItem.file);

  try {
    const response = await fetch(apiBaseUrl + 'uploadhrm2', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');

    fileItem.status = 'success';
    const rawData = await fetchHrmData(fileItem.name);
    if (rawData) {
      await appendHrmDataToActivities(fileItem.name, rawData);
    } else {
      fileItem.status = 'error';
    }
  } catch (error) {
    console.error('Error uploading:', error);
    fileItem.status = 'error';
  }
};

const processFiles = (files: FileList) => {
  const newFiles = Array.from(files).map(file => ({
    file,
    name: file.name,
    status: 'pending' as const
  }));

  // Add to the UI list immediately
  uploadedFiles.value.push(...newFiles);

  // Trigger the upload (and subsequent fetch) for each file
  newFiles.forEach(fileItem => uploadFile(fileItem));
};
// uploaded files info removed (debug)

// Function to fetch subsports when a sport is selected
const handleSportChange = async (act: any) => {
  act.subsport = null; // Reset subsport when sport changes
  act.equipment = null; // Reset equipment when sport changes
  if (!act.sport) {
    act.subsportOptions = [];
    act.equipmentOptions = [];
    return;
  }

  try {
    // Fetch Subsports and Equipment in parallel for better performance
    const [ssRes, eqRes] = await Promise.all([
      fetch(apiBaseUrl + `subsport/${act.sport}`),
      fetch(apiBaseUrl + `equipment/${act.sport}`)
    ]);

    if (ssRes.ok) act.subsportOptions = await ssRes.json();
    if (eqRes.ok) act.equipmentOptions = await eqRes.json();

  } catch (err) {
    console.error('Error fetching cascading data:', err);
  }
};

const handleDrag = (e: DragEvent) => {
  e.preventDefault();
  dragActive.value = (e.type === 'dragenter' || e.type === 'dragover');
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  dragActive.value = false;
  if (e.dataTransfer?.files) processFiles(e.dataTransfer.files);
};

const handleFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files) processFiles(target.files);
};

const isSaving = ref(false);

const isGarminSyncing = ref(false);

// Credential/MFA UI state
const showCredentialsModal = ref(false);
const showMfaModal = ref(false);
const credEmail = ref('');
const credPassword = ref('');
const credSubmitting = ref(false);
const mfaCode = ref('');
const mfaSubmitting = ref(false);
let mfaResumeId: string | null = null;
const showLogoutConfirm = ref(false);
const tokenStatus = ref({ has_tokens: false, has_env_credentials: false });

const startGarminSync = async () => {
  isGarminSyncing.value = true;
  try {
    const response = await fetch(`${apiBaseUrl}sync/days/7`, { method: 'GET' });

    if (!response.ok) throw new Error('Sync failed');

    const data = await response.json();
    const fileNames = data?.downloaded_files || [];

    if (fileNames.length === 0) {
      alert('No new Garmin activities were downloaded.');
      return;
    }

    for (const fileName of fileNames) {
      const rawData = await fetchHrmData(fileName);
      if (rawData) {
        await appendHrmDataToActivities(fileName, rawData);
      } else {
        console.warn('Unable to process synced activity:', fileName);
      }
    }

    alert(`Imported ${fileNames.length} Garmin activity file(s). Review details and save when ready.`);
  } catch (err) {
    console.error('Error during sync:', err);
    alert('Failed to synchronize data.');
  } finally {
    isGarminSyncing.value = false;
  }
}

const checkCredentialStatus = async () => {
  try {
    const res = await fetch(`${apiBaseUrl}sync/credentials/status`);
    if (!res.ok) return { has_tokens: false, has_env_credentials: false };
    return await res.json();
  } catch (e) {
    console.error('Credential status check failed', e);
    return { has_tokens: false, has_env_credentials: false };
  }
}

const refreshTokenStatus = async () => {
  const status = await checkCredentialStatus();
  tokenStatus.value = status;
}

const submitCredentials = async () => {
  if (!credEmail.value || !credPassword.value) return;
  credSubmitting.value = true;
  try {
    const res = await fetch(`${apiBaseUrl}sync/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: credEmail.value, password: credPassword.value })
    });

    if (res.status === 202) {
      const data = await res.json();
      mfaResumeId = data.resume_id;
      showCredentialsModal.value = false;
      showMfaModal.value = true;
        await refreshTokenStatus();
      return;
    }

    if (res.ok) {
      showCredentialsModal.value = false;
      // successful login, start sync
      await refreshTokenStatus();
      await startGarminSync();
      return;
    }

    const err = await res.json();
    alert('Login failed: ' + (err.detail || err.error || 'unknown'));
  } catch (e) {
    console.error('submitCredentials error', e);
    alert('Login failed');
  } finally {
    credSubmitting.value = false;
  }
}

const submitMfa = async () => {
  if (!mfaResumeId || !mfaCode.value) return;
  mfaSubmitting.value = true;
  try {
    const res = await fetch(`${apiBaseUrl}sync/credentials/mfa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_id: mfaResumeId, code: mfaCode.value })
    });

    if (res.ok) {
      showMfaModal.value = false;
      mfaResumeId = null;
      mfaCode.value = '';
      // tokens saved, start sync
      await refreshTokenStatus();
      await startGarminSync();
      return;
    }

    const err = await res.json();
    alert('MFA failed: ' + (err.detail || err.error || 'unknown'));
  } catch (e) {
    console.error('submitMfa error', e);
    alert('MFA submit failed');
  } finally {
    mfaSubmitting.value = false;
  }
}

const handleGarminSync = async () => {
  // Check if tokens or env credentials are present; if not prompt for credentials
  const status = await checkCredentialStatus();
  if (status.has_tokens || status.has_env_credentials) {
    await startGarminSync();
  } else {
    credEmail.value = '';
    credPassword.value = '';
    showCredentialsModal.value = true;
  }
}

const handleGarminLogout = async () => {
  try {
    const res = await fetch(`${apiBaseUrl}sync/credentials/logout`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert('Failed to clear tokens: ' + (err.detail || err.error || res.statusText));
      return;
    }
    const data = await res.json();
    alert('Cleared tokens: ' + (data.removed ? data.removed.join(', ') : 'none'));
    await refreshTokenStatus();
  } catch (e) {
    console.error('handleGarminLogout error', e);
    alert('Failed to clear tokens');
  }
}

onMounted(async () => {
  // existing onMounted earlier fetched sports; also refresh token status
  await refreshTokenStatus();
});

const saveAllActivities = async () => {
  if (activities.value.length === 0) return;

  isSaving.value = true;
  let successCount = 0;
  let errorCount = 0;
  const checkedActivities = activities.value.filter(act => act.checked);

  for (const act of checkedActivities) {
    console.log('Saving activity:', act);
    try {
      const response = await fetch(apiBaseUrl + 'activities', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(serializeActivityForApi(act))
      });

      if (!response.ok) throw new Error(`Failed to save ${act.name}`);

      successCount++;
    } catch (error) {
      console.error('Error saving activity:', error);
      errorCount++;
    }
  }

  isSaving.value = false;

  if (errorCount === 0) {
    alert(`Successfully saved all ${successCount} activities!`);
    activities.value = []; // Clear the list on total success
  } else {
    alert(`Finished with mixed results: ${successCount} saved, ${errorCount} failed.`);
    // Optionally: Filter out the successful ones so the user only sees the failures
  }
};

const isFormValid = computed(() => {
  if (activities.value.length === 0) return false;

  return activities.value.every(act => {
    // Safely check if name exists and has content
    const hasName = act.name && typeof act.name === 'string' && act.name.trim() !== '';

    // Check other mandatory fields
    const hasSport = act.sport !== null && act.sport !== undefined;

    return hasName && hasSport;
  });
});

const secondsToHMS = (seconds: number | string): string => {
  const s = Number(seconds) || 0;
  const h = Math.floor(s / 3600).toString().padStart(2, '0');
  const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
  const sec = (s % 60).toString().padStart(2, '0');
  return `${h}:${m}:${sec}`;
};

const hmsToSeconds = (hms: string, currentValue: number): number => {
  // Regex: 1-2 digits : 1-2 digits : 1-2 digits
  const hmsRegex = /^(\d{1,2}):(\d{1,2}):(\d{1,2})$/;
  const match = hms.trim().match(hmsRegex);


  if (!match) {
    console.warn("Invalid format. Keeping original value:", hms);
    return currentValue; // Fallback to what was there before
  }

  const [_, h, m, s] = match;
  return parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(s);
};

const metersToKm = (m: number | string) => (Number(m) / 1000).toFixed(2);
const kmToMeters = (km: string, current: number) => {
  const val = parseFloat(km);
  return isNaN(val) ? current : Math.round(val * 1000);
};


// Speed: m/s <-> km/h (Conversion factor: 3.6)
const msToKmh = (ms: number | string) => (Number(ms) * 3.6).toFixed(2);
const kmhToMs = (kmh: string, current: number) => {
  const val = parseFloat(kmh);
  return isNaN(val) ? current : val / 3.6;
};

const serializeActivityForApi = (act: any) => {
  return {
    ...act,
    distance: Number((act.distance / 1000).toFixed(2)), // metres → km
    //avgspeed: Number((act.avgspeed * 3.6).toFixed(2)), // optional: m/s → km/h if your API expects it
  };
};

</script>

<style scoped>
.text-purple {
  color: #6f42c1;
}

.upload-zone {
  border: 2px dashed #dee2e6;
  border-radius: 0.5rem;
  padding: 3rem;
  text-align: center;
  background-color: #f8f9fa;
  transition: all 0.2s;
}

.upload-zone:hover {
  border-color: #adb5bd;
}

.upload-zone.drag-active {
  border-color: #0d6efd;
  background-color: #e7f1ff;
}

.bg-success-subtle {
  background-color: #d1e7dd;
}

/* Chrome, Safari, Edge, Opera */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* Firefox */
input[type=number] {
  -moz-appearance: textfield;
}
</style>