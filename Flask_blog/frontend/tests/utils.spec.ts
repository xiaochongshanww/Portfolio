import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getMediaIcon,
  formatFileSize,
  getMediaTypeName,
  getVisibilityInfo,
} from '../src/utils/mediaUtils';
import {
  getUserDisplayName,
  getUserShortName,
  getUserFullName,
  shouldPromptNickname,
  getUserDisplayHint,
  getNicknameSuggestion,
} from '../src/utils/userDisplay';
import {
  codeThemes,
  getThemeColors,
  switchTheme,
  loadThemeFromStorage,
} from '../src/utils/codeTheme';
import { message } from '../src/utils/message';
import messageManager from '../src/utils/messageManager';

describe('mediaUtils', () => {
  it('getMediaIcon maps known and falls back to Files', () => {
    expect(getMediaIcon('image')).toBe('Picture');
    expect(getMediaIcon('video')).toBe('VideoPlay');
    expect(getMediaIcon('unknown')).toBe('Files');
    expect(getMediaIcon(undefined)).toBe('Files');
  });

  it('formatFileSize formats sizes', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(undefined)).toBe('0 B');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(2 * 1024 * 1024)).toBe('2 MB');
  });

  it('getMediaTypeName maps known types', () => {
    expect(getMediaTypeName('image')).toBe('图片');
    expect(getMediaTypeName('bogus')).toBe('未知');
  });

  it('getVisibilityInfo handles all visibilities', () => {
    expect(getVisibilityInfo('private').name).toBe('私有');
    expect(getVisibilityInfo('shared').name).toBe('共享');
    expect(getVisibilityInfo('public').name).toBe('公开');
    expect(getVisibilityInfo('weird').name).toBe('未知');
    expect(getVisibilityInfo(123).name).toBe('未知');
  });
});

describe('userDisplay', () => {
  it('returns fallback when no user', () => {
    expect(getUserDisplayName(null)).toBe('用户');
    expect(getUserDisplayName(undefined)).toBe('用户');
  });

  it('prefers nickname and truncates', () => {
    const user = { nickname: 'Alice', email: 'alice@x.com', id: 1 };
    expect(getUserDisplayName(user)).toBe('Alice');
    const long = { nickname: 'A'.repeat(20), email: 'e@x.com', id: 1 };
    expect(getUserDisplayName(long)).toBe('A'.repeat(11) + '…');
  });

  it('falls back to email prefix', () => {
    const user = { email: 'alice@example.com', id: 2 };
    expect(getUserDisplayName(user)).toBe('alice');
  });

  it('falls back to id when no nickname/email usable', () => {
    expect(getUserDisplayName({ id: 7 })).toBe('用户7');
    expect(getUserDisplayName({ email: 'test123@x.com', id: 3 })).toBe('用户3');
  });

  it('short/full name variants', () => {
    const user = { nickname: 'Bob', email: 'b@x.com', id: 1 };
    expect(getUserShortName(user)).toBe('Bob');
    expect(getUserFullName(null)).toBe('匿名用户');
  });

  it('shouldPromptNickname', () => {
    expect(shouldPromptNickname({ nickname: '', email: 'e@x.com' })).toBe(true);
    expect(shouldPromptNickname({ nickname: 'ok', email: 'e@x.com' })).toBe(false);
    expect(shouldPromptNickname(null)).toBe(false);
  });

  it('getUserDisplayHint', () => {
    expect(getUserDisplayHint(null)).toBe('');
    expect(getUserDisplayHint({ nickname: 'N', email: 'e@x.com' })).toBe('昵称: N');
    expect(getUserDisplayHint({ email: 'e@x.com' })).toBe('邮箱: e@x.com');
    expect(getUserDisplayHint({ id: 9 })).toBe('用户ID: 9');
  });

  it('getNicknameSuggestion', () => {
    expect(getNicknameSuggestion({ nickname: 'ok' })).toBeNull();
    const suggestion = getNicknameSuggestion({ email: 'sug@x.com', id: 4 });
    expect(suggestion).not.toBeNull();
    expect(suggestion?.shouldPrompt).toBe(true);
    expect(suggestion?.suggestion).toBe('sug');
  });
});

describe('codeTheme', () => {
  it('exposes a theme list', () => {
    expect(codeThemes.length).toBeGreaterThanOrEqual(5);
    expect(codeThemes[0].value).toBe('github-dark');
  });

  it('getThemeColors returns config and falls back', () => {
    expect(getThemeColors('github-dark').background).toBe('#0d1117');
    expect(getThemeColors('nord').keyword).toBe('#81a1c1');
    expect(getThemeColors('unknown').background).toBe('#0d1117');
  });

  it('switchTheme updates current theme and persists', () => {
    switchTheme('nord');
    expect(localStorage.getItem('codeTheme')).toBe('nord');
    expect(document.getElementById('global-code-theme')).not.toBeNull();
  });

  it('loadThemeFromStorage restores saved or defaults', () => {
    localStorage.setItem('codeTheme', 'nord');
    loadThemeFromStorage();
    expect(document.getElementById('global-code-theme')).not.toBeNull();
    localStorage.setItem('codeTheme', 'not-a-theme');
    loadThemeFromStorage();
    expect(document.getElementById('global-code-theme')).not.toBeNull();
  });
});

describe('message', () => {
  beforeEach(() => {
    vi.spyOn(messageManager, 'show').mockImplementation(() => {});
  });

  it('delegates to messageManager with priorities', () => {
    message.success('ok');
    expect(messageManager.show).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'success' })
    );
    message.error('boom');
    expect(messageManager.show).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'error' })
    );
    message.warning('warn');
    expect(messageManager.show).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'warning' })
    );
    message.info('info');
    expect(messageManager.show).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'info' })
    );
  });

  it('accepts object form', () => {
    message.show({ message: 'obj', duration: 1 });
    expect(messageManager.show).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'obj', duration: 1 })
    );
  });
});
