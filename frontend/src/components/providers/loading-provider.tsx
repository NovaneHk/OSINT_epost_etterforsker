"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react'

interface LoadingState {
  [key: string]: boolean
}

interface LoadingContextType {
  loading: LoadingState
  setLoading: (key: string, isLoading: boolean) => void
  isLoading: (key: string) => boolean
  isAnyLoading: () => boolean
}

const LoadingContext = createContext<LoadingContextType | undefined>(undefined)

interface LoadingProviderProps {
  children: ReactNode
}

export function LoadingProvider({ children }: LoadingProviderProps) {
  const [loading, setLoadingState] = useState<LoadingState>({})

  const setLoading = (key: string, isLoading: boolean) => {
    setLoadingState(prev => ({
      ...prev,
      [key]: isLoading
    }))
  }

  const isLoading = (key: string) => {
    return loading[key] || false
  }

  const isAnyLoading = () => {
    return Object.values(loading).some(Boolean)
  }

  return (
    <LoadingContext.Provider value={{
      loading,
      setLoading,
      isLoading,
      isAnyLoading
    }}>
      {children}
    </LoadingContext.Provider>
  )
}

export function useLoading() {
  const context = useContext(LoadingContext)
  if (context === undefined) {
    throw new Error('useLoading must be used within a LoadingProvider')
  }
  return context
}

// Loading hook with automatic cleanup
export function useLoadingState(key: string) {
  const { setLoading, isLoading } = useLoading()

  const startLoading = () => setLoading(key, true)
  const stopLoading = () => setLoading(key, false)
  const isCurrentlyLoading = isLoading(key)

  React.useEffect(() => {
    // Cleanup on unmount
    return () => {
      setLoading(key, false)
    }
  }, [key, setLoading])

  return {
    isLoading: isCurrentlyLoading,
    startLoading,
    stopLoading
  }
}

// HOC for components that need loading state
export function withLoading<P extends object>(
  Component: React.ComponentType<P>,
  loadingKey: string
) {
  return function LoadingWrapper(props: P) {
    const { isLoading } = useLoadingState(loadingKey)

    if (isLoading) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )
    }

    return <Component {...props} />
  }
}