'use client';

import { createContext, useContext, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useHotkeys } from 'react-hotkeys-hook';

interface KeyboardShortcutsContextType {
  // Add any methods we need to expose
}

const KeyboardShortcutsContext = createContext<KeyboardShortcutsContextType | undefined>(undefined);

export function useKeyboardShortcuts() {
  const context = useContext(KeyboardShortcutsContext);
  if (context === undefined) {
    throw new Error('useKeyboardShortcuts must be used within a KeyboardShortcutsProvider');
  }
  return context;
}

interface KeyboardShortcutsProviderProps {
  children: React.ReactNode;
}

export function KeyboardShortcutsProvider({ children }: KeyboardShortcutsProviderProps) {
  const router = useRouter();

  // Navigation shortcuts
  useHotkeys('g+d', () => router.push('/'), { preventDefault: true });
  useHotkeys('g+l', () => router.push('/leads'), { preventDefault: true });
  useHotkeys('g+s', () => router.push('/sources'), { preventDefault: true });
  useHotkeys('g+r', () => router.push('/runs'), { preventDefault: true });
  useHotkeys('g+c', () => router.push('/campaigns'), { preventDefault: true });
  useHotkeys('g+e', () => router.push('/exports'), { preventDefault: true });
  useHotkeys('g+p', () => router.push('/playbooks'), { preventDefault: true });
  useHotkeys('g+t', () => router.push('/settings'), { preventDefault: true });

  // Global shortcuts
  useHotkeys('ctrl+k,cmd+k', () => {
    // Focus search input
    const searchInput = document.querySelector('input[placeholder*="Søk"]') as HTMLInputElement;
    if (searchInput) {
      searchInput.focus();
    }
  }, { preventDefault: true });

  useHotkeys('f', () => {
    // Focus search when 'f' is pressed
    const searchInput = document.querySelector('input[placeholder*="Søk"]') as HTMLInputElement;
    if (searchInput && document.activeElement?.tagName !== 'INPUT') {
      searchInput.focus();
    }
  });

  useHotkeys('e', () => {
    // Quick export shortcut
    const exportButton = document.querySelector('[data-shortcut="export"]') as HTMLButtonElement;
    if (exportButton && document.activeElement?.tagName !== 'INPUT') {
      exportButton.click();
    }
  });

  useHotkeys('escape', () => {
    // Close modals, clear focus, etc.
    const activeElement = document.activeElement as HTMLElement;
    if (activeElement?.tagName === 'INPUT') {
      activeElement.blur();
    }

    // Close any open dropdowns or modals
    const escElements = document.querySelectorAll('[data-escape="true"]');
    escElements.forEach((element) => {
      const button = element as HTMLButtonElement;
      button.click();
    });
  });

  // Show keyboard shortcuts help
  useHotkeys('shift+/', () => {
    // Could open a help modal showing all shortcuts
    console.log('Keyboard shortcuts:');
    console.log('G+D: Dashboard');
    console.log('G+L: Leads');
    console.log('G+S: Sources');
    console.log('G+R: Runs');
    console.log('G+C: Campaigns');
    console.log('G+E: Exports');
    console.log('G+P: Playbooks');
    console.log('G+T: Settings');
    console.log('Ctrl/Cmd+K: Search');
    console.log('F: Focus search');
    console.log('E: Quick export');
    console.log('Escape: Close/Clear');
  });

  const value: KeyboardShortcutsContextType = {
    // Add any methods we want to expose
  };

  return (
    <KeyboardShortcutsContext.Provider value={value}>
      {children}
    </KeyboardShortcutsContext.Provider>
  );
}