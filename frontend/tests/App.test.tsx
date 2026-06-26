import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock fetch globally
const mockFetch = vi.fn();
window.fetch = mockFetch as any;

// Mock cytoscape
vi.mock('cytoscape', () => {
  const mockLayout = { run: vi.fn(), stop: vi.fn() };
  const mockCy = {
    add: vi.fn().mockReturnThis(),
    style: vi.fn().mockReturnThis(),
    layout: vi.fn(() => mockLayout),
    on: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    zoom: vi.fn(() => 1),
    pan: vi.fn(() => ({ x: 0, y: 0 })),
    center: vi.fn(),
    fit: vi.fn(),
    json: vi.fn(() => ({ elements: [] })),
    destroy: vi.fn(),
    resize: vi.fn(),
  };
  return { default: vi.fn(() => mockCy) };
});

beforeEach(() => {
  mockFetch.mockReset();
  // Mock all API calls that App makes on mount
  mockFetch
    .mockResolvedValueOnce({ json: () => Promise.resolve({ total: 0, items: [], counts: { image: 0, video: 0, audio: 0, document: 0 } }) } as any) // /api/assets
    .mockResolvedValueOnce({ json: () => Promise.resolve([]) } as any)  // /api/formats
    .mockResolvedValueOnce({ json: () => Promise.resolve({ paths: [] }) } as any) // /api/config/watch-paths
    .mockResolvedValueOnce({ json: () => Promise.resolve({}) } as any)  // /api/task-models (ckCfg)
    .mockResolvedValueOnce({ json: () => Promise.resolve({}) } as any)  // /api/config/watch-paths (ckCfg)
    .mockResolvedValueOnce({ json: () => Promise.resolve([]) } as any)  // /api/tags
    .mockResolvedValueOnce({ json: () => Promise.resolve({ pending: 0, processing_name: null }) } as any) // /api/queue/status
    .mockResolvedValueOnce({ json: () => Promise.resolve({ total: 0, items: [] }) } as any); // /api/assets (poll)
});

describe('App view toggle', () => {
  it.skip('renders graph view button', async () => {
    // Dynamic import to ensure mocks are in place
    const App = (await import('../src/App')).default;
    render(<App />);
    // Three view buttons should exist
    expect(screen.getByText(/云图/)).toBeTruthy();
    expect(screen.getByText(/网格/)).toBeTruthy();
    expect(screen.getByText(/列表/)).toBeTruthy();
  });
});
