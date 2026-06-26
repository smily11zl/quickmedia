import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import GraphView from '../src/GraphView';

// Mock react-force-graph-2d
vi.mock('react-force-graph-2d', () => ({
  default: vi.fn(() => null),
}));

const mockGraphData = {
  nodes: [{ id: 1, name: '宠物', description: '猫狗', asset_count: 5 }],
  edges: [{ node_id: 1, asset_id: 10 }],
  unassigned: [{ id: 99, filename: 'orphan.jpg', asset_type: 'image' }],
};

const defaultProps = {
  graphData: mockGraphData,
  selectedNodeId: null as number | null,
  selectedNodeName: '',
  onSelectNode: vi.fn(),
  onSelectAsset: vi.fn(),
  searchResults: [] as any[],
  expandedNodes: new Set<number>(),
  onExpandedChange: vi.fn(),
};

describe('GraphView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<GraphView {...defaultProps} />);
    expect(document.querySelector('[data-testid="graph-container"]')).toBeFalsy(); // Canvas-based, no DOM container
  });

  it('shows legend', () => {
    render(<GraphView {...defaultProps} />);
    expect(screen.getByText(/聚合节点/)).toBeTruthy();
    expect(screen.getByText(/未分配节点/)).toBeTruthy();
  });

  it('renders zoom controls', () => {
    render(<GraphView {...defaultProps} />);
    expect(screen.getByText('+')).toBeTruthy();
    expect(screen.getByText('−')).toBeTruthy();
    expect(screen.getByText('⌂')).toBeTruthy();
    expect(screen.getByText('🔄')).toBeTruthy();
  });
});
