'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

type RangeOption = 'total' | 'last_7d' | 'last_30d' | 'last_90d' | 'current_year';

interface AssistantSentiment {
  positive: number;
  negative: number;
  neutral: number;
  unknown: number;
}

interface AssistantSummaryItem {
  assistant_id?: string | null;
  assistant_name: string;
  total_calls: number;
  total_duration_seconds: number;
  total_cost: number;
  sentiment: AssistantSentiment;
  status_counts: Record<string, number>;
}

interface DashboardAssistantSummary {
  timeframe: string;
  total_cost: number;
  total_calls: number;
  assistants: AssistantSummaryItem[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [activeNav, setActiveNav] = useState('Dashboard');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [callLogs, setCallLogs] = useState<any[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [stats, setStats] = useState({
    totalCalls: 0,
    inboundCalls: 0,
    outboundCalls: 0,
    completedCalls: 0,
    answeredRate: 0,
    avgDuration: 0,
    totalDuration: 0,
    totalCost: 0,
  });
  const [selectedSummaryRange, setSelectedSummaryRange] = useState<RangeOption>('total');
  const [assistantSummary, setAssistantSummary] = useState<DashboardAssistantSummary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const rangeOptions: { label: string; value: RangeOption }[] = [
    { label: 'Total Cost', value: 'total' },
    { label: 'Last 7D', value: 'last_7d' },
    { label: 'Last 30D', value: 'last_30d' },
    { label: 'Last 90D', value: 'last_90d' },
    { label: 'Current Year', value: 'current_year' },
  ];
  const positiveStatuses = ['completed'];
  const negativeStatuses = ['failed', 'busy', 'no-answer', 'canceled', 'not-answered'];
  const neutralStatuses = ['in-progress', 'queued', 'ringing'];

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');

    if (!token) {
      router.push('/login');
      return;
    }

    if (userStr) {
      const parsedUser = JSON.parse(userStr);
      setUser(parsedUser);
      const resolvedUserId = parsedUser.id || parsedUser._id || parsedUser.clientId;
      if (resolvedUserId) {
        fetchCallLogs(resolvedUserId);
      }
    }

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }
  }, [router]);

  useEffect(() => {
    if (!user) return;
    const resolvedUserId = user.id || user._id || user.clientId;
    if (!resolvedUserId) return;
    fetchAssistantSummary(resolvedUserId, selectedSummaryRange);
  }, [user, selectedSummaryRange]);

  const fetchAssistantSummary = async (userId: string, range: RangeOption) => {
    try {
      setIsSummaryLoading(true);
      setSummaryError(null);
      const token = localStorage.getItem('token');
      if (!token) {
        setSummaryError('You are not authenticated. Please sign in again.');
        setAssistantSummary(null);
        return;
      }
      const response = await fetch(`${API_URL}/api/dashboard/assistant-summary/${userId}?timeframe=${range}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch assistant summary');
      }

      const data = await response.json();
      setAssistantSummary(data);
    } catch (error) {
      console.error('Error fetching assistant summary:', error);
      if (error instanceof TypeError) {
        setSummaryError('Unable to reach dashboard summary service. Please verify the backend is running.');
      } else {
        setSummaryError(error instanceof Error ? error.message : 'Failed to fetch assistant summary');
      }
      setAssistantSummary(null);
    } finally {
      setIsSummaryLoading(false);
    }
  };

  const fetchCallLogs = async (userId: string) => {
    try {
      setIsLoadingStats(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/phone-numbers/call-logs/user/${userId}?limit=500`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        const logs = data.call_logs || [];
        setCallLogs(logs);

        // Calculate stats
        const totalCalls = logs.length;
        const inboundCalls = logs.filter((log: any) => log.direction === 'inbound').length;
        const outboundCalls = logs.filter((log: any) => log.direction.includes('outbound')).length;
        const completedCalls = logs.filter((log: any) => log.status === 'completed').length;
        const totalDuration = logs.reduce((sum: number, log: any) => sum + (log.duration || 0), 0);
        const avgDuration = totalCalls > 0 ? Math.round(totalDuration / totalCalls) : 0;
        const totalCost = logs.reduce((sum: number, log: any) => sum + Math.abs(parseFloat(log.price || '0')), 0);
        const answeredRate = totalCalls > 0 ? Math.round((completedCalls / totalCalls) * 100) : 0;

        setStats({
          totalCalls,
          inboundCalls,
          outboundCalls,
          completedCalls,
          answeredRate,
          avgDuration,
          totalDuration,
          totalCost,
        });
      }
    } catch (error) {
      console.error('Error fetching call logs:', error);
    } finally {
      setIsLoadingStats(false);
    }
  };

  const formatCurrency = (value: number) => {
    if (!Number.isFinite(value)) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  const getSentimentTotal = (sentiment: AssistantSentiment) =>
    sentiment.positive + sentiment.negative + sentiment.neutral + sentiment.unknown;

  const getStatusBadgeClasses = (status: string) => {
    const normalized = status.toLowerCase();
    if (positiveStatuses.includes(normalized)) {
      return 'bg-green-500/15 text-green-500 border border-green-500/20';
    }
    if (negativeStatuses.includes(normalized)) {
      return 'bg-red-500/15 text-red-500 border border-red-500/20';
    }
    if (neutralStatuses.includes(normalized)) {
      return 'bg-yellow-500/15 text-yellow-600 border border-yellow-500/20';
    }
    return 'bg-gray-500/10 text-gray-500 border border-gray-500/20';
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('clientId');
    localStorage.removeItem('isAdmin');
    router.push('/login');
  };

  const toggleTheme = () => {
    const newTheme = !isDarkMode;
    setIsDarkMode(newTheme);
    localStorage.setItem('theme', newTheme ? 'dark' : 'light');
  };

  const handleNavigation = (navItem: string) => {
    setActiveNav(navItem);
    if (navItem === 'AI Agent') {
      router.push('/ai-agent');
    } else if (navItem === 'Phone Numbers') {
      router.push('/phone-numbers');
    } else if (navItem === 'Call logs') {
      router.push('/phone-numbers?tab=calls');
    } else if (navItem === 'Campaigns') {
      router.push('/campaigns');
    } else if (navItem === 'Settings') {
      router.push('/settings');
    }
  };

  const navigationItems = [
    {
      name: 'Dashboard',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      )
    },
    {
      name: 'AI Agent',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      )
    },
    {
      name: 'Phone Numbers',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
      )
    },
    {
      name: 'Call logs',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      )
    },
    {
      name: 'Campaigns',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
      )
    },
    {
      name: 'Whatsapp',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      )
    },
    {
      name: 'Connect calendar',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      )
    },
    {
      name: 'Settings',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      )
    },
  ];

  const summaryTotalCost = assistantSummary?.total_cost ?? 0;
  const summaryTotalCalls = assistantSummary?.total_calls ?? 0;
  const totalAssistants = assistantSummary?.assistants.length ?? 0;

  if (!user) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark bg-gray-900' : 'bg-neutral-light'}`}>
      {/* Sidebar */}
      <aside
        onMouseEnter={() => setIsSidebarCollapsed(false)}
        onMouseLeave={() => setIsSidebarCollapsed(true)}
        className={`fixed left-0 top-0 h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border-r ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} transition-all duration-300 z-40 ${isSidebarCollapsed ? 'w-20' : 'w-64'} ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-start gap-3'} ${isSidebarCollapsed ? 'px-4' : 'px-6'} py-4 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center flex-shrink-0">
              <DotLottieReact
                src="/microphone-animation.lottie"
                loop
                autoplay
                style={{ width: '24px', height: '24px' }}
              />
            </div>
            {!isSidebarCollapsed && (
              <span className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-neutral-dark'} whitespace-nowrap`}>Convis AI</span>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navigationItems.map((item) => (
              <button
                key={item.name}
                onClick={() => handleNavigation(item.name)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  activeNav === item.name
                    ? `${isDarkMode ? 'bg-primary/20 text-primary' : 'bg-primary/10 text-primary'} font-semibold`
                    : `${isDarkMode ? 'text-gray-400 hover:bg-gray-700 hover:text-white' : 'text-neutral-mid hover:bg-neutral-light hover:text-neutral-dark'}`
                } ${isSidebarCollapsed ? 'justify-center' : ''}`}
              >
                <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {item.icon}
                </svg>
                {!isSidebarCollapsed && (
                  <span className="text-sm">{item.name}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`transition-all duration-300 ${isSidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64'}`}>
        {/* Top Header */}
        <header className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-neutral-mid/10'} border-b sticky top-0 z-30`}>
          <div className="flex items-center justify-between px-6 py-4">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-neutral-light"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Search Bar */}
            <div className="flex-1 max-w-xl mx-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search for article, video or document"
                  className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-neutral-light border-neutral-mid/20 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                />
                <svg className={`w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Right Side Icons */}
            <div className="flex items-center gap-2">
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                {isDarkMode ? (
                  <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-neutral-mid" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>

              {/* Notifications */}
              <button className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors relative`}>
                <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>

              {/* User Avatar */}
              <button onClick={handleLogout} className={`flex items-center gap-2 p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}>
                <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary/80 rounded-full flex items-center justify-center">
                  <span className="text-xs font-bold text-white">
                    {user.email?.[0]?.toUpperCase() || 'U'}
                  </span>
                </div>
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {/* Welcome Section */}
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 mb-6 shadow-sm`}>
            <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
              Hello {user.email?.split('@')[0] || 'User'},
            </h1>
            <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
              Explore content more deeply and effectively.
            </p>
          </div>

          {/* Dashboard Stats */}
          {isLoadingStats ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Total Calls */}
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-purple-500/20 to-purple-600/20 border-purple-500/30' : 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200'} rounded-2xl p-6 border shadow-sm hover:shadow-md transition-all`}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-xl ${isDarkMode ? 'bg-purple-500/30' : 'bg-purple-500'}`}>
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                  </div>
                  <div className={`text-xs font-semibold px-3 py-1 rounded-full ${isDarkMode ? 'bg-purple-500/20 text-purple-300' : 'bg-purple-200 text-purple-700'}`}>
                    Total
                  </div>
                </div>
                <h3 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                  {stats.totalCalls.toLocaleString()}
                </h3>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Total Calls</p>
              </div>

              {/* Inbound Calls */}
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-blue-500/20 to-blue-600/20 border-blue-500/30' : 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200'} rounded-2xl p-6 border shadow-sm hover:shadow-md transition-all`}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-xl ${isDarkMode ? 'bg-blue-500/30' : 'bg-blue-500'}`}>
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                    </svg>
                  </div>
                  <div className={`text-xs font-semibold px-3 py-1 rounded-full ${isDarkMode ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-200 text-blue-700'}`}>
                    Inbound
                  </div>
                </div>
                <h3 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                  {stats.inboundCalls.toLocaleString()}
                </h3>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Incoming Calls</p>
              </div>

              {/* Outbound Calls */}
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-green-500/20 to-green-600/20 border-green-500/30' : 'bg-gradient-to-br from-green-50 to-green-100 border-green-200'} rounded-2xl p-6 border shadow-sm hover:shadow-md transition-all`}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-xl ${isDarkMode ? 'bg-green-500/30' : 'bg-green-500'}`}>
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </div>
                  <div className={`text-xs font-semibold px-3 py-1 rounded-full ${isDarkMode ? 'bg-green-500/20 text-green-300' : 'bg-green-200 text-green-700'}`}>
                    Outbound
                  </div>
                </div>
                <h3 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                  {stats.outboundCalls.toLocaleString()}
                </h3>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Outgoing Calls</p>
              </div>

              {/* Answer Rate */}
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-pink-500/20 to-pink-600/20 border-pink-500/30' : 'bg-gradient-to-br from-pink-50 to-pink-100 border-pink-200'} rounded-2xl p-6 border shadow-sm hover:shadow-md transition-all`}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-xl ${isDarkMode ? 'bg-pink-500/30' : 'bg-pink-500'}`}>
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className={`text-xs font-semibold px-3 py-1 rounded-full ${isDarkMode ? 'bg-pink-500/20 text-pink-300' : 'bg-pink-200 text-pink-700'}`}>
                    Success
                  </div>
                </div>
                <h3 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                  {stats.answeredRate}%
                </h3>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Answer Rate</p>
              </div>
            </div>
          )}

          {/* AI Agent Spend & Sentiment Summary */}
          <section className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 mt-8 shadow-sm`}> 
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
              <div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                  AI Agent Summary
                </h2>
                <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                  Track spending, call volume, and sentiment trends for each deployed assistant.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {rangeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setSelectedSummaryRange(option.value)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      selectedSummaryRange === option.value
                        ? 'bg-primary text-white shadow-lg shadow-primary/20'
                        : isDarkMode
                          ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                          : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-purple-500/15 to-purple-600/20 border-purple-500/30' : 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200'} rounded-2xl p-4 border shadow-sm`}>
                <p className={`text-xs font-semibold uppercase ${isDarkMode ? 'text-purple-200' : 'text-purple-700'}`}>Total Cost</p>
                <h3 className={`text-2xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  {isSummaryLoading ? '—' : formatCurrency(summaryTotalCost)}
                </h3>
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Across all assistants</p>
              </div>
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-blue-500/15 to-blue-600/20 border-blue-500/30' : 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200'} rounded-2xl p-4 border shadow-sm`}>
                <p className={`text-xs font-semibold uppercase ${isDarkMode ? 'text-blue-200' : 'text-blue-700'}`}>Total Calls</p>
                <h3 className={`text-2xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  {isSummaryLoading ? '—' : summaryTotalCalls.toLocaleString()}
                </h3>
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Handled in selected period</p>
              </div>
              <div className={`${isDarkMode ? 'bg-gradient-to-br from-emerald-500/15 to-emerald-600/20 border-emerald-500/30' : 'bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200'} rounded-2xl p-4 border shadow-sm`}>
                <p className={`text-xs font-semibold uppercase ${isDarkMode ? 'text-emerald-200' : 'text-emerald-700'}`}>Active Assistants</p>
                <h3 className={`text-2xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  {isSummaryLoading ? '—' : totalAssistants.toLocaleString()}
                </h3>
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>With call activity</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs mb-4">
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-green-500" /> Positive</div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500" /> Negative</div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-yellow-500" /> Neutral</div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-gray-400" /> No Sentiment</div>
            </div>

            <div className="overflow-x-auto">
              {isSummaryLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin h-10 w-10 border-b-2 border-primary rounded-full"></div>
                </div>
              ) : summaryError ? (
                <div className={`p-4 rounded-xl border ${isDarkMode ? 'border-red-700 bg-red-900/20 text-red-200' : 'border-red-200 bg-red-50 text-red-700'}`}>
                  {summaryError}
                </div>
              ) : assistantSummary && assistantSummary.assistants.length > 0 ? (
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className={isDarkMode ? 'text-gray-300' : 'text-neutral-mid'}>
                      <th className="text-left font-semibold pb-3 pr-4">Agent</th>
                      <th className="text-left font-semibold pb-3 px-4">Amount Spent</th>
                      <th className="text-left font-semibold pb-3 px-4">Total Calls</th>
                      <th className="text-left font-semibold pb-3 pl-4">Sentiment & Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assistantSummary.assistants.map((assistant) => {
                      const sentimentTotal = getSentimentTotal(assistant.sentiment);
                      const segments = [
                        { value: assistant.sentiment.positive, className: 'bg-green-500' },
                        { value: assistant.sentiment.negative, className: 'bg-red-500' },
                        { value: assistant.sentiment.neutral, className: 'bg-yellow-500' },
                        { value: assistant.sentiment.unknown, className: 'bg-gray-400' },
                      ];

                      return (
                        <tr
                          key={assistant.assistant_id || assistant.assistant_name}
                          className={isDarkMode ? 'border-t border-gray-700' : 'border-t border-neutral-mid/10'}
                        >
                          <td className="py-4 pr-4 align-top">
                            <div className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                              {assistant.assistant_name}
                            </div>
                            <div className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                              {assistant.assistant_id ? `ID: ${assistant.assistant_id}` : 'Unassigned number'}
                            </div>
                          </td>
                          <td className={`py-4 px-4 align-top ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            {formatCurrency(assistant.total_cost)}
                          </td>
                          <td className={`py-4 px-4 align-top ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            {assistant.total_calls.toLocaleString()}
                          </td>
                          <td className="py-4 pl-4 align-top">
                            <div className="flex flex-col gap-2">
                              <div className="flex items-center gap-3">
                                <div className="flex-1 h-2 rounded-full overflow-hidden bg-neutral-200 dark:bg-gray-700">
                                  {segments.map((segment, index) => (
                                    <div
                                      key={index}
                                      className={`${segment.className} h-full`}
                                      style={{ width: `${sentimentTotal > 0 ? (segment.value / sentimentTotal) * 100 : 0}%` }}
                                    />
                                  ))}
                                </div>
                                <div className="flex flex-wrap gap-3 text-xs">
                                  <span className="flex items-center gap-1 text-green-500"><span>👍</span>{assistant.sentiment.positive}</span>
                                  <span className="flex items-center gap-1 text-red-500"><span>👎</span>{assistant.sentiment.negative}</span>
                                  <span className="flex items-center gap-1 text-yellow-500"><span>😐</span>{assistant.sentiment.neutral}</span>
                                  <span className="flex items-center gap-1 text-gray-400"><span>❔</span>{assistant.sentiment.unknown}</span>
                                </div>
                              </div>
                              {Object.keys(assistant.status_counts).length > 0 && (
                                <div className="flex flex-wrap gap-2 text-[11px]">
                                  {Object.entries(assistant.status_counts).map(([status, count]) => (
                                    <span
                                      key={status}
                                      className={`px-2 py-1 rounded-lg capitalize ${getStatusBadgeClasses(status)}`}
                                    >
                                      {status.replace(/[-_]/g, ' ')}: {count}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className={`p-6 rounded-xl text-center ${isDarkMode ? 'bg-gray-900 text-gray-300' : 'bg-neutral-light text-neutral-mid'}`}>
                  No assistant activity found for the selected period.
                </div>
              )}
            </div>
          </section>

        </main>
      </div>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        ></div>
      )}
    </div>
  );
}
