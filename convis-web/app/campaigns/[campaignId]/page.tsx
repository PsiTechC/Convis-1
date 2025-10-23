'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { NAV_ITEMS, NavigationItem } from '../../components/Navigation';
import { TopBar } from '../../components/TopBar';
import CreateCampaignModal from '../create-campaign-modal';
import LeadViewerModal from '../components/LeadViewerModal';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Campaign {
  id?: string;
  _id?: string;
  name: string;
  country: string;
  status: string;
  caller_id: string;
  working_window: {
    timezone: string;
    start: string;
    end: string;
    days: number[];
  };
  retry_policy: {
    max_attempts: number;
    retry_after_minutes: number[];
  };
  pacing: {
    calls_per_minute: number;
    max_concurrent: number;
  };
  start_at?: string | null;
  stop_at?: string | null;
  calendar_enabled?: boolean;
  system_prompt_override?: string | null;
  database_config?: {
    enabled?: boolean;
    type?: string;
    host?: string;
    port?: string;
    database?: string;
    username?: string;
    table_name?: string;
    search_columns?: string[];
  } | null;
  created_at: string;
  updated_at: string;
}

interface CampaignStats {
  total_leads: number;
  queued: number;
  completed: number;
  failed: number;
  no_answer: number;
  busy: number;
  calling: number;
  avg_sentiment_score?: number | null;
  calendar_bookings: number;
  total_calls: number;
  avg_call_duration?: number | null;
}

interface Lead {
  id: string;
  first_name?: string | null;
  last_name?: string | null;
  name?: string | null;
  email?: string | null;
  e164?: string | null;
  raw_number?: string | null;
  batch_name?: string | null;
  status: string;
  attempts: number;
  timezone?: string | null;
  custom_fields?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

type StoredUser = {
  id?: string;
  _id?: string;
  clientId?: string;
  name?: string;
  fullName?: string;
  firstName?: string;
  lastName?: string;
  username?: string;
  email?: string;
  [key: string]: unknown;
};


function formatDateTime(value?: string | null) {
  if (!value) return 'Not scheduled';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatMinutesList(values: number[]) {
  if (!values?.length) return '—';
  return values.join(', ');
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return '—';
  const total = Math.round(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

  const getLeadDisplayName = (lead: Lead) => {
    if (lead.first_name || lead.last_name) {
      const combined = `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim();
      if (combined) {
        return combined;
      }
    }
    return lead.name || '—';
  };

export default function CampaignDetailPage() {
  const router = useRouter();
  const params = useParams<{ campaignId: string }>();
  const campaignId = useMemo(() => {
    if (!params) return '';
    const value = params.campaignId;
    return Array.isArray(value) ? value[0] : value;
  }, [params]);

  const [user, setUser] = useState<StoredUser | null>(null);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeNav, setActiveNav] = useState('Campaigns');
  const [isTestingCall, setIsTestingCall] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigationItems = useMemo(() => NAV_ITEMS, []);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isLeadViewerOpen, setIsLeadViewerOpen] = useState(false);

  const displayName = useMemo(() => {
    if (!user) return '';
    const possible = [
      user.name,
      user.fullName,
      user.firstName && user.lastName ? `${user.firstName} ${user.lastName}` : undefined,
      user.firstName,
      user.username,
      user.email,
    ].find((value) => typeof value === 'string' && value.trim().length > 0);
    return possible ? String(possible).trim() : '';
  }, [user]);

  const userInitial = useMemo(() => {
    if (!displayName) return 'U';
    return displayName.charAt(0).toUpperCase();
  }, [displayName]);

  const userGreeting = useMemo(() => {
    if (!displayName) return undefined;
    if (displayName.includes('@')) {
      return displayName.split('@')[0];
    }
    return displayName.split(' ')[0];
  }, [displayName]);

  const userIdValue = useMemo(() => {
    return (user?.id || user?._id || user?.clientId || '') as string;
  }, [user]);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }

    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');

    if (!token || !userStr) {
      router.push('/login');
      return;
    }

    const parsedUser: StoredUser = JSON.parse(userStr);
    setUser(parsedUser);
  }, [router]);

  const resolvedCampaignId = useMemo(() => {
    return campaignId || '';
  }, [campaignId]);

  const fetchCampaign = useCallback(async () => {
    if (!resolvedCampaignId) return;
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/campaigns/${resolvedCampaignId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch campaign');
      }
      const data = await response.json();
      setCampaign(data);
    } catch (err) {
      console.error('Error fetching campaign', err);
      setError('Unable to load campaign details.');
    } finally {
      setIsLoading(false);
    }
  }, [resolvedCampaignId]);

  const fetchStats = useCallback(async () => {
    if (!resolvedCampaignId) return;
    try {
      const response = await fetch(`${API_URL}/api/campaigns/${resolvedCampaignId}/stats`);
      if (!response.ok) {
        throw new Error('Failed to fetch stats');
      }
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats', err);
    }
  }, [resolvedCampaignId]);

  const fetchLeads = useCallback(async () => {
    if (!resolvedCampaignId) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/campaigns/${resolvedCampaignId}/leads?limit=20`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) {
        throw new Error('Failed to fetch leads');
      }
      const data = await response.json();
      setLeads(data || []);
    } catch (err) {
      console.error('Error fetching leads', err);
    }
  }, [resolvedCampaignId]);

  useEffect(() => {
    if (!resolvedCampaignId) return;
    fetchCampaign();
    fetchStats();
    fetchLeads();
  }, [resolvedCampaignId, fetchCampaign, fetchStats, fetchLeads]);

  const handleNavigation = (navItem: NavigationItem) => {
    setActiveNav(navItem.name);
    router.push(navItem.href);
  };

  const toggleTheme = () => {
    const newTheme = !isDarkMode;
    setIsDarkMode(newTheme);
    localStorage.setItem('theme', newTheme ? 'dark' : 'light');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  const handleStatusUpdate = async (status: 'running' | 'paused' | 'stopped') => {
    if (!resolvedCampaignId) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/campaigns/${resolvedCampaignId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update campaign status');
      }

      await fetchCampaign();
      await fetchStats();
      await fetchLeads();
      alert(`Campaign ${status === 'running' ? 'started' : status === 'paused' ? 'paused' : 'stopped'} successfully.`);
    } catch (err) {
      console.error('Error updating campaign status', err);
      alert(err instanceof Error ? err.message : 'Failed to update campaign status');
    }
  };

  const handleTestCall = async () => {
    if (!resolvedCampaignId || isTestingCall) return;
    try {
      setIsTestingCall(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/campaigns/${resolvedCampaignId}/test-call`, {
        method: 'POST',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Unable to initiate test call');
      }

      const data = await response.json();
      await fetchStats();
      await fetchLeads();
      alert(data.message || 'Test call initiated successfully.');
    } catch (err) {
      console.error('Error triggering test call', err);
      alert(err instanceof Error ? err.message : 'Failed to trigger test call');
    } finally {
      setIsTestingCall(false);
    }
  };

  const statusBadgeClass = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'completed':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'stopped':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

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

          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navigationItems.map((item) => (
              <button
                key={item.name}
                onClick={() => handleNavigation(item)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  activeNav === item.name
                    ? `${isDarkMode ? 'bg-primary/20 text-primary' : 'bg-primary/10 text-primary'} font-semibold`
                    : `${isDarkMode ? 'text-gray-400 hover:bg-gray-700 hover:text-white' : 'text-neutral-mid hover:bg-neutral-light hover:text-neutral-dark'}`
                } ${isSidebarCollapsed ? 'justify-center' : ''}`}
              >
                <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {item.icon}
                </svg>
                {!isSidebarCollapsed && <span className="text-sm">{item.name}</span>}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      <div className={`${isSidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64'} transition-all duration-300`}>
        <TopBar
          isDarkMode={isDarkMode}
          toggleTheme={toggleTheme}
          onLogout={handleLogout}
          userInitial={userInitial}
          userLabel={userGreeting}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
          collapseSearchOnMobile
        />

        <main className="p-6 space-y-6">
          <button
            onClick={() => router.push('/campaigns')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${isDarkMode ? 'border-gray-700 text-gray-300 hover:bg-gray-800' : 'border-neutral-mid/20 text-dark hover:bg-neutral-light'} transition-colors text-sm font-medium`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Campaigns
          </button>

          <div>
            <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-dark'}`}>Campaign Details</h1>
            <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>Review configuration and trigger an instant test call.</p>
          </div>

          {error && (
            <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800 text-red-300' : 'bg-red-50 border-red-200 text-red-700'} border rounded-xl px-4 py-3`}>
              {error}
            </div>
          )}

          {isLoading || !campaign ? (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : (
            <>
              <section className={`${isDarkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-dark'} rounded-2xl p-6 shadow-sm`}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold mb-1">{campaign.name}</h2>
                    <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                      {campaign.country} • Caller ID {campaign.caller_id}
                    </p>
                    <p className={`${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'} text-sm mt-2`}>
                      Created {formatDateTime(campaign.created_at)} • Updated {formatDateTime(campaign.updated_at)}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusBadgeClass(campaign.status)}`}>
                    {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                  </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
                  <div className={`${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'} rounded-xl p-4`}>
                    <h3 className="text-sm font-semibold mb-2">Working Window</h3>
                    <p className="text-sm">
                      {campaign.working_window.start} – {campaign.working_window.end} ({campaign.working_window.timezone})
                    </p>
                    <p className="text-xs mt-1">
                      Days: {campaign.working_window.days.map((d) => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d]).join(', ')}
                    </p>
                  </div>
                  <div className={`${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'} rounded-xl p-4`}>
                    <h3 className="text-sm font-semibold mb-2">Schedule</h3>
                    <p className="text-sm">Start: {formatDateTime(campaign.start_at)}</p>
                    <p className="text-sm mt-1">Stop: {formatDateTime(campaign.stop_at)}</p>
                  </div>
                  <div className={`${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'} rounded-xl p-4`}>
                    <h3 className="text-sm font-semibold mb-2">Retry Policy</h3>
                    <p className="text-sm">Max attempts: {campaign.retry_policy.max_attempts}</p>
                    <p className="text-sm mt-1">Delays (min): {formatMinutesList(campaign.retry_policy.retry_after_minutes)}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-3 mt-6">
                  <button
                    onClick={() => handleStatusUpdate('running')}
                    className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors text-sm font-semibold"
                  >
                    Start Campaign
                  </button>
                  <button
                    onClick={() => handleStatusUpdate('paused')}
                    className={`px-4 py-2 rounded-lg ${isDarkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-neutral-light text-dark hover:bg-neutral-mid/20'} transition-colors text-sm font-semibold`}
                  >
                    Pause Campaign
                  </button>
                  <button
                    onClick={() => handleStatusUpdate('stopped')}
                    className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors text-sm font-semibold"
                  >
                    Stop Campaign
                  </button>
                  <button
                    onClick={handleTestCall}
                    disabled={isTestingCall}
                    className={`px-4 py-2 rounded-lg ${isTestingCall ? 'bg-gray-400 cursor-not-allowed text-white' : 'bg-green-500 text-white hover:bg-green-600'} transition-colors text-sm font-semibold flex items-center gap-2`}
                  >
                    {isTestingCall ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Testing...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
                        </svg>
                        Instant Test Call
                      </>
                    )}
                  </button>
                </div>

                <div className="flex flex-wrap gap-3 mt-4">
                  <button
                    onClick={() => setIsEditModalOpen(true)}
                    className={`px-4 py-2 rounded-lg border ${isDarkMode ? 'border-gray-600 text-white hover:bg-gray-700' : 'border-neutral-mid/20 text-dark hover:bg-neutral-light'} transition-colors text-sm font-semibold`}
                  >
                    Edit Campaign
                  </button>
                  <button
                    onClick={() => setIsUploadModalOpen(true)}
                    className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors text-sm font-semibold"
                  >
                    Upload Leads CSV
                  </button>
                  <button
                    onClick={() => setIsLeadViewerOpen(true)}
                    className={`px-4 py-2 rounded-lg ${isDarkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-neutral-light text-dark hover:bg-neutral-mid/20'} transition-colors text-sm font-semibold`}
                  >
                    View All Leads
                  </button>
                </div>
              </section>

              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className={`${isDarkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-dark'} rounded-2xl p-6 shadow-sm`}>
                  <h3 className="text-lg font-semibold mb-4">Performance</h3>
                  {stats ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Total Leads</p>
                        <p className="text-2xl font-bold">{stats.total_leads}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Queued</p>
                        <p className="text-2xl font-bold text-blue-500">{stats.queued}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Completed</p>
                        <p className="text-2xl font-bold text-green-500">{stats.completed}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Failed</p>
                        <p className="text-2xl font-bold text-red-500">{stats.failed}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>No Answer</p>
                        <p className="text-2xl font-bold">{stats.no_answer}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Busy</p>
                        <p className="text-2xl font-bold">{stats.busy}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Avg Sentiment</p>
                        <p className="text-2xl font-bold">{stats.avg_sentiment_score != null ? stats.avg_sentiment_score.toFixed(2) : '—'}</p>
                      </div>
                      <div>
                        <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm`}>Avg Call Duration</p>
                        <p className="text-2xl font-bold">{formatDuration(stats.avg_call_duration)}</p>
                      </div>
                    </div>
                  ) : (
                    <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>No statistics available yet.</p>
                  )}
                </div>

                <div className={`${isDarkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-dark'} rounded-2xl p-6 shadow-sm`}>
                  <h3 className="text-lg font-semibold mb-4">Configuration</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} uppercase text-xs font-semibold`}>Calendar Booking</p>
                      <p>{campaign.calendar_enabled ? 'Enabled' : 'Disabled'}</p>
                    </div>
                    <div>
                      <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} uppercase text-xs font-semibold`}>System Prompt Override</p>
                      <p>{campaign.system_prompt_override ? campaign.system_prompt_override : 'Using assistant default prompt.'}</p>
                    </div>
                    <div>
                      <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} uppercase text-xs font-semibold`}>Database Lookup</p>
                      {campaign.database_config?.enabled ? (
                        <ul className="list-disc pl-5 space-y-1">
                          <li>Type: {campaign.database_config.type || 'postgresql'}</li>
                          <li>Host: {campaign.database_config.host || '—'}</li>
                          <li>Database: {campaign.database_config.database || '—'}</li>
                          <li>Table: {campaign.database_config.table_name || '—'}</li>
                          <li>Search Columns: {campaign.database_config.search_columns?.join(', ') || '—'}</li>
                        </ul>
                      ) : (
                        <p>Disabled</p>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              <section className={`${isDarkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-dark'} rounded-2xl p-6 shadow-sm`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Recent Leads</h3>
                  <button
                    onClick={() => setIsLeadViewerOpen(true)}
                    className={`text-sm font-medium ${isDarkMode ? 'text-primary' : 'text-primary'} hover:underline`}
                  >
                    View All
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                    <thead className={isDarkMode ? 'bg-gray-900 text-gray-300' : 'bg-neutral-light text-gray-600'}>
                      <tr>
                        <th className="px-4 py-2 text-left font-semibold">Batch</th>
                        <th className="px-4 py-2 text-left font-semibold">Lead</th>
                        <th className="px-4 py-2 text-left font-semibold">Contact Number</th>
                        <th className="px-4 py-2 text-left font-semibold">Email</th>
                        <th className="px-4 py-2 text-left font-semibold">Status</th>
                        <th className="px-4 py-2 text-left font-semibold">Attempts</th>
                        <th className="px-4 py-2 text-left font-semibold">Timezone</th>
                        <th className="px-4 py-2 text-left font-semibold">Updated</th>
                      </tr>
                    </thead>
                    <tbody className={isDarkMode ? 'divide-y divide-gray-700' : 'divide-y divide-gray-200'}>
                      {leads.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                            No leads found for this campaign.
                          </td>
                        </tr>
                      ) : (
                        leads.map((lead) => (
                          <tr key={lead.id}>
                            <td className="px-4 py-2">{lead.batch_name || '—'}</td>
                            <td className="px-4 py-2">{getLeadDisplayName(lead)}</td>
                            <td className="px-4 py-2 font-mono">{lead.e164 || lead.raw_number || '—'}</td>
                            <td className="px-4 py-2">{lead.email || '—'}</td>
                            <td className="px-4 py-2">
                              <span className="inline-flex items-center px-2 py-1 rounded-full bg-neutral-light text-xs font-medium dark:bg-gray-900">
                                {lead.status}
                              </span>
                            </td>
                            <td className="px-4 py-2">{lead.attempts}</td>
                            <td className="px-4 py-2">{lead.timezone || '—'}</td>
                            <td className="px-4 py-2">{formatDateTime(lead.updated_at)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </main>
      </div>

      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        ></div>
      )}

      {campaign && userIdValue && (
        <>
          <CreateCampaignModal
            isOpen={isEditModalOpen}
            onClose={() => setIsEditModalOpen(false)}
            onSuccess={() => {
              fetchCampaign();
              fetchStats();
            }}
            isDarkMode={isDarkMode}
            userId={userIdValue}
            mode="edit"
            campaignId={resolvedCampaignId}
            initialCampaign={campaign}
            initialStep={1}
          />
          <CreateCampaignModal
            isOpen={isUploadModalOpen}
            onClose={() => setIsUploadModalOpen(false)}
            onSuccess={() => {
              fetchStats();
              fetchLeads();
            }}
            isDarkMode={isDarkMode}
            userId={userIdValue}
            mode="edit"
            campaignId={resolvedCampaignId}
            initialCampaign={campaign}
            initialStep={3}
          />
          <LeadViewerModal
            isOpen={isLeadViewerOpen}
            onClose={() => setIsLeadViewerOpen(false)}
            campaignId={resolvedCampaignId}
            isDarkMode={isDarkMode}
          />
        </>
      )}
    </div>
  );
}
