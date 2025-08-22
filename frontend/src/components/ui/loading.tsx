"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <Loader2
      className={cn(
        'animate-spin text-muted-foreground',
        sizeClasses[size],
        className
      )}
    />
  )
}

interface LoadingOverlayProps {
  isLoading: boolean
  children: React.ReactNode
  className?: string
  loadingText?: string
}

export function LoadingOverlay({
  isLoading,
  children,
  className,
  loadingText = 'Loading...'
}: LoadingOverlayProps) {
  return (
    <div className={cn('relative', className)}>
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="flex flex-col items-center space-y-2">
            <LoadingSpinner size="lg" />
            <p className="text-sm text-muted-foreground">{loadingText}</p>
          </div>
        </div>
      )}
    </div>
  )
}

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
    />
  )
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4">
          <Skeleton className="h-4 w-[250px]" />
          <Skeleton className="h-4 w-[200px]" />
          <Skeleton className="h-4 w-[150px]" />
          <Skeleton className="h-4 w-[100px]" />
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border p-6 space-y-3">
      <Skeleton className="h-4 w-[250px]" />
      <Skeleton className="h-4 w-[200px]" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-[80%]" />
      </div>
    </div>
  )
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-lg border p-6 space-y-2">
          <Skeleton className="h-4 w-[100px]" />
          <Skeleton className="h-8 w-[60px]" />
          <Skeleton className="h-3 w-[120px]" />
        </div>
      ))}
    </div>
  )
}

interface FullPageLoadingProps {
  text?: string
}

export function FullPageLoading({ text = 'Loading...' }: FullPageLoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <LoadingSpinner size="lg" />
      <p className="text-lg text-muted-foreground">{text}</p>
    </div>
  )
}

interface InlineLoadingProps {
  text?: string
  size?: 'sm' | 'md' | 'lg'
}

export function InlineLoading({ text = 'Loading...', size = 'sm' }: InlineLoadingProps) {
  return (
    <div className="flex items-center space-x-2">
      <LoadingSpinner size={size} />
      <span className="text-sm text-muted-foreground">{text}</span>
    </div>
  )
}

interface ButtonLoadingProps {
  isLoading: boolean
  children: React.ReactNode
  loadingText?: string
  className?: string
}

export function ButtonLoading({
  isLoading,
  children,
  loadingText,
  className
}: ButtonLoadingProps) {
  return (
    <div className={cn('flex items-center space-x-2', className)}>
      {isLoading && <LoadingSpinner size="sm" />}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </div>
  )
}

// Higher-order component for wrapping content with loading state
interface WithLoadingProps {
  isLoading: boolean
  fallback?: React.ReactNode
  children: React.ReactNode
}

export function WithLoading({ isLoading, fallback, children }: WithLoadingProps) {
  if (isLoading) {
    return fallback || <InlineLoading />
  }

  return <>{children}</>
}

// Progressive loading component
interface ProgressiveLoadingProps {
  stages: {
    name: string
    completed: boolean
  }[]
  currentStage?: string
}

export function ProgressiveLoading({ stages, currentStage }: ProgressiveLoadingProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2">
        <LoadingSpinner size="sm" />
        <span className="text-sm font-medium">Loading...</span>
      </div>

      <div className="space-y-2">
        {stages.map((stage, index) => (
          <div key={stage.name} className="flex items-center space-x-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              stage.completed
                ? 'bg-green-500'
                : currentStage === stage.name
                  ? 'bg-blue-500 animate-pulse'
                  : 'bg-gray-300'
            )} />
            <span className={cn(
              'text-xs',
              stage.completed
                ? 'text-green-600'
                : currentStage === stage.name
                  ? 'text-blue-600'
                  : 'text-muted-foreground'
            )}>
              {stage.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Data loading wrapper with error handling
interface DataLoadingWrapperProps<T> {
  data: T | null
  isLoading: boolean
  error: Error | null
  children: (data: T) => React.ReactNode
  loadingFallback?: React.ReactNode
  errorFallback?: (error: Error) => React.ReactNode
  emptyFallback?: React.ReactNode
}

export function DataLoadingWrapper<T>({
  data,
  isLoading,
  error,
  children,
  loadingFallback,
  errorFallback,
  emptyFallback
}: DataLoadingWrapperProps<T>) {
  if (isLoading) {
    return <>{loadingFallback || <InlineLoading />}</>
  }

  if (error) {
    return <>{errorFallback ? errorFallback(error) : (
      <div className="text-red-600 text-sm">Error: {error.message}</div>
    )}</>
  }

  if (!data) {
    return <>{emptyFallback || (
      <div className="text-muted-foreground text-sm">No data available</div>
    )}</>
  }

  return <>{children(data)}</>
}