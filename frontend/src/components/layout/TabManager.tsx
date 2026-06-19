import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

export interface Tab {
  id: string
  label: string
  component: React.ComponentType
  closeable?: boolean
}

interface TabManagerProps {
  tabs: Tab[]
  activeTabId?: string
  onTabsChange?: (tabs: Tab[], newActiveId?: string) => void
  onActiveTabChange?: (tabId: string) => void
  className?: string
}

export function TabManager({ tabs: initialTabs, activeTabId: externalActiveTabId, onTabsChange, onActiveTabChange, className }: TabManagerProps) {
  const [tabs, setTabs] = useState<Tab[]>(initialTabs)
  const [activeTabId, setActiveTabId] = useState<string>(externalActiveTabId || initialTabs[0]?.id || '')
  
  // Sync with external active tab
  useEffect(() => {
    if (externalActiveTabId && externalActiveTabId !== activeTabId) {
      setActiveTabId(externalActiveTabId)
    }
  }, [externalActiveTabId, activeTabId])
  
  // Sync tabs with parent
  useEffect(() => {
    setTabs(initialTabs)
  }, [initialTabs])

  const handleCloseTab = useCallback((tabId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    
    const tabToClose = tabs.find(t => t.id === tabId)
    if (tabToClose && tabToClose.closeable === false) return
    
    const newTabs = tabs.filter(t => t.id !== tabId)
    setTabs(newTabs)
    
    let newActiveId = activeTabId
    if (activeTabId === tabId && newTabs.length > 0) {
      const closedIndex = tabs.findIndex(t => t.id === tabId)
      const newActiveTab = newTabs[Math.max(0, closedIndex - 1)]
      newActiveId = newActiveTab.id
      setActiveTabId(newActiveId)
    }
    
    onTabsChange?.(newTabs, newActiveId)
  }, [tabs, activeTabId, onTabsChange])

  const handleTabClick = useCallback((tabId: string) => {
    setActiveTabId(tabId)
    onActiveTabChange?.(tabId)
  }, [onActiveTabChange])

  const activeTab = tabs.find(t => t.id === activeTabId)

  return (
    <Tabs className={className}>
      <TabsList>
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.id}
            active={activeTabId === tab.id}
            closeable={tab.closeable !== false}
            onClick={() => handleTabClick(tab.id)}
            onClose={(e) => handleCloseTab(tab.id, e)}
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      
      <AnimatePresence mode="wait">
        {activeTab && (
          <TabsContent key={activeTabId}>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              <activeTab.component />
            </motion.div>
          </TabsContent>
        )}
      </AnimatePresence>
    </Tabs>
  )
}
