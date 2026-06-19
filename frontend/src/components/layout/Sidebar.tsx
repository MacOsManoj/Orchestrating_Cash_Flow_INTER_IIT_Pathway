import { motion } from 'framer-motion'
import { 
  LayoutDashboard, 
  TrendingUp, 
  Activity,
  Shield,
  Briefcase,
  PieChart,
  Settings,
  FileText
} from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SidebarItem {
  id: string
  label: string
  icon: React.ReactNode
  component: React.ComponentType
  hidden?: boolean  // Hidden items are not shown in sidebar but can be opened programmatically
}

interface SidebarProps {
  items: SidebarItem[]
  activeItem?: string
  onItemClick: (id: string) => void
  className?: string
}

export const defaultSidebarItems: SidebarItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <LayoutDashboard size={20} />,
    component: () => <div>Dashboard</div>
  },
  {
    id: 'portfolio',
    label: 'Portfolio',
    icon: <Briefcase size={20} />,
    component: () => <div>Portfolio</div>
  },
  {
    id: 'stocks',
    label: 'Stocks',
    icon: <TrendingUp size={20} />,
    component: () => <div>Stocks</div>
  },
  {
    id: 'bonds',
    label: 'Bonds',
    icon: <FileText size={20} />,
    component: () => <div>Bonds</div>
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: <Activity size={20} />,
    component: () => <div>Analytics</div>
  },
  {
    id: 'risk',
    label: 'Risk',
    icon: <Shield size={20} />,
    component: () => <div>Risk</div>
  },
  {
    id: 'performance',
    label: 'Performance',
    icon: <PieChart size={20} />,
    component: () => <div>Performance</div>
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: <Settings size={20} />,
    component: () => <div>Settings</div>
  },
  {
    id: 'news',
    label: 'News',
    icon: <FileText size={20} />,
    component: () => <div>News</div>
  }
]

export function Sidebar({ items, activeItem, onItemClick, className }: SidebarProps) {
  // Filter out hidden items
  const visibleItems = items.filter(item => !item.hidden)
  
  return (
    <div className={cn("w-16 bg-background border-r border-border flex flex-col items-stretch py-16", className)}>
      {visibleItems.map((item) => (
        <motion.button
          key={item.id}
          onClick={() => onItemClick(item.id)}
          className={cn(
            "h-14 flex items-center justify-center transition-colors relative group",
            activeItem === item.id 
              ? "bg-card text-accent" 
              : "text-accent hover:bg-card"
          )}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          title={item.label}
        >
          {item.icon}
          {activeItem === item.id && (
            <motion.div
              layoutId="activeIndicator"
              className="absolute left-0 top-0 bottom-0 w-1 bg-accent rounded-r-full"
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            />
          )}
          <div className="absolute left-16 ml-2 px-3 py-1.5 bg-[#0B141A] text-accent text-xs rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50 border border-accent shadow-lg">
            {item.label}
          </div>
        </motion.button>
      ))}
    </div>
  )
}
