import "./App.css";
import { AppLayout } from "@/components/layout/AppLayout";
import { type SidebarItem } from "@/components/layout/Sidebar";
import {
  TrendingUp,
  Shield,
  Briefcase,
  PieChart,
  Settings as SettingsIcon,
  FileText,
  CircleStar,
  MoveUpRight,
} from "lucide-react";
import {
  HomeIcon,
  ExploreIcon,
  PlaygroundIcon,
  CashflowIcon,
  ComplianceIcon,
} from "@/components/icons";
import {
  Dashboard,
  Portfolio,
  Stocks,
  Bonds,
  Playground,
  Risk,
  Performance,
  FXTradingDashboard,
  Settings,
  CommoditiesDashboard,
  Options,
  News,
} from "@/views";
import { ExploreAssets } from "./views/explore-assets";

const sidebarItems: SidebarItem[] = [
  {
    id: "dashboard",
    label: "Home",
    icon: <HomeIcon size={24} />,
    component: Dashboard,
  },
  {
      id: 'explore',
      label: 'Explore Assets',
      icon: <ExploreIcon size={24} />,
      component: ExploreAssets,
  },
  {
    id: "playground",
    label: "Playground",
    icon: <PlaygroundIcon size={24} />,
    component: Playground,
  },
  {
    id: "cashflow",
    label: "Cashflow",
    icon: <CashflowIcon size={24} />,
    component: Performance,
  },
  {
    id: "compliance",
    label: "Compliance",
    icon: <ComplianceIcon size={24} />,
    component: Risk,
  },
  {
    id: "forex",
    label: "Forex",
    icon: <MoveUpRight size={24} />,
    component: FXTradingDashboard,
  },
  {
    id: "news",
    label: "News",
    icon: <FileText size={24} />,
    component: News,
  },
  // Hidden asset views (not shown in sidebar, opened via explore-assets)
  {
    id: "bonds",
    label: "Bonds",
    icon: <FileText size={24} />,
    component: Bonds,
    hidden: true,
  },
  {
    id: "stocks",
    label: "Stocks",
    icon: <FileText size={24} />,
    component: Stocks,
    hidden: true,
  },
  {
    id: "commodities",
    label: "Commodities",
    icon: <FileText size={24} />,
    component: CommoditiesDashboard,
    hidden: true,
  },
];

const defaultTab = {
  id: "dashboard",
  label: "Home",
  component: Dashboard,
  closeable: false,
};

// Initial tabs to test the tab manager
const initialTabs = [defaultTab];

function App() {
  return (
    <AppLayout
      sidebarItems={sidebarItems}
      defaultTab={defaultTab}
      initialTabs={initialTabs}
    />
  );
}

export default App;
