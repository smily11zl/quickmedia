import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NodePanel from '../src/NodePanel';

// Mock global fetch
const mockFetch = vi.fn();
window.fetch = mockFetch as any;

// Helper to reset fetch between tests
beforeEach(() => {
  mockFetch.mockReset();
});

describe('NodePanel', () => {
  const mockNodes = [
    { id: 1, name: '宠物', description: '猫狗照片', asset_count: 5 },
    { id: 2, name: '文档', description: '项目文件', asset_count: 3 },
  ];

  const aggIdle = { status: 'idle' };
  const aggRunning = { status: 'processing', task: { mode: 'full', status: 'processing' } };
  const aggFailed = { status: 'failed', task: { mode: 'full', status: 'failed', error: 'AI timeout' } };

  function mockResponses(nodes: any[], agg: any) {
    mockFetch
      .mockResolvedValueOnce({ json: () => Promise.resolve(nodes) } as any)   // fetchNodes
      .mockResolvedValueOnce({ json: () => Promise.resolve(agg) } as any);     // fetchStatus
  }

  it('renders empty state when no nodes', async () => {
    mockResponses([], aggIdle);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/暂无聚合节点/)).toBeDefined();
    });
  });

  it('renders action buttons on empty state', async () => {
    mockResponses([], aggIdle);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('全量分析')).toBeDefined();
    });
  });

  it('does not show append buttons when no nodes exist', async () => {
    mockResponses([], aggIdle);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('全量分析')).toBeDefined();
    });
    // 全量追加 and 追加分析 should not appear (no nodes)
    expect(screen.queryByText('全量追加')).toBeNull();
    expect(screen.queryByText('追加分析')).toBeNull();
  });

  it('renders node list with names and counts', async () => {
    mockResponses(mockNodes, aggIdle);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('宠物')).toBeDefined();
      expect(screen.getByText('(5)')).toBeDefined();
      expect(screen.getByText('文档')).toBeDefined();
      expect(screen.getByText('(3)')).toBeDefined();
    });
  });

  it('shows all three action buttons when nodes exist', async () => {
    mockResponses(mockNodes, aggIdle);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('全量分析')).toBeDefined();
      expect(screen.getByText('全量追加')).toBeDefined();
      expect(screen.getByText('追加分析')).toBeDefined();
    });
  });

  it('shows processing banner when aggregation is running', async () => {
    mockResponses(mockNodes, aggRunning);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('聚合分析中...')).toBeDefined();
    });
  });

  it('shows error banner when aggregation failed', async () => {
    mockResponses(mockNodes, aggFailed);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/AI timeout/)).toBeDefined();
    });
  });

  it('disables action buttons when running', async () => {
    mockResponses(mockNodes, aggRunning);

    render(<NodePanel onSelectNode={() => {}} />);

    await waitFor(() => {
      const btn = screen.getByText('全量分析').closest('button');
      expect(btn?.disabled).toBe(true);
    });
  });

  it('calls onSelectNode when a node is clicked', async () => {
    const onSelect = vi.fn();
    mockResponses(mockNodes, aggIdle);

    render(<NodePanel onSelectNode={onSelect} />);

    await waitFor(() => {
      expect(screen.getByText('宠物')).toBeDefined();
    });

    screen.getByText('宠物').click();
    expect(onSelect).toHaveBeenCalledWith(1, "宠物");
  });
});
