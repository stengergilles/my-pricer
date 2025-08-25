import React, { createContext, useContext, useState, ReactNode } from 'react'

interface ApiLoadingContextType {
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  activeOperations: Set<string>
  startOperation: (operationId: string) => void
  endOperation: (operationId: string) => void
}

const ApiLoadingContext = createContext<ApiLoadingContextType | undefined>(undefined)

export const useApiLoading = () => {
  const context = useContext(ApiLoadingContext)
  if (!context) {
    throw new Error('useApiLoading must be used within an ApiLoadingProvider')
  }
  return context
}

interface ApiLoadingProviderProps {
  children: ReactNode
}

export const ApiLoadingProvider: React.FC<ApiLoadingProviderProps> = ({ children }) => {
  const [activeOperations, setActiveOperations] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)

  const startOperation = (operationId: string) => {
    console.log(`🚀 Global Loading: Starting operation ${operationId}`)
    setActiveOperations(prev => {
      const newSet = new Set(prev)
      newSet.add(operationId)
      return newSet
    })
    setIsLoading(true)
  }

  const endOperation = (operationId: string) => {
    console.log(`✅ Global Loading: Ending operation ${operationId}`)
    setActiveOperations(prev => {
      const newSet = new Set(prev)
      newSet.delete(operationId)
      const stillLoading = newSet.size > 0
      setIsLoading(stillLoading)
      console.log(`📊 Global Loading: ${newSet.size} operations remaining, isLoading: ${stillLoading}`)
      return newSet
    })
  }

  const value = {
    isLoading,
    setIsLoading,
    activeOperations,
    startOperation,
    endOperation
  }

  return (
    <ApiLoadingContext.Provider value={value}>
      {children}
    </ApiLoadingContext.Provider>
  )
}
