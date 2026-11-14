export const HR_ZONE_COLOURS = ['#007bff', '#28a745', '#ffc107', '#fd7e14', '#dc3545'];
export const POWER_ZONE_COLOURS = ['#add8e6', '#007bff', '#28a745', '#ffc107', '#fd7e14', '#dc3545', '#8b0000', '#800080'];
export const SPEED_ZONE_COLOURS = ['#60a5fa', '#34d399', '#facc15', '#f97316', '#ef4444', '#7c2d12'];
export const GRADE_ZONE_COLOURS = ['#1d4ed8', '#007bff', '#add8e6', '#f4d35e', '#f7a928', '#f97316', '#ef4444', '#dc2626', '#7f1d1d'];

const DEFAULT_FALLBACK = '#999';

export function getZoneThresholds(metric) {
  switch (metric) {
    case 'hr':
      return [
        { min: 0, max: 0.6, label: 'Zone 1', color: HR_ZONE_COLOURS[0] },
        { min: 0.6, max: 0.7, label: 'Zone 2', color: HR_ZONE_COLOURS[1] },
        { min: 0.7, max: 0.8, label: 'Zone 3', color: HR_ZONE_COLOURS[2] },
        { min: 0.8, max: 0.9, label: 'Zone 4', color: HR_ZONE_COLOURS[3] },
        { min: 0.9, max: Infinity, label: 'Zone 5', color: HR_ZONE_COLOURS[4] },
      ];
    case 'power':
      return [
        { min: 0, max: 0.55, label: 'Zone 1', color: POWER_ZONE_COLOURS[1] },
        { min: 0.55, max: 0.75, label: 'Zone 2', color: POWER_ZONE_COLOURS[2] },
        { min: 0.75, max: 0.9, label: 'Zone 3', color: POWER_ZONE_COLOURS[3] },
        { min: 0.9, max: 1.05, label: 'Zone 4', color: POWER_ZONE_COLOURS[4] },
        { min: 1.05, max: 1.2, label: 'Zone 5', color: POWER_ZONE_COLOURS[5] },
        { min: 1.2, max: Infinity, label: 'Zone 6+', color: POWER_ZONE_COLOURS[6] },
      ];
    case 'speed':
      return [
        { min: 0, max: 15, label: '0–15 kph', color: SPEED_ZONE_COLOURS[0] },
        { min: 15, max: 20, label: '15–20 kph', color: SPEED_ZONE_COLOURS[1] },
        { min: 20, max: 25, label: '20–25 kph', color: SPEED_ZONE_COLOURS[2] },
        { min: 25, max: 30, label: '25–30 kph', color: SPEED_ZONE_COLOURS[3] },
        { min: 30, max: 40, label: '30–40 kph', color: SPEED_ZONE_COLOURS[4] },
        { min: 40, max: Infinity, label: '40+ kph', color: SPEED_ZONE_COLOURS[5] },
      ];
    case 'grade':
      return [
        { min: -Infinity, max: -10, label: '<-10%', color: GRADE_ZONE_COLOURS[0] },
        { min: -10, max: -5, label: '-10% to -5%', color: GRADE_ZONE_COLOURS[1] },
        { min: -5, max: 0, label: '-5% to 0%', color: GRADE_ZONE_COLOURS[2] },
        { min: 0, max: 3, label: '0% to 3%', color: GRADE_ZONE_COLOURS[3] },
        { min: 3, max: 6, label: '3% to 6%', color: GRADE_ZONE_COLOURS[4] },
        { min: 6, max: 9, label: '6% to 9%', color: GRADE_ZONE_COLOURS[5] },
        { min: 9, max: 12, label: '9% to 12%', color: GRADE_ZONE_COLOURS[6] },
        { min: 12, max: 15, label: '12% to 15%', color: GRADE_ZONE_COLOURS[7] },
        { min: 15, max: Infinity, label: '>15%', color: GRADE_ZONE_COLOURS[8] },
      ];
    default:
      return [];
  }
}

export function getZoneColour(metric, zone) {
  const zones = getZoneThresholds(metric);
  if (!zones.length || zone == null) return DEFAULT_FALLBACK;
  const index = Number(zone) - 1;
  const match = zones[index] || zones[zones.length - 1];
  return match?.color || DEFAULT_FALLBACK;
}

export function resolveMetricZone(metric, value, options = {}) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return null;

  switch (metric) {
    case 'hr': {
      const maxHr = Number(options.max_hr ?? 200);
      if (!Number.isFinite(maxHr) || maxHr <= 0) return null;
      const ratio = numericValue / maxHr;
      if (ratio < 0.6) return 1;
      if (ratio < 0.7) return 2;
      if (ratio < 0.8) return 3;
      if (ratio < 0.9) return 4;
      return 5;
    }
    case 'power': {
      const ftp = Number(options.ftp ?? 250);
      if (!Number.isFinite(ftp) || ftp <= 0) return null;
      const ratio = numericValue / ftp;
      if (ratio < 0.55) return 1;
      if (ratio < 0.75) return 2;
      if (ratio < 0.9) return 3;
      if (ratio < 1.05) return 4;
      if (ratio < 1.2) return 5;
      return 6;
    }
    case 'speed': {
      if (numericValue < 15) return 1;
      if (numericValue < 20) return 2;
      if (numericValue < 25) return 3;
      if (numericValue < 30) return 4;
      if (numericValue < 40) return 5;
      return 6;
    }
    case 'grade': {
      if (numericValue < -10) return 1;
      if (numericValue < -5) return 2;
      if (numericValue < 0) return 3;
      if (numericValue < 3) return 4;
      if (numericValue < 6) return 5;
      if (numericValue < 9) return 6;
      if (numericValue < 12) return 7;
      if (numericValue < 15) return 8;
      return 9;
    }
    default:
      return null;
  }
}

export function getMetricColour(metric, value, options = {}) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue) || !metric) return DEFAULT_FALLBACK;
  const zone = resolveMetricZone(metric, numericValue, options);
  if (zone == null) return DEFAULT_FALLBACK;
  return getZoneColour(metric, zone);
}

export function getMetricLegendStops(metric) {
  return getZoneThresholds(metric).map((zone) => zone.color);
}
