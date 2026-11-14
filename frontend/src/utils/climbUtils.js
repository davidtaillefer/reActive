import { getMetricColour } from './metricColours.js';

export function getGradeColour(grade, minGrade = -10, maxGrade = 10) {
  const value = Number.isFinite(Number(grade)) ? Number(grade) : 0;
  void minGrade;
  void maxGrade;
  return getMetricColour('grade', value);
}

export function formatDistanceLabel(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return '0m';
  return `${Math.round(numericValue)}m`;
}

export function formatGradeValue(value, digits = 1) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return `0.${'0'.repeat(digits)}%`;
  return `${numericValue.toFixed(digits)}%`;
}

export function sanitizeTrackPoints(track = []) {
  const points = Array.isArray(track) ? track : Object.values(track || {});

  return points.filter((point) => {
    if (!point) return false;

    const toNumber = (value) => {
      if (value == null) return Number.NaN;
      if (typeof value === 'string' && value.trim() === '') return Number.NaN;
      return Number(value);
    };

    const lat = toNumber(point.position_lat);
    const lon = toNumber(point.position_long);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
    if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return false;
    if (lat === 0 && lon === 0) return false;

    return true;
  });
}

function rgbaFromRgb(colour, alpha = 0.3) {
  if (!colour) return `rgba(255, 255, 255, ${alpha})`;

  const normalized = String(colour).trim();

  if (normalized.startsWith('#')) {
    const hex = normalized.slice(1);
    const fullHex = hex.length === 3
      ? hex.split('').map((char) => char + char).join('')
      : hex;
    const numeric = Number.parseInt(fullHex, 16);
    const r = (numeric >> 16) & 255;
    const g = (numeric >> 8) & 255;
    const b = numeric & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  const rgbMatch = normalized.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([0-9.]+))?\)/i);
  if (rgbMatch) {
    const [, r, g, b] = rgbMatch;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  return `rgba(255, 255, 255, ${alpha})`;
}

export function buildClimbProfile(climb, track = []) {
  const trackPoints = Array.isArray(track) ? track : Object.values(track || {});
  if (!trackPoints.length || !climb) {
    return { points: [], datasets: [], totalDistance: 0 };
  }

  const startIndex = Number.isFinite(Number(climb.start_index)) ? Number(climb.start_index) : 0;
  const endIndex = Number.isFinite(Number(climb.end_index)) ? Number(climb.end_index) : startIndex;
  const selected = trackPoints.slice(
    Math.max(0, startIndex),
    Math.min(trackPoints.length, endIndex + 1),
  );

  if (selected.length < 2) {
    return { points: [], datasets: [], totalDistance: 0 };
  }

  const startDistance = Number(selected[0].distance ?? 0);
  const points = selected.map((point, index) => {
    const distance = Number(point.distance ?? 0);
    const altitude = Number(point.enhanced_altitude ?? point.altitude ?? 0);
    return {
      index,
      distanceMeters: index === 0 ? 0 : Number(distance - startDistance),
      elevation: altitude,
      grade: Number(point.grade_smooth ?? point.grade ?? 0),
    };
  });

  const datasets = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const prev = points[i];
    const curr = points[i + 1];
    const distanceDelta = Math.max(curr.distanceMeters - prev.distanceMeters, 1);
    const grade = ((curr.elevation - prev.elevation) / distanceDelta) * 100;
    const color = getGradeColour(grade);

    datasets.push({
      label: `Climb segment ${i + 1}`,
      data: [
        { x: prev.distanceMeters, y: prev.elevation },
        { x: curr.distanceMeters, y: curr.elevation },
      ],
      borderColor: color,
      backgroundColor: rgbaFromRgb(color, 0.3),
      pointRadius: 0,
      borderWidth: 4,
      spanGaps: false,
      fill: 'origin',
      tension: 0,
      order: i,
    });
  }

  const totalDistance = Math.max(points.at(-1)?.distanceMeters ?? 0, 0);
  return { points, datasets, totalDistance };
}
