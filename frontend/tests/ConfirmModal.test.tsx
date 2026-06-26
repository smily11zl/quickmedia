import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfirmModal from '../src/ConfirmModal';

describe('ConfirmModal', () => {
  it('renders title and message', () => {
    render(
      <ConfirmModal
        title="确认删除"
        message="确定要删除此节点？"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByText('确认删除')).toBeTruthy();
    expect(screen.getByText('确定要删除此节点？')).toBeTruthy();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmModal
        title="确认操作"
        message="确定吗？"
        confirmText="确定"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText('确定'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button clicked', () => {
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        title="确认操作"
        message="确定吗？"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByText('取消'));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('uses coral for default confirm color', () => {
    render(
      <ConfirmModal
        title="测试"
        message="测试消息"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const btn = screen.getByRole('button', { name: /确认/ });
    expect(btn.getAttribute('data-color')).toBe('coral');
  });

  it('uses error color when confirmColor is error', () => {
    render(
      <ConfirmModal
        title="确认删除"
        message="删除不可撤销"
        confirmText="删除"
        confirmColor="error"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const btn = screen.getByRole('button', { name: /删除/ });
    expect(btn.getAttribute('data-color')).toBe('error');
  });

  it('disables confirm button when loading', () => {
    render(
      <ConfirmModal
        title="删除中"
        message="请稍候"
        loading={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const btn = screen.getByText('处理中...');
    expect(btn.hasAttribute('disabled')).toBe(true);
  });
});
