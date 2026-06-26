import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import Toast from '../src/Toast';

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with message', () => {
    render(<Toast message="测试消息" onClose={vi.fn()} />);
    expect(screen.getByText('测试消息')).toBeTruthy();
    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('renders default info type', () => {
    render(<Toast message="信息" onClose={vi.fn()} />);
    expect(screen.getByRole('status').getAttribute('data-type')).toBe('info');
  });

  it('renders error type', () => {
    render(<Toast message="错误" type="error" onClose={vi.fn()} />);
    expect(screen.getByRole('status').getAttribute('data-type')).toBe('error');
  });

  it('renders success type', () => {
    render(<Toast message="成功" type="success" onClose={vi.fn()} />);
    expect(screen.getByRole('status').getAttribute('data-type')).toBe('success');
  });

  it('auto-dismisses after 2.5 seconds', () => {
    const onClose = vi.fn();
    render(<Toast message="自动消失" onClose={onClose} />);
    expect(onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(2500); });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
