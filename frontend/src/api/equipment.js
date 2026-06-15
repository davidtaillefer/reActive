const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

const normalizeEquipment = (e) => ({
  ...e,
  equipmentId: e.idk
});

export const getSports = async () => {
  const res = await fetch(`${apiBaseUrl}/sports`);
  return res.json();
};

export const getEquipmentBySport = async (sportId) => {
  const res = await fetch(`${apiBaseUrl}/equipment/${sportId}`);
  const data = await res.json();
  return data.map(normalizeEquipment);
};

export const getEquipmentById = async (id) => {
  const res = await fetch(`${apiBaseUrl}/equipment2/${id}`);
  const data = await res.json();

  const item = Array.isArray(data) ? data[0] : data;

  return item;
};

export const getTotalDistance = async (id) => {
  const res = await fetch(`${apiBaseUrl}/equipment/usage/${id}`);
  const data = await res.json();
  return data.total_distance;
};

export const createEquipment = async (formData) => {
  return fetch(`${apiBaseUrl}/equipment`, {
    method: 'POST',
    body: formData
  });
};

export const updateEquipment = async (id, formData) => {
  return fetch(`${apiBaseUrl}/equipment/${id}`, {
    method: 'PUT',
    body: formData
  });
};

export const deleteEquipment = (id) =>
    fetch(`${apiBaseUrl}/equipment/${id}`, {
        method: 'DELETE'
    });

export const getMaintenance = async (id) => {
  const res = await fetch(`${apiBaseUrl}/equipment/${id}/maintenance`);
  return res.json();
};

export const createMaintenance = async (id, maintenanceData) => {
  return fetch(`${apiBaseUrl}/equipment/${id}/maintenance`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(maintenanceData)
  });
};

export const updateMaintenance = (id, data) =>
    fetch(`${apiBaseUrl}equipment/${id}/maintenance`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

export const deleteMaintenance = (id) =>
    fetch(`${apiBaseUrl}equipment/${id}/maintenance`, {
        method: 'DELETE'
    });