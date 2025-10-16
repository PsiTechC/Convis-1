'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface CallLog {
  id: string;
  call_sid?: string;
  from?: string;
  from_number?: string;
  to: string;
  direction: 'inbound' | 'outbound' | 'outbound-api' | 'outbound-dial';
  status: string;
  duration?: number | null;
  start_time?: string;
  end_time?: string;
  date_created?: string;
  price?: string;
  price_unit?: string;
  recording_url?: string;
  assistant_id?: string;
  assistant_name?: string;
}

interface DashboardStats {
  totalCalls: number;
  inboundCalls: number;
  outboundCalls: number;
  completedCalls: number;
  failedCalls: number;
  totalDuration: number;
  avgDuration: number;
  totalCost: number;
  answeredRate: number;
}

function DashboardContent({ isDarkMode, userId }: { isDarkMode: boolean; userId: string }) {
  const [callLogs, setCallLogs] = useState<CallLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    totalCalls: 0,
    inboundCalls: 0,
    outboundCalls: 0,
    completedCalls: 0,
    failedCalls: 0,
    totalDuration: 0,
    avgDuration: 0,
    totalCost: 0,
    answeredRate: 0,
  });

  useEffect(() => {
    fetchCallLogs();
  }, [userId]);

  const fetchCallLogs = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_URL}/api/phone-numbers/call-logs/user/${userId}?limit=500`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setCallLogs(data.call_logs || []);
        calculateStats(data.call_logs || []);
      }
    } catch (error) {
      console.error('Error fetching call logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const calculateStats = (logs: CallLog[]) => {
    const totalCalls = logs.length;
    const inboundCalls = logs.filter((log) => log.direction === 'inbound').length;
    const outboundCalls = logs.filter((log) => log.direction.includes('outbound')).length;
    const completedCalls = logs.filter((log) => log.status === 'completed').length;
    const failedCalls = logs.filter((log) => log.status === 'failed' || log.status === 'busy' || log.status === 'no-answer').length;

    const totalDuration = logs.reduce((sum, log) => sum + (log.duration || 0), 0);
    const avgDuration = totalCalls > 0 ? Math.round(totalDuration / totalCalls) : 0;

    const totalCost = logs.reduce((sum, log) => {
      const price = parseFloat(log.price || '0');
      return sum + Math.abs(price);
    }, 0);

    const answeredRate = totalCalls > 0 ? Math.round((completedCalls / totalCalls) * 100) : 0;

    setStats({
      totalCalls,
      inboundCalls,
      outboundCalls,
      completedCalls,
      failedCalls,
      totalDuration,
      avgDuration,
      totalCost,
      answeredRate,
    });
  };

  const getCallsByDay = () => {
    const dailyData: { [key: string]: { date: string; inbound: number; outbound: number; total: number } } = {};

    callLogs.forEach((log) => {
      const date = log.date_created ? new Date(log.date_created).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Unknown';

      if (!dailyData[date]) {
        dailyData[date] = { date, inbound: 0, outbound: 0, total: 0 };
      }

      dailyData[date].total++;
      if (log.direction === 'inbound') {
        dailyData[date].inbound++;
      } else {
        dailyData[date].outbound++;
      }
    });

    return Object.values(dailyData).slice(-14);
  };

  const getCallStatusData = () => {
    const statusCounts: { [key: string]: number } = {};

    callLogs.forEach((log) => {
      const status = log.status || 'unknown';
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    });

    return Object.entries(statusCounts).map(([name, value]) => ({ name, value }));
  };

  const getDurationDistribution = () => {
    const ranges = [
      { name: '0-30s', min: 0, max: 30, count: 0 },
      { name: '31-60s', min: 31, max: 60, count: 0 },
      { name: '1-3m', min: 61, max: 180, count: 0 },
      { name: '3-5m', min: 181, max: 300, count: 0 },
      { name: '5m+', min: 301, max: Infinity, count: 0 },
    ];

    callLogs.forEach((log) => {
      const duration = log.duration || 0;
      const range = ranges.find((r) => duration >= r.min && duration <= r.max);
      if (range) range.count++;
    });

    return ranges.map(({ name, count }) => ({ name, count }));
  };

  const getRecentCalls = () => {
    return [...callLogs]
      .sort((a, b) => {
        const dateA = new Date(a.date_created || 0).getTime();
        const dateB = new Date(b.date_created || 0).getTime();
        return dateB - dateA;
      })
      .slice(0, 5);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const COLORS = ['#7C3AED', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#6366F1'];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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

