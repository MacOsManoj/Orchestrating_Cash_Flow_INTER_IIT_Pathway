import { useState } from 'react';
import { Search } from 'lucide-react';
import { AlertIcon, NotificationIcon } from '@/components/icons';

export interface Tab {
  id: string
  label: string
  component: React.ComponentType
  closeable?: boolean
}

interface TopBarProps {
  tabs?: Tab[]
  activeTabId?: string
  onTabClick?: (tabId: string) => void
  onTabClose?: (tabId: string, e: React.MouseEvent) => void
  onTabReorder?: (fromIndex: number, toIndex: number) => void
}

export function TopBar() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="h-[48px] flex items-center justify-end px-3 gap-3 relative">
      {/* Right section - Icons and Search */}
      <div className="flex items-center gap-3">
        {/* Alerts Icon */}
        <button
          className="relative p-2 hover:bg-card/50 rounded-md transition-colors group"
          aria-label="Alerts"
        >
          <AlertIcon className="text-muted-foreground group-hover:text-accent transition-colors" size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full" />
        </button>

        {/* Notifications Icon */}
        <button
          className="relative p-2 hover:bg-card/50 rounded-md transition-colors group"
          aria-label="Notifications"
        >
          <NotificationIcon className="text-muted-foreground group-hover:text-accent transition-colors" size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent rounded-full" />
        </button>

        {/* Search Bar */}
        <div className="relative ml-2 mr-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={16} />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64 pl-9 pr-4 py-2 bg-card/30 border border-border/50 rounded-md text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-all h-9"
          />
        </div>
      </div>
    </div>
  );
}
