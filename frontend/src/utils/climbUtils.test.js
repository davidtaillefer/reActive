import test from 'node:test';
import assert from 'node:assert/strict';
import {
  getGradeColor as getGradeColour,
  buildClimbProfile,
  formatDistanceLabel,
  formatGradeValue,
  sanitizeTrackPoints,
} from './climbUtils.js';
import {
  getZoneColour,
  getMetricColour,
  getZoneThresholds,
} from './metricColours.js';

test('grade colors use the shared bucket palette instead of the old gradient', () => {
  assert.equal(getGradeColour(-10), '#2563eb');
  assert.equal(getGradeColour(0), '#f4d35e');
  assert.equal(getGradeColour(10), '#ef4444');
});

test('climb profile builds segment datasets for a selected climb', () => {
  const track = [
    { distance: 0, enhanced_altitude: 100 },
    { distance: 50, enhanced_altitude: 110 },
    { distance: 100, enhanced_altitude: 120 },
    { distance: 150, enhanced_altitude: 130 },
  ];

  const result = buildClimbProfile({ start_index: 0, end_index: 3 }, track);

  assert.equal(result.points.length, 4);
  assert.equal(result.datasets.length, 3);
  assert.equal(result.datasets[0].data[0].x, 0);
  assert.equal(result.datasets[0].data[1].x, 50);
  assert.equal(result.datasets[0].backgroundColor.startsWith('rgba('), true);
  assert.notEqual(result.datasets[0].backgroundColor, 'rgba(255, 255, 255, 0.3)');
});

test('climb profile formatting rounds distance labels and grade values consistently', () => {
  assert.equal(formatDistanceLabel(1567.8), '1568m');
  assert.equal(formatDistanceLabel(1567.2), '1567m');
  assert.equal(formatGradeValue(6.125), '6.1%');
  assert.equal(formatGradeValue(-3.0), '-3.0%');
});

test('sanitizeTrackPoints drops invalid and 0,0 coordinates before route fitting', () => {
  const points = [
    { position_lat: 52.12, position_long: -1.34 },
    { position_lat: null, position_long: null },
    { position_lat: 0, position_long: 0 },
    { position_lat: '', position_long: '1.23' },
    { position_lat: 52.13, position_long: -1.35 },
  ];

  const sanitized = sanitizeTrackPoints(points);

  assert.equal(sanitized.length, 2);
  assert.deepEqual(sanitized[0], points[0]);
  assert.deepEqual(sanitized[1], points[4]);
});

test('zone-based route colors use the shared zone palettes instead of gradients', () => {
  assert.equal(getZoneColour('hr', 1), '#007bff');
  assert.equal(getZoneColour('hr', 5), '#dc3545');
  assert.equal(getZoneColour('power', 2), '#28a745');
  assert.equal(getZoneColour('speed', 4), '#f97316');
  assert.equal(getZoneColour('grade', 5), '#f7a928');

  assert.equal(getMetricColour('hr', 110, { max_hr: 200 }), '#007bff');
  assert.equal(getMetricColour('speed', 27, { max_speed: 40 }), '#f97316');
  assert.equal(getMetricColour('grade', 4.5), '#f7a928');

  assert.deepEqual(getZoneThresholds('speed'), [
    { min: 0, max: 15, label: '0–15 kph', color: '#60a5fa' },
    { min: 15, max: 20, label: '15–20 kph', color: '#34d399' },
    { min: 20, max: 25, label: '20–25 kph', color: '#facc15' },
    { min: 25, max: 30, label: '25–30 kph', color: '#f97316' },
    { min: 30, max: 40, label: '30–40 kph', color: '#ef4444' },
    { min: 40, max: Infinity, label: '40+ kph', color: '#7c2d12' },
  ]);
});
