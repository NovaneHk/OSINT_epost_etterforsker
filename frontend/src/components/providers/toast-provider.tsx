'use client';

import { Toaster } from '@/components/ui/toaster';

interface ToastProviderProps {
  children?: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  return (
    <>
      {children}
      <Toaster />
    </>
  );
}