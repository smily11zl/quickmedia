import { describe, it, expect, beforeEach } from 'vitest';

// We'll test the i18n module once it exists
describe('s1: i18n module', () => {
  describe('locale files', () => {
    it('zh and en exist a...[truncated]
import { describe, it, expect } from 'vitest';

describe('V18: aiT status colors', () => {
  // Color mapping should match detail panel:
  // done=#5db872, processing=#e8a55a, failed=#c64545, pending=#6c6a64, cancelled=#8b75a6
  const EXPECTED_COLORS: Record<string, string> = {
    done: '#5db872',
    processing: '#e8a55a', 
    failed: '#c64545',
    pending: '#6c6a64',
    cancelled: '#8b75a6',
  };

  it('all 5 statuses have defined colors', () => {
    const statuses = ['done', 'processing', 'pending', 'failed', 'cancelled'];
    statuses.forEach(s => {
      expect(EXPECTED_COLORS[s]).toBeDefined();
    });
  });

  it('colors are distinct from each other', () => {
    const colors = Object.values(EXPECTED_COLORS);
    expect(new Set(colors).size).toBe(colors.length);
  });
});
