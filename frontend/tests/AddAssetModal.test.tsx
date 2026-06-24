import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import AddAssetModal from '../src/AddAssetModal';

const mockFetch = vi.fn();
window.fetch = mockFetch as any;

beforeEach(() => {
  mockFetch.mockReset();
});

describe('AddAssetModal', () => {
  const mockAssets = [
    { id: 1, filename: 'cat.jpg', asset_type: 'image', size: 100, path: '/a', thumbnail_status: 'done' },
    { id: 2, filename: 'dog.mp4', asset_type: 'video', size: 200, path: '/b', thumbnail_status: 'pending' },
    { id: 3, filename: 'contract.pdf', asset_type: 'document', size: 300, path: '/c', thumbnail_status: 'pending' },
  ];

  it('fetches assets on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="测试节点" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/assets?limit=500');
    });
  });

  it('renders node name in title', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="宠物" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/宠物/)).toBeDefined();
    });
  });

  it('renders all fetched assets', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="测试" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('cat.jpg')).toBeDefined();
      expect(screen.getByText('dog.mp4')).toBeDefined();
      expect(screen.getByText('contract.pdf')).toBeDefined();
    });
  });

  it('shows asset count', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="测试" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/已选 0 \/ 3/)).toBeDefined();
    });
  });

  it('has confirm button initially disabled', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="测试" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      const btn = screen.getByText(/确认添加/).closest('button');
      expect(btn?.disabled).toBe(true);
    });
  });

  it('has search input', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ items: mockAssets }),
    } as any);

    render(<AddAssetModal nodeId={1} nodeName="测试" onClose={() => {}} onAdded={() => {}} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('搜索素材...')).toBeDefined();
    });
  });
});
