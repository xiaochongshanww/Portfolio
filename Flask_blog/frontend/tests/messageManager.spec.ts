import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mocks = vi.hoisted(() => ({ ElMessage: vi.fn() }));
vi.mock('element-plus', () => ({ ElMessage: mocks.ElMessage }));

import messageManager, { MESSAGE_PRIORITY } from '../src/utils/messageManager';

describe('messageManager', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.ElMessage.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('normalizes string options to info priority', () => {
    const m = messageManager._normalizeMessage('hello');
    expect(m.content).toBe('hello');
    expect(m.priority).toBe(MESSAGE_PRIORITY.INFO);
    expect(m.type).toBe('info');
  });

  it('normalizes object options', () => {
    const m = messageManager._normalizeMessage({
      message: 'x',
      type: 'success',
      priority: MESSAGE_PRIORITY.SUCCESS,
    });
    expect(m.content).toBe('x');
    expect(m.type).toBe('success');
    expect(m.priority).toBe(MESSAGE_PRIORITY.SUCCESS);
  });

  it('detects duplicates within 3 seconds', () => {
    expect(messageManager._isDuplicateMessage({ content: 'dup-a', timestamp: 1000 })).toBe(false);
    expect(messageManager._isDuplicateMessage({ content: 'dup-a', timestamp: 2000 })).toBe(true);
    expect(messageManager._isDuplicateMessage({ content: 'dup-b', timestamp: 2000 })).toBe(false);
  });

  it('flushes critical messages immediately', () => {
    messageManager.show({
      content: 'critical-msg',
      priority: MESSAGE_PRIORITY.CRITICAL,
      type: 'error',
    });
    vi.runAllTimers();
    expect(mocks.ElMessage).toHaveBeenCalled();
  });

  it('batches non-critical messages until scheduled flush', () => {
    messageManager.show({
      content: 'info-msg',
      priority: MESSAGE_PRIORITY.INFO,
      type: 'info',
    });
    expect(mocks.ElMessage).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(mocks.ElMessage).toHaveBeenCalled();
  });

  it('merges similar messages of same type', () => {
    const merged = messageManager._mergeSimilarMessages([
      { content: 'm1', type: 'info', priority: MESSAGE_PRIORITY.INFO },
      { content: 'm2', type: 'info', priority: MESSAGE_PRIORITY.INFO },
    ]);
    expect(merged.length).toBe(1);
  });

  it('keeps different types separate', () => {
    const merged = messageManager._mergeSimilarMessages([
      { content: 'e1', type: 'error', priority: MESSAGE_PRIORITY.CRITICAL },
      { content: 'i1', type: 'info', priority: MESSAGE_PRIORITY.INFO },
    ]);
    expect(merged.length).toBe(2);
  });

  it('maps default icons by type', () => {
    expect(messageManager._getDefaultIcon('error')).toBe('🚨');
    expect(messageManager._getDefaultIcon('success')).toBe('✅');
    expect(messageManager._getDefaultIcon('unknown')).toBe('');
  });
});
