"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  Language,
  TranslationKey,
  TranslationValues,
  setLanguage,
  getCurrentLanguage,
  initializeLanguage,
  t as translate,
  formatDate,
  formatNumber,
  formatCurrency,
  formatPercentage,
  formatFileSize,
  pluralize,
  getValidationMessage,
  getErrorMessage,
  getStatusText,
  getActionText,
  getAvailableLanguages
} from '@/lib/i18n';

interface I18nContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, values?: TranslationValues) => string;
  formatDate: (date: Date | string, format?: 'short' | 'long' | 'time') => string;
  formatNumber: (number: number, options?: Intl.NumberFormatOptions) => string;
  formatCurrency: (amount: number, currency?: string) => string;
  formatPercentage: (value: number, decimals?: number) => string;
  formatFileSize: (bytes: number) => string;
  pluralize: (count: number, singular: string, plural?: string) => string;
  getValidationMessage: (rule: string, params?: Record<string, any>) => string;
  getErrorMessage: (error: string) => string;
  getStatusText: (status: string) => string;
  getActionText: (action: string) => string;
  availableLanguages: Array<{ code: Language; name: string }>;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

interface I18nProviderProps {
  children: ReactNode;
}

export function I18nProvider({ children }: I18nProviderProps) {
  const [language, setCurrentLanguage] = useState<Language>(() => initializeLanguage());

  const handleLanguageChange = (newLanguage: Language) => {
    setLanguage(newLanguage);
    setCurrentLanguage(newLanguage);
  };

  useEffect(() => {
    // Initialize language on mount
    const initialLang = initializeLanguage();
    if (initialLang !== language) {
      setCurrentLanguage(initialLang);
    }
  }, [language]);

  const contextValue: I18nContextType = {
    language,
    setLanguage: handleLanguageChange,
    t: translate,
    formatDate,
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatFileSize,
    pluralize,
    getValidationMessage,
    getErrorMessage,
    getStatusText,
    getActionText,
    availableLanguages: getAvailableLanguages(),
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

// Convenience hooks for common use cases
export function useTranslation() {
  const { t } = useI18n();
  return { t };
}

export function useFormatters() {
  const {
    formatDate,
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatFileSize,
    pluralize
  } = useI18n();

  return {
    formatDate,
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatFileSize,
    pluralize,
  };
}

export function useValidation() {
  const { getValidationMessage } = useI18n();
  return { getValidationMessage };
}

export function useLanguage() {
  const { language, setLanguage, availableLanguages } = useI18n();
  return { language, setLanguage, availableLanguages };
}

// HOC for components that need translations
export function withTranslation<T extends object>(
  Component: React.ComponentType<T>
) {
  const WrappedComponent = (props: T) => {
    const { t } = useI18n();
    return <Component {...props} t={t} />;
  };

  WrappedComponent.displayName = `withTranslation(${Component.displayName || Component.name})`;

  return WrappedComponent;
}