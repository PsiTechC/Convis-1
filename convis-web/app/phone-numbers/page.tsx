'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { NAV_ITEMS, NavigationItem } from '../components/Navigation';
import { TopBar } from '../components/TopBar';

interface PhoneNumber {
  id: string;
  phone_number: string;
  provider: string;
  friendly_name?: string;
  capabilities?: {
    voice?: boolean;
    sms?: boolean;
    mms?: boolean;
  };
  status: string;
  created_at: string;
  assigned_assistant_id?: string;
  assigned_assistant_name?: string;
  webhook_url?: string;
}

interface AIAssistant {
  id: string;
  name: string;
  system_message: string;
  voice: string;
  temperature: number;
  created_at: string;
  updated_at: string;
}

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
  recording_sid?: string;
  recording_duration?: number;
  transcription_text?: string;
  transcription_sid?: string;
  transcription_url?: string;
  assistant_id?: string;
  assistant_name?: string;
}

interface ServiceProvider {
  id: string;
  name: string;
  logo: string;
  description: string;
  authUrl: string;
  color: string;
  features: string[];
}

function PhoneNumbersPageContent() {
  const router = useRouter();
  const urlSearchParams = useSearchParams();
  const [user, setUser] = useState<any>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [activeNav, setActiveNav] = useState('Phone Numbers');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [callLogs, setCallLogs] = useState<CallLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCalls, setIsLoadingCalls] = useState(false);
  const [lastCallLogsRefresh, setLastCallLogsRefresh] = useState<Date | null>(null);
  const [isProviderModalOpen, setIsProviderModalOpen] = useState(false);
  const [isCredentialsModalOpen, setIsCredentialsModalOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<ServiceProvider | null>(null);
  const [credentials, setCredentials] = useState({ accountSid: '', authToken: '' });
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedPhoneNumber, setSelectedPhoneNumber] = useState<PhoneNumber | null>(null);
  const [activeTab, setActiveTab] = useState<'numbers' | 'calls'>('numbers');
  const [aiAssistants, setAiAssistants] = useState<AIAssistant[]>([]);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedAssistant, setSelectedAssistant] = useState<string>('');
  const [isAssigning, setIsAssigning] = useState(false);
  const [isPurchaseModalOpen, setIsPurchaseModalOpen] = useState(false);
  const [numberSearchParams, setNumberSearchParams] = useState({ areaCode: '', contains: '' });
  const [availableNumbers, setAvailableNumbers] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [selectedNumber, setSelectedNumber] = useState<string>('');
  const [selectedCallLog, setSelectedCallLog] = useState<CallLog | null>(null);
  const [isCallDetailsModalOpen, setIsCallDetailsModalOpen] = useState(false);
  const [isCallModalOpen, setIsCallModalOpen] = useState(false);
  const [selectedPhoneForCall, setSelectedPhoneForCall] = useState<PhoneNumber | null>(null);
  const [callToNumber, setCallToNumber] = useState('');
  const [isInitiatingCall, setIsInitiatingCall] = useState(false);
  const [verifiedCallerIds, setVerifiedCallerIds] = useState<any[]>([]);
  const [isLoadingCallerIds, setIsLoadingCallerIds] = useState(false);

  // Active call tracking
  const [activeCallSid, setActiveCallSid] = useState<string | null>(null);
  const [activeCallStatus, setActiveCallStatus] = useState<string>('');
  const [isCallActive, setIsCallActive] = useState(false);

  // API URL with fallback
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const serviceProviders: ServiceProvider[] = [
    {
      id: 'twilio',
      name: 'Twilio',
      logo: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIyNCIgY3k9IjI0IiByPSIyMCIgZmlsbD0id2hpdGUiLz48Y2lyY2xlIGN4PSIxNyIgY3k9IjE3IiByPSI0IiBmaWxsPSIjRjIyRjQ2Ii8+PGNpcmNsZSBjeD0iMzEiIGN5PSIxNyIgcj0iNCIgZmlsbD0iI0YyMkY0NiIvPjxjaXJjbGUgY3g9IjE3IiBjeT0iMzEiIHI9IjQiIGZpbGw9IiNGMjJGNDYiLz48Y2lyY2xlIGN4PSIzMSIgY3k9IjMxIiByPSI0IiBmaWxsPSIjRjIyRjQ2Ii8+PC9zdmc+',
      description: 'Industry-leading communications platform with global reach',
      authUrl: '',
      color: 'from-red-500 to-red-600',
      features: ['Voice', 'SMS', 'WhatsApp', 'Video']
    },
    {
      id: 'frejun',
      name: 'Frejun',
      logo: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB4PSI4IiB5PSI4IiB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHJ4PSI2IiBmaWxsPSJ3aGl0ZSIvPjxwYXRoIGQ9Ik0xNiAxNmgxNnY0SDE2ek0xNiAyNGgxMnY0SDE2ek0xNiAzMmg4djRoLTh6IiBmaWxsPSIjMDA3QUZGIi8+PC9zdmc+',
      description: 'Real-time AI voice communications with OpenAI integration',
      authUrl: '',
      color: 'from-cyan-500 to-blue-600',
      features: ['Voice', 'AI Integration', 'Real-time Streaming', 'WebSocket']
    }
  ];

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');

    if (!token) {
      router.push('/login');
      return;
    }

    if (userStr) {
      const userData = JSON.parse(userStr);
      setUser(userData);
      // Try id, _id, and clientId for compatibility
      const userId = userData.id || userData._id || userData.clientId;
      if (userId) {
        checkProviderConnection(userId, token);
        fetchAIAssistants(userId, token);
      }
    }

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }
  }, [router]);

  useEffect(() => {
    const tabParam = urlSearchParams?.get('tab');
    if (tabParam === 'calls') {
      setActiveNav('Call logs');
      setActiveTab('calls');
    } else if (tabParam === 'numbers') {
      setActiveNav('Phone Numbers');
      setActiveTab('numbers');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSearchParams]);

  useEffect(() => {
    if (activeTab === 'calls' && user) {
      fetchCallLogs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const checkProviderConnection = async (userId: string, token: string) => {
    try {
      const response = await fetch(`${API_URL}/api/phone-numbers/connection-status/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.connections && data.connections.length > 0) {
          // User has existing connection, auto-sync phone numbers
          console.log('Existing provider connection found, syncing phone numbers...');
          syncPhoneNumbers(userId, token);
        } else {
          // No connection, just fetch any existing phone numbers
          fetchPhoneNumbers(userId, token);
        }
      } else {
        // Fallback to regular fetch
        fetchPhoneNumbers(userId, token);
      }
    } catch (error) {
      console.error('Error checking provider connection:', error);
      // Fallback to regular fetch
      fetchPhoneNumbers(userId, token);
    }
  };

  const syncPhoneNumbers = async (userId: string, token: string) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/phone-numbers/sync/${userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPhoneNumbers(data.phone_numbers || []);
        console.log('Phone numbers synced successfully');
      } else {
        // If sync fails, try regular fetch
        fetchPhoneNumbers(userId, token);
      }
    } catch (error) {
      console.error('Error syncing phone numbers:', error);
      // Fallback to regular fetch
      fetchPhoneNumbers(userId, token);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPhoneNumbers = async (userId: string, token: string) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/phone-numbers/user/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPhoneNumbers(data.phone_numbers || []);
      }
    } catch (error) {
      console.error('Error fetching phone numbers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCallLogs = async (phoneNumberId?: string) => {
    try {
      setIsLoadingCalls(true);
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) {
        console.error('User ID not found');
        setIsLoadingCalls(false);
        return;
      }

      if (!token) {
        console.error('Authentication token missing');
        setIsLoadingCalls(false);
        return;
      }

      const url = phoneNumberId
        ? `${API_URL}/api/phone-numbers/call-logs/phone/${phoneNumberId}`
        : `${API_URL}/api/phone-numbers/call-logs/user/${userId}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Call logs response:', data);
        setCallLogs(data.call_logs || []);
        setLastCallLogsRefresh(new Date());
      } else {
        console.error('Failed to fetch call logs:', response.status);
      }
    } catch (error) {
      console.error('Error fetching call logs:', error);
    } finally {
      setIsLoadingCalls(false);
    }
  };

  const handleConnectProvider = async () => {
    if (!selectedProvider || !credentials.accountSid || !credentials.authToken || !user) {
      return;
    }

    try {
      setIsConnecting(true);
      const token = localStorage.getItem('token');
      // Try id, _id, and clientId for compatibility
      const userId = user.id || user._id || user.clientId;

      if (!userId) {
        alert('User ID not found. Please login again.');
        setIsConnecting(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/phone-numbers/connect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: selectedProvider.id,
          account_sid: credentials.accountSid,
          auth_token: credentials.authToken,
          user_id: userId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setPhoneNumbers(data.phone_numbers || []);
        setIsCredentialsModalOpen(false);
        setIsProviderModalOpen(false);
        setCredentials({ accountSid: '', authToken: '' });
        setSelectedProvider(null);
      } else {
        const error = await response.json();
        alert(error.message || 'Failed to connect provider');
      }
    } catch (error) {
      console.error('Error connecting provider:', error);
      alert('An error occurred while connecting to the provider');
    } finally {
      setIsConnecting(false);
    }
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

  const handleNavigation = (navItem: NavigationItem) => {
    setActiveNav(navItem.name);
    if (navItem.name === 'Phone Numbers') {
      setActiveTab('numbers');
    } else if (navItem.name === 'Call logs') {
      setActiveTab('calls');
    }
    router.push(navItem.href);
  };

  const fetchAIAssistants = async (userId: string, token: string) => {
    try {
      const response = await fetch(`${API_URL}/api/ai-assistants/user/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAiAssistants(data.assistants || []);
      }
    } catch (error) {
      console.error('Error fetching AI assistants:', error);
    }
  };

  const handleOpenAssignModal = (phone: PhoneNumber) => {
    setSelectedPhoneNumber(phone);
    setSelectedAssistant(phone.assigned_assistant_id || '');
    setIsAssignModalOpen(true);
  };

  const handleAssignAssistant = async () => {
    if (!selectedPhoneNumber || !selectedAssistant || !user) {
      return;
    }

    try {
      setIsAssigning(true);
      const token = localStorage.getItem('token');
      const userId = user.id || user._id || user.clientId;

      const response = await fetch(`${API_URL}/api/phone-numbers/assign-assistant`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number_id: selectedPhoneNumber.id,
          assistant_id: selectedAssistant,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Update the phone number in the list
        setPhoneNumbers(prev => prev.map(p =>
          p.id === selectedPhoneNumber.id ? data.phone_number : p
        ));
        setIsAssignModalOpen(false);
        setSelectedPhoneNumber(null);
        setSelectedAssistant('');
        alert(data.message);
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to assign AI assistant');
      }
    } catch (error) {
      console.error('Error assigning AI assistant:', error);
      alert('An error occurred while assigning the AI assistant');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUnassignAssistant = async (phoneNumber: PhoneNumber) => {
    if (!confirm('Are you sure you want to unassign the AI assistant from this phone number?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');

      const response = await fetch(`${API_URL}/api/phone-numbers/unassign-assistant/${phoneNumber.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Update the phone number in the list
        setPhoneNumbers(prev => prev.map(p =>
          p.id === phoneNumber.id ? data : p
        ));
        alert('AI assistant unassigned successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to unassign AI assistant');
      }
    } catch (error) {
      console.error('Error unassigning AI assistant:', error);
      alert('An error occurred while unassigning the AI assistant');
    }
  };

  const handleProviderLogin = (provider: ServiceProvider) => {
    setSelectedProvider(provider);
    setIsProviderModalOpen(false);
    setIsCredentialsModalOpen(true);
  };

  const handleSearchNumbers = async () => {
    try {
      setIsSearching(true);
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) {
        alert('User ID not found. Please login again.');
        return;
      }

      const response = await fetch(`${API_URL}/api/phone-numbers/twilio/search-numbers`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          country_code: 'US',
          area_code: numberSearchParams.areaCode || undefined,
          contains: numberSearchParams.contains || undefined,
          limit: 20
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAvailableNumbers(data.available_numbers || []);
        // Reset selections when new search is performed
        setSelectedNumber('');
        setSelectedAssistant('');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to search numbers');
      }
    } catch (error) {
      console.error('Error searching numbers:', error);
      alert('An error occurred while searching for numbers');
    } finally {
      setIsSearching(false);
    }
  };

  const checkCallStatus = async (callSid: string) => {
    try {
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) return;

      const response = await fetch(
        `${API_URL}/api/outbound-calls/call-status/${callSid}/${userId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setActiveCallStatus(data.status);

        // If call is completed, stop tracking
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'canceled') {
          setIsCallActive(false);
          setActiveCallSid(null);
          // Refresh call logs
          fetchCallLogs();
        }
      }
    } catch (error) {
      console.error('Error checking call status:', error);
    }
  };

  const hangupCall = async () => {
    if (!activeCallSid) return;

    try {
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) return;

      const response = await fetch(
        `${API_URL}/api/outbound-calls/hangup/${activeCallSid}/${userId}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setIsCallActive(false);
        setActiveCallSid(null);
        setActiveCallStatus('completed');
        alert('Call ended successfully');
        fetchCallLogs();
      } else {
        alert('Failed to end call');
      }
    } catch (error) {
      console.error('Error hanging up call:', error);
      alert('An error occurred while ending the call');
    }
  };

  const fetchVerifiedCallerIds = async () => {
    try {
      setIsLoadingCallerIds(true);
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) {
        console.error('User ID not found');
        return;
      }

      // Fetch verified caller IDs from Twilio
      const response = await fetch(
        `${API_URL}/api/phone-numbers/twilio/verified-caller-ids/${userId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setVerifiedCallerIds(data.verified_caller_ids || []);
      } else {
        console.error('Failed to fetch verified caller IDs');
        setVerifiedCallerIds([]);
      }
    } catch (error) {
      console.error('Error fetching verified caller IDs:', error);
      setVerifiedCallerIds([]);
    } finally {
      setIsLoadingCallerIds(false);
    }
  };

  const handleMakeCall = async () => {
    if (!selectedPhoneForCall || !callToNumber.trim()) {
      alert('Please enter a phone number to call');
      return;
    }

    // Basic phone number validation
    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    if (!phoneRegex.test(callToNumber.replace(/[\s-()]/g, ''))) {
      alert('Please enter a valid phone number (e.g., +1234567890)');
      return;
    }

    try {
      setIsInitiatingCall(true);
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId || !selectedPhoneForCall.assigned_assistant_id) {
        alert('Configuration error. Please try again.');
        return;
      }

      const response = await fetch(
        `${API_URL}/api/outbound-calls/make-call/${selectedPhoneForCall.assigned_assistant_id}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            phone_number: callToNumber.replace(/[\s-()]/g, '')
          }),
        }
      );

      if (response.ok) {
        const data = await response.json();

        // Start tracking active call
        setActiveCallSid(data.call_sid);
        setActiveCallStatus('initiated');
        setIsCallActive(true);

        // Close modal and reset
        setIsCallModalOpen(false);
        setCallToNumber('');
        setSelectedPhoneForCall(null);

        // Start polling for call status every 2 seconds
        const statusInterval = setInterval(() => {
          if (data.call_sid) {
            checkCallStatus(data.call_sid);
          }
        }, 2000);

        // Clear interval after 5 minutes (max call duration tracking)
        setTimeout(() => {
          clearInterval(statusInterval);
        }, 300000);

        // Store interval ID to clear it when needed
        (window as any).callStatusInterval = statusInterval;
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to initiate call');
      }
    } catch (error) {
      console.error('Error making call:', error);
      alert('An error occurred while initiating the call');
    } finally {
      setIsInitiatingCall(false);
    }
  };

  const handlePurchaseNumber = async () => {
    if (!selectedNumber || !selectedAssistant) {
      alert('Please select a number and an AI assistant');
      return;
    }

    try {
      setIsPurchasing(true);
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      if (!userId) {
        alert('User ID not found. Please login again.');
        return;
      }

      const response = await fetch(`${API_URL}/api/phone-numbers/twilio/purchase-number`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          phone_number: selectedNumber,
          friendly_name: `Auto-purchased ${new Date().toLocaleDateString()}`,
          use_twiml_app: true,
          assistant_id: selectedAssistant
        }),
      });

      if (response.ok) {
        const data = await response.json();
        alert('Number purchased successfully! Webhook automatically configured.');

        // Refresh phone numbers list
        syncPhoneNumbers(userId, token);

        // Close modal and reset state
        setIsPurchaseModalOpen(false);
        setSelectedNumber('');
        setSelectedAssistant('');
        setAvailableNumbers([]);
        setNumberSearchParams({ areaCode: '', contains: '' });
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to purchase number');
      }
    } catch (error) {
      console.error('Error purchasing number:', error);
      alert('An error occurred while purchasing the number');
    } finally {
      setIsPurchasing(false);
    }
  };

  const formatDuration = (seconds?: number | null): string => {
    if (!seconds || seconds === 0) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDateTime = (dateString?: string | null): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatLastRefreshed = (date: Date | null): string => {
    if (!date) return '—';
    return date.toLocaleString();
  };

  const navigationItems = useMemo(() => NAV_ITEMS, []);

  const userInitial = useMemo(() => {
    const candidate = user?.fullName || user?.name || user?.username || user?.email;
    if (!candidate || typeof candidate !== 'string') {
      return 'U';
    }
    const trimmed = candidate.trim();
    return trimmed.length > 0 ? trimmed.charAt(0).toUpperCase() : 'U';
  }, [user]);

  const userGreeting = useMemo(() => {
    const options = [
      user?.firstName,
      user?.fullName,
      user?.name,
      user?.username,
      user?.email,
    ].filter((value) => typeof value === 'string' && value.trim().length > 0) as string[];

    if (options.length === 0) return undefined;
    const preferred = options[0];
    if (preferred.includes('@')) {
      return preferred.split('@')[0];
    }
    return preferred.split(' ')[0];
  }, [user]);


  if (!user) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className={`flex h-screen ${isDarkMode ? 'dark bg-gray-900' : 'bg-neutral-light'}`}>
      {/* Sidebar - Full height with logo */}
      <aside
        onMouseEnter={() => setIsSidebarCollapsed(false)}
        onMouseLeave={() => setIsSidebarCollapsed(true)}
        className={`fixed left-0 top-0 h-screen ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border-r ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} transition-all duration-300 z-40 ${isSidebarCollapsed ? 'w-20' : 'w-64'} ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
      >
        <div className="flex flex-col h-full">
          {/* Logo Section */}
          <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center px-4' : 'justify-start gap-3 px-6'} py-4 h-[57px] border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
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
                {!isSidebarCollapsed && (
                  <span className="text-sm">{item.name}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${isSidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64'}`}>
        <TopBar
          isDarkMode={isDarkMode}
          toggleTheme={toggleTheme}
          onLogout={handleLogout}
          userInitial={userInitial}
          userLabel={userGreeting}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
          searchPlaceholder="Search phone numbers..."
          collapseSearchOnMobile
        />

        <div className="flex-1 overflow-y-auto">
          {/* Page Content */}
        <main className="p-6">
          {/* Header Section */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                Phone Numbers & Call Logs
              </h1>
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                Manage your phone numbers, view call logs, and connect with service providers
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setIsPurchaseModalOpen(true)}
                className="px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl hover:shadow-lg hover:shadow-green-500/25 transition-all duration-200 flex items-center gap-2 font-semibold"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Purchase Number
              </button>
              <button
                onClick={() => setIsProviderModalOpen(true)}
                className="px-6 py-3 bg-gradient-to-r from-primary to-primary/80 text-white rounded-xl hover:shadow-lg hover:shadow-primary/25 transition-all duration-200 flex items-center gap-2 font-semibold"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Connect Provider
              </button>
            </div>
          </div>

          {/* Active Call Banner */}
          {isCallActive && activeCallSid && (
            <div className={`mb-6 p-6 rounded-2xl border-2 ${
              isDarkMode
                ? 'bg-gradient-to-r from-green-900/30 to-emerald-900/30 border-green-700'
                : 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-300'
            } shadow-lg animate-pulse-slow`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Animated call icon */}
                  <div className="relative">
                    <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
                      isDarkMode ? 'bg-green-800' : 'bg-green-500'
                    }`}>
                      <svg className="w-7 h-7 text-white animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                      </svg>
                    </div>
                    {/* Ripple effect */}
                    <div className={`absolute inset-0 rounded-full animate-ping ${
                      isDarkMode ? 'bg-green-700' : 'bg-green-400'
                    } opacity-40`}></div>
                  </div>

                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                        Call in Progress
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        activeCallStatus === 'ringing'
                          ? (isDarkMode ? 'bg-yellow-900 text-yellow-300' : 'bg-yellow-100 text-yellow-800')
                          : activeCallStatus === 'in-progress'
                          ? (isDarkMode ? 'bg-green-900 text-green-300' : 'bg-green-100 text-green-800')
                          : (isDarkMode ? 'bg-blue-900 text-blue-300' : 'bg-blue-100 text-blue-800')
                      }`}>
                        {activeCallStatus === 'ringing' && '📞 Ringing...'}
                        {activeCallStatus === 'in-progress' && '✓ Connected'}
                        {activeCallStatus === 'initiated' && '⏳ Initiating...'}
                        {activeCallStatus === 'queued' && '⏸ Queued'}
                      </span>
                    </div>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Call SID: <span className="font-mono">{activeCallSid}</span>
                    </p>
                  </div>
                </div>

                {/* Hang up button */}
                <button
                  onClick={hangupCall}
                  className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 flex items-center gap-2 ${
                    isDarkMode
                      ? 'bg-red-900 hover:bg-red-800 text-red-200'
                      : 'bg-red-500 hover:bg-red-600 text-white'
                  } shadow-lg hover:shadow-xl`}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
                  </svg>
                  End Call
                </button>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className={`flex gap-2 mb-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
            <button
              onClick={() => {
                setActiveTab('numbers');
                router.replace('/phone-numbers');
              }}
              className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
                activeTab === 'numbers'
                  ? `border-primary ${isDarkMode ? 'text-primary' : 'text-primary'}`
                  : `border-transparent ${isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-neutral-mid hover:text-neutral-dark'}`
              }`}
            >
              Phone Numbers ({phoneNumbers.length})
            </button>
            <button
              onClick={() => {
                setActiveTab('calls');
                router.replace('/phone-numbers?tab=calls');
                if (callLogs.length === 0) {
                  fetchCallLogs();
                }
              }}
              className={`px-6 py-3 font-semibold transition-all duration-200 border-b-2 ${
                activeTab === 'calls'
                  ? `border-primary ${isDarkMode ? 'text-primary' : 'text-primary'}`
                  : `border-transparent ${isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-neutral-mid hover:text-neutral-dark'}`
              }`}
            >
              Call Logs ({callLogs.length})
            </button>
          </div>

          {/* Phone Numbers List */}
          {activeTab === 'numbers' && (
            <>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : phoneNumbers.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {phoneNumbers.map((phone) => (
                <div
                  key={phone.id}
                  className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-neutral-mid/10'} border rounded-2xl p-6 hover:shadow-lg transition-all duration-200`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                          {phone.phone_number}
                        </h3>
                        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                          {phone.provider}
                        </p>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      phone.status === 'active'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    }`}>
                      {phone.status}
                    </span>
                  </div>

                  {phone.friendly_name && (
                    <p className={`text-sm mb-3 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      {phone.friendly_name}
                    </p>
                  )}

                  {/* AI Assistant Assignment Status */}
                  {phone.assigned_assistant_name ? (
                    <div className={`mb-4 p-3 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className={`text-xs font-semibold ${isDarkMode ? 'text-blue-400' : 'text-blue-700'}`}>
                          AI Assistant Assigned
                        </span>
                      </div>
                      <p className={`text-sm font-medium ${isDarkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                        {phone.assigned_assistant_name}
                      </p>
                    </div>
                  ) : (
                    <div className={`mb-4 p-3 rounded-xl ${isDarkMode ? 'bg-gray-700/50 border border-gray-600' : 'bg-gray-50 border border-gray-200'}`}>
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          No AI assistant assigned
                        </span>
                      </div>
                    </div>
                  )}

                  {phone.capabilities && (
                    <div className="flex gap-2 mb-4">
                      {phone.capabilities.voice && (
                        <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-neutral-light text-neutral-dark'}`}>
                          Voice
                        </span>
                      )}
                      {phone.capabilities.sms && (
                        <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-neutral-light text-neutral-dark'}`}>
                          SMS
                        </span>
                      )}
                      {phone.capabilities.mms && (
                        <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-neutral-light text-neutral-dark'}`}>
                          MMS
                        </span>
                      )}
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    {/* Make Call Button */}
                    {phone.capabilities?.voice && phone.assigned_assistant_name && (
                      <button
                        onClick={() => {
                          setSelectedPhoneForCall(phone);
                          setCallToNumber('');
                          setIsCallModalOpen(true);
                          fetchVerifiedCallerIds();
                        }}
                        className={`w-full px-4 py-2.5 rounded-xl ${isDarkMode ? 'bg-green-600 hover:bg-green-700 text-white' : 'bg-green-500 hover:bg-green-600 text-white'} transition-colors text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-green-500/25`}
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                        Make Call
                      </button>
                    )}

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleOpenAssignModal(phone)}
                        className={`flex-1 px-4 py-2 rounded-xl ${isDarkMode ? 'bg-primary/20 hover:bg-primary/30 text-primary' : 'bg-primary/10 hover:bg-primary/20 text-primary'} transition-colors text-sm font-medium flex items-center justify-center gap-2`}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {phone.assigned_assistant_name ? 'Change' : 'Assign'} AI
                      </button>
                      {phone.assigned_assistant_name && (
                        <button
                          onClick={() => handleUnassignAssistant(phone)}
                          className={`px-4 py-2 rounded-xl ${isDarkMode ? 'bg-red-900/30 hover:bg-red-900/50 text-red-400' : 'bg-red-50 hover:bg-red-100 text-red-600'} transition-colors`}
                          title="Unassign AI Assistant"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-12 text-center`}>
              <div className="w-20 h-20 bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-10 h-10 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                No Phone Numbers Yet
              </h3>
              <p className={`mb-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                Connect with a service provider to add your first phone number
              </p>
              <button
                onClick={() => setIsProviderModalOpen(true)}
                className="px-6 py-3 bg-gradient-to-r from-primary to-primary/80 text-white rounded-xl hover:shadow-lg hover:shadow-primary/25 transition-all duration-200 inline-flex items-center gap-2 font-semibold"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Get Started
              </button>
            </div>
          )}
            </>
          )}

          {/* Call Logs Section */}
          {activeTab === 'calls' && (
            <>
          {isLoadingCalls ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : callLogs.length > 0 ? (
                <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl overflow-hidden shadow-sm`}>
                  <div className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-6 py-4 ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                    <div>
                      <h3 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>Recent Call Logs</h3>
                      <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Last refreshed: {formatLastRefreshed(lastCallLogsRefresh)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => fetchCallLogs()}
                        disabled={isLoadingCalls}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                          isLoadingCalls
                            ? 'bg-neutral-mid/20 text-neutral-mid cursor-not-allowed'
                            : isDarkMode
                              ? 'bg-gray-700 hover:bg-gray-600 text-white'
                              : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'
                        }`}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9H4m0 0V4m16 16v-5h-.581m-15.357-2a8.003 8.003 0 0015.357 2H20m0 0v5" />
                        </svg>
                        {isLoadingCalls ? 'Refreshing…' : 'Refresh Logs'}
                      </button>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className={`${isDarkMode ? 'bg-gray-700' : 'bg-neutral-light'}`}>
                        <tr>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Direction
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            From
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            To
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Status
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Duration
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Time
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            AI Assistant
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Recording
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Cost
                          </th>
                          <th className={`px-6 py-4 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-700">
                        {callLogs.map((call, index) => (
                          <tr key={call.id || call.call_sid || `call-${index}`} className={`${isDarkMode ? 'hover:bg-gray-700/50' : 'hover:bg-neutral-light'} transition-colors`}>
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                {call.direction === 'inbound' ? (
                                  <>
                                    <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                                    </svg>
                                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                                      Inbound
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                                    </svg>
                                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                                      Outbound
                                    </span>
                                  </>
                                )}
                              </div>
                            </td>
                            <td className={`px-6 py-4 text-sm font-mono ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                              {call.from || call.from_number || '-'}
                            </td>
                            <td className={`px-6 py-4 text-sm font-mono ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                              {call.to}
                            </td>
                            <td className="px-6 py-4">
                              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                call.status === 'completed'
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                  : call.status === 'failed'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  : call.status === 'busy'
                                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                              }`}>
                                {call.status}
                              </span>
                            </td>
                            <td className={`px-6 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                              {formatDuration(call.duration)}
                            </td>
                            <td className={`px-6 py-4 text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                              {formatDateTime(call.start_time || call.date_created)}
                            </td>
                            <td className={`px-6 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                              {call.assistant_name ? (
                                <div className="flex items-center gap-2">
                                  <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                  </svg>
                                  <span>{call.assistant_name}</span>
                                </div>
                              ) : (
                                '-'
                              )}
                            </td>
                            <td className="px-6 py-4">
                              {call.recording_url ? (
                                <audio
                                  controls
                                  className="max-w-xs"
                                  preload="metadata"
                                >
                                  <source src={call.recording_url} type="audio/mpeg" />
                                  Your browser does not support audio playback.
                                </audio>
                              ) : (
                                <span className={`text-sm ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                                  No recording
                                </span>
                              )}
                            </td>
                            <td className={`px-6 py-4 text-sm font-semibold ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                              {call.price ? `$${Math.abs(parseFloat(call.price)).toFixed(4)}` : '-'}
                            </td>
                            <td className="px-6 py-4">
                              <button
                                onClick={() => {
                                  setSelectedCallLog(call);
                                  setIsCallDetailsModalOpen(true);
                                }}
                                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                  isDarkMode
                                    ? 'bg-primary/20 text-primary hover:bg-primary/30'
                                    : 'bg-primary/10 text-primary hover:bg-primary/20'
                                }`}
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-12 text-center`}>
                  <div className="w-20 h-20 bg-gradient-to-br from-primary/20 to-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-10 h-10 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                  </div>
                  <h3 className={`text-xl font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    No Call Logs Yet
                  </h3>
                  <p className={`mb-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                    Call logs will appear here once you start making or receiving calls
                  </p>
                </div>
              )}
            </>
          )}
        </main>
        </div>
      </div>

      {/* Service Provider Modal */}
      {isProviderModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex items-center justify-between`}>
              <div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Choose a Service Provider
                </h2>
                <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                  Connect with your preferred telephony service to manage phone numbers
                </p>
              </div>
              <button
                onClick={() => setIsProviderModalOpen(false)}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {serviceProviders.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => handleProviderLogin(provider)}
                    className={`${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 border-gray-600' : 'bg-white hover:bg-neutral-light border-neutral-mid/20'} border rounded-xl p-6 text-left transition-all duration-200 hover:shadow-lg hover:scale-105 group`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-16 h-16 bg-gradient-to-br ${provider.color} rounded-xl flex items-center justify-center p-3 flex-shrink-0 shadow-lg`}>
                        <img src={provider.logo} alt={provider.name} className="w-full h-full object-contain" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className={`font-bold text-lg mb-1 ${isDarkMode ? 'text-white' : 'text-neutral-dark'} group-hover:text-primary transition-colors`}>
                          {provider.name}
                        </h3>
                        <p className={`text-sm mb-3 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                          {provider.description}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {provider.features.map((feature, index) => (
                            <span
                              key={index}
                              className={`px-2 py-1 rounded-lg text-xs font-medium ${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-neutral-light text-neutral-dark'}`}
                            >
                              {feature}
                            </span>
                          ))}
                        </div>
                      </div>
                      <svg className={`w-5 h-5 flex-shrink-0 ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'} group-hover:text-primary transition-colors`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>

              <div className={`mt-6 p-4 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
                <div className="flex gap-3">
                  <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className={`text-sm font-medium mb-1 ${isDarkMode ? 'text-blue-400' : 'text-blue-900'}`}>
                      How it works
                    </p>
                    <p className={`text-sm ${isDarkMode ? 'text-blue-300' : 'text-blue-800'}`}>
                      After selecting a provider, you'll enter your API credentials. Once authenticated, your phone numbers will automatically sync with Convis AI.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Credentials Modal */}
      {isCredentialsModalOpen && selectedProvider && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-md w-full shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex items-center justify-between`}>
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 bg-gradient-to-br ${selectedProvider.color} rounded-xl flex items-center justify-center p-2`}>
                  <img src={selectedProvider.logo} alt={selectedProvider.name} className="w-full h-full object-contain" />
                </div>
                <div>
                  <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    Connect {selectedProvider.name}
                  </h2>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                    Enter your API credentials
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsCredentialsModalOpen(false);
                  setIsProviderModalOpen(true);
                  setSelectedProvider(null);
                  setCredentials({ accountSid: '', authToken: '' });
                }}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                  {selectedProvider.id === 'frejun' ? 'Teler Account ID' : 'Account SID'}
                </label>
                <input
                  type="text"
                  value={credentials.accountSid}
                  onChange={(e) => setCredentials({ ...credentials, accountSid: e.target.value })}
                  placeholder={selectedProvider.id === 'frejun' ? 'Enter your Teler Account ID' : 'Enter your Account SID'}
                  className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-neutral-light border-neutral-mid/20 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-mono text-sm`}
                />
              </div>

              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                  {selectedProvider.id === 'frejun' ? 'Teler API Key' : 'Auth Token'}
                </label>
                <input
                  type="password"
                  value={credentials.authToken}
                  onChange={(e) => setCredentials({ ...credentials, authToken: e.target.value })}
                  placeholder={selectedProvider.id === 'frejun' ? 'Enter your Teler API Key' : 'Enter your Auth Token'}
                  className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-neutral-light border-neutral-mid/20 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-mono text-sm`}
                />
              </div>

              <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
                <div className="flex gap-3">
                  <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className={`text-xs ${isDarkMode ? 'text-blue-300' : 'text-blue-800'}`}>
                      Find your credentials in your {selectedProvider.name} dashboard. Your credentials are securely stored and never shared.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className={`px-6 py-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex gap-3`}>
              <button
                onClick={() => {
                  setIsCredentialsModalOpen(false);
                  setIsProviderModalOpen(true);
                  setSelectedProvider(null);
                  setCredentials({ accountSid: '', authToken: '' });
                }}
                className={`flex-1 px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'} transition-colors font-semibold`}
              >
                Back
              </button>
              <button
                onClick={handleConnectProvider}
                disabled={isConnecting || !credentials.accountSid || !credentials.authToken}
                className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all duration-200 ${
                  isConnecting || !credentials.accountSid || !credentials.authToken
                    ? 'bg-gray-400 cursor-not-allowed text-gray-600'
                    : 'bg-gradient-to-r from-primary to-primary/80 text-white hover:shadow-lg hover:shadow-primary/25'
                }`}
              >
                {isConnecting ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Connecting...
                  </div>
                ) : (
                  'Connect'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant Assignment Modal */}
      {isAssignModalOpen && selectedPhoneNumber && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-md w-full shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    Assign AI Assistant
                  </h2>
                  <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                    {selectedPhoneNumber.phone_number}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setIsAssignModalOpen(false);
                    setSelectedPhoneNumber(null);
                    setSelectedAssistant('');
                  }}
                  className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
                >
                  <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {aiAssistants.length > 0 ? (
                <>
                  <label className={`block text-sm font-semibold mb-3 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                    Select AI Assistant
                  </label>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {aiAssistants.map((assistant) => (
                      <button
                        key={assistant.id}
                        onClick={() => setSelectedAssistant(assistant.id)}
                        className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                          selectedAssistant === assistant.id
                            ? `${isDarkMode ? 'bg-primary/20 border-primary' : 'bg-primary/10 border-primary'}`
                            : `${isDarkMode ? 'bg-gray-700 border-gray-600 hover:border-gray-500' : 'bg-white border-gray-200 hover:border-gray-300'}`
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                            selectedAssistant === assistant.id
                              ? 'bg-primary text-white'
                              : `${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'}`
                          }`}>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                            </svg>
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                              {assistant.name}
                            </h3>
                            <p className={`text-xs truncate ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              Voice: {assistant.voice} • Temp: {assistant.temperature}
                            </p>
                          </div>
                          {selectedAssistant === assistant.id && (
                            <svg className="w-5 h-5 text-primary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className={`mt-4 p-4 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} border`}>
                    <div className="flex gap-3">
                      <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div>
                        <p className={`text-xs ${isDarkMode ? 'text-blue-300' : 'text-blue-800'}`}>
                          The webhook URL will be automatically configured on your Twilio phone number to handle incoming calls with the selected AI assistant.
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <div className={`w-16 h-16 rounded-full ${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'} flex items-center justify-center mx-auto mb-4`}>
                    <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    No AI Assistants Found
                  </h3>
                  <p className={`text-sm mb-4 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                    Create an AI assistant first to assign to your phone number
                  </p>
                  <button
                    onClick={() => router.push('/ai-agent')}
                    className="px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors text-sm font-medium"
                  >
                    Create AI Assistant
                  </button>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {aiAssistants.length > 0 && (
              <div className={`px-6 py-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex gap-3`}>
                <button
                  onClick={() => {
                    setIsAssignModalOpen(false);
                    setSelectedPhoneNumber(null);
                    setSelectedAssistant('');
                  }}
                  className={`flex-1 px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'} transition-colors font-semibold`}
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignAssistant}
                  disabled={isAssigning || !selectedAssistant}
                  className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all duration-200 ${
                    isAssigning || !selectedAssistant
                      ? 'bg-gray-400 cursor-not-allowed text-gray-600'
                      : 'bg-gradient-to-r from-primary to-primary/80 text-white hover:shadow-lg hover:shadow-primary/25'
                  }`}
                >
                  {isAssigning ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Assigning...
                    </div>
                  ) : (
                    'Assign AI Assistant'
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Purchase Number Modal */}
      {isPurchaseModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex items-center justify-between`}>
              <div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Purchase Phone Number
                </h2>
                <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                  Search and purchase a new Twilio phone number with automatic webhook configuration
                </p>
              </div>
              <button
                onClick={() => {
                  setIsPurchaseModalOpen(false);
                  setAvailableNumbers([]);
                  setNumberSearchParams({ areaCode: '', contains: '' });
                  setSelectedNumber('');
                  setSelectedAssistant('');
                }}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Search Section */}
              <div className={`mb-6 p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                <h3 className={`font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Search Criteria
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      Area Code (Optional)
                    </label>
                    <input
                      type="text"
                      value={numberSearchParams.areaCode}
                      onChange={(e) => setNumberSearchParams({ ...numberSearchParams, areaCode: e.target.value })}
                      placeholder="e.g., 415"
                      maxLength={3}
                      className={`w-full px-4 py-2.5 rounded-xl ${isDarkMode ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                    />
                  </div>
                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      Contains Digits (Optional)
                    </label>
                    <input
                      type="text"
                      value={numberSearchParams.contains}
                      onChange={(e) => setNumberSearchParams({ ...numberSearchParams, contains: e.target.value })}
                      placeholder="e.g., 1234"
                      className={`w-full px-4 py-2.5 rounded-xl ${isDarkMode ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleSearchNumbers}
                      disabled={isSearching}
                      className={`w-full px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 ${
                        isSearching
                          ? 'bg-gray-400 cursor-not-allowed text-gray-600'
                          : 'bg-gradient-to-r from-primary to-primary/80 text-white hover:shadow-lg hover:shadow-primary/25'
                      }`}
                    >
                      {isSearching ? (
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Searching...
                        </div>
                      ) : (
                        <div className="flex items-center justify-center gap-2">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                          Search
                        </div>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Available Numbers List */}
              {availableNumbers.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    <h3 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      Step 1: Select a Number ({availableNumbers.length} available)
                    </h3>
                  </div>
                  <div className="space-y-2 max-h-56 overflow-y-auto pr-2">
                    {availableNumbers.map((number, index) => (
                      <button
                        key={index}
                        onClick={() => setSelectedNumber(number.phone_number)}
                        className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                          selectedNumber === number.phone_number
                            ? `${isDarkMode ? 'bg-primary/20 border-primary' : 'bg-primary/10 border-primary'}`
                            : `${isDarkMode ? 'bg-gray-700 border-gray-600 hover:border-gray-500' : 'bg-white border-gray-200 hover:border-gray-300'}`
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                                selectedNumber === number.phone_number
                                  ? 'bg-primary text-white'
                                  : `${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'}`
                              }`}>
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                                </svg>
                              </div>
                              <div>
                                <h3 className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                                  {number.phone_number}
                                </h3>
                                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                  {number.locality && number.region ? `${number.locality}, ${number.region}` : 'US Number'}
                                </p>
                              </div>
                            </div>
                            <div className="flex gap-2 mt-2">
                              {number.capabilities?.voice && (
                                <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-100 text-gray-700'}`}>
                                  Voice
                                </span>
                              )}
                              {number.capabilities?.sms && (
                                <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-100 text-gray-700'}`}>
                                  SMS
                                </span>
                              )}
                              {number.capabilities?.mms && (
                                <span className={`px-2 py-1 rounded-lg text-xs ${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-100 text-gray-700'}`}>
                                  MMS
                                </span>
                              )}
                            </div>
                          </div>
                          {selectedNumber === number.phone_number && (
                            <svg className="w-6 h-6 text-primary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Assistant Selection */}
              {selectedNumber && (
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-green-900/20 border border-green-800' : 'bg-green-50 border border-green-200'}`}>
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className={`font-semibold ${isDarkMode ? 'text-green-400' : 'text-green-900'}`}>
                      Step 2: Assign AI Assistant
                    </h3>
                  </div>
                  {aiAssistants.length > 0 ? (
                    <div className="space-y-2 max-h-44 overflow-y-auto">
                      {aiAssistants.map((assistant) => (
                        <button
                          key={assistant.id}
                          onClick={() => setSelectedAssistant(assistant.id)}
                          className={`w-full text-left p-3 rounded-xl border-2 transition-all duration-200 ${
                            selectedAssistant === assistant.id
                              ? `${isDarkMode ? 'bg-primary/20 border-primary' : 'bg-primary/10 border-primary'}`
                              : `${isDarkMode ? 'bg-gray-700 border-gray-600 hover:border-gray-500' : 'bg-white border-gray-200 hover:border-gray-300'}`
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                selectedAssistant === assistant.id
                                  ? 'bg-primary text-white'
                                  : `${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'}`
                              }`}>
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                </svg>
                              </div>
                              <div className="min-w-0 flex-1">
                                <h4 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                                  {assistant.name}
                                </h4>
                                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-600'} truncate`}>
                                  Voice: {assistant.voice}
                                </p>
                              </div>
                            </div>
                            {selectedAssistant === assistant.id && (
                              <svg className="w-5 h-5 text-primary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className={`p-6 rounded-xl text-center ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                      <p className={`text-sm mb-3 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        No AI assistants found. Create one first.
                      </p>
                      <button
                        onClick={() => router.push('/ai-agent')}
                        className="px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors text-sm font-medium"
                      >
                        Create AI Assistant
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Info Box */}
              {availableNumbers.length === 0 && !isSearching && (
                <div className={`p-6 rounded-xl text-center ${isDarkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className={`font-semibold ${isDarkMode ? 'text-blue-400' : 'text-blue-900'}`}>
                      How it works
                    </p>
                  </div>
                  <p className={`text-sm ${isDarkMode ? 'text-blue-300' : 'text-blue-800'}`}>
                    1. Search for available numbers by area code or digits<br />
                    2. Select a number from the results<br />
                    3. Choose an AI assistant to assign<br />
                    4. Click "Purchase & Configure" - webhook is automatically set up!
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className={`px-6 py-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              {/* Status Message */}
              {(!selectedNumber || !selectedAssistant) && availableNumbers.length > 0 && (
                <div className={`mb-3 p-3 rounded-xl ${isDarkMode ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'} text-sm`}>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-yellow-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className={isDarkMode ? 'text-yellow-400' : 'text-yellow-800'}>
                      {!selectedNumber && 'Please select a phone number'}
                      {selectedNumber && !selectedAssistant && 'Please assign an AI assistant'}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setIsPurchaseModalOpen(false);
                    setAvailableNumbers([]);
                    setNumberSearchParams({ areaCode: '', contains: '' });
                    setSelectedNumber('');
                    setSelectedAssistant('');
                  }}
                  className={`flex-1 px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'} transition-colors font-semibold`}
                >
                  Cancel
                </button>
                <button
                  onClick={handlePurchaseNumber}
                  disabled={isPurchasing || !selectedNumber || !selectedAssistant}
                  className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all duration-200 ${
                    isPurchasing || !selectedNumber || !selectedAssistant
                      ? 'bg-gray-400 cursor-not-allowed text-gray-600'
                      : 'bg-gradient-to-r from-green-500 to-green-600 text-white hover:shadow-lg hover:shadow-green-500/25'
                  }`}
                >
                  {isPurchasing ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Purchasing...
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Purchase & Configure
                    </div>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Call Details Modal */}
      {isCallDetailsModalOpen && selectedCallLog && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex items-center justify-between`}>
              <div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Call Details
                </h2>
                <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                  {selectedCallLog.call_sid || selectedCallLog.id}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsCallDetailsModalOpen(false);
                  setSelectedCallLog(null);
                }}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Call Information Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Direction
                  </p>
                  <div className="flex items-center gap-2">
                    {selectedCallLog.direction === 'inbound' ? (
                      <>
                        <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                        </svg>
                        <span className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>Inbound</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                        </svg>
                        <span className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>Outbound</span>
                      </>
                    )}
                  </div>
                </div>

                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Status
                  </p>
                  <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                    selectedCallLog.status === 'completed'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : selectedCallLog.status === 'failed'
                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                    {selectedCallLog.status}
                  </span>
                </div>

                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    From
                  </p>
                  <p className={`text-lg font-mono font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {selectedCallLog.from || selectedCallLog.from_number || '-'}
                  </p>
                </div>

                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    To
                  </p>
                  <p className={`text-lg font-mono font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {selectedCallLog.to}
                  </p>
                </div>

                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Duration
                  </p>
                  <p className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {formatDuration(selectedCallLog.duration)}
                  </p>
                </div>

                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Time
                  </p>
                  <p className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {formatDateTime(selectedCallLog.start_time || selectedCallLog.date_created)}
                  </p>
                </div>

                {selectedCallLog.assistant_name && (
                  <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                    <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-blue-400' : 'text-blue-700'}`}>
                      AI Assistant
                    </p>
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                      <p className={`text-lg font-semibold ${isDarkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                        {selectedCallLog.assistant_name}
                      </p>
                    </div>
                  </div>
                )}

                {selectedCallLog.price && (
                  <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                    <p className={`text-xs font-semibold uppercase tracking-wider mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Cost
                    </p>
                    <p className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      ${Math.abs(parseFloat(selectedCallLog.price)).toFixed(4)}
                    </p>
                  </div>
                )}
              </div>

              {/* Recording Section */}
              {selectedCallLog.recording_url && (
                <div className={`mb-6 p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <h3 className={`text-lg font-bold mb-4 flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    Call Recording
                  </h3>
                  <audio
                    controls
                    className="w-full"
                    preload="metadata"
                  >
                    <source src={selectedCallLog.recording_url} type="audio/mpeg" />
                    Your browser does not support audio playback.
                  </audio>
                  <div className="mt-3 flex gap-3">
                    <a
                      href={selectedCallLog.recording_url}
                      download
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isDarkMode
                          ? 'bg-gray-600 hover:bg-gray-500 text-white'
                          : 'bg-gray-200 hover:bg-gray-300 text-neutral-dark'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download Recording
                      </div>
                    </a>
                  </div>
                </div>
              )}

              {/* Transcription Section */}
              {selectedCallLog.transcription_text && (
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <h3 className={`text-lg font-bold mb-4 flex items-center gap-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Call Transcription
                  </h3>
                  <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} max-h-96 overflow-y-auto`}>
                    <p className={`text-sm leading-relaxed whitespace-pre-wrap ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      {selectedCallLog.transcription_text}
                    </p>
                  </div>
                </div>
              )}

              {/* No Recording/Transcription Message */}
              {!selectedCallLog.recording_url && !selectedCallLog.transcription_text && (
                <div className={`p-6 rounded-xl text-center ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    No recording or transcription available for this call.
                  </p>
                  <p className={`text-xs mt-2 ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                    Recordings and transcriptions may take a few minutes to process after the call ends.
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className={`px-6 py-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex justify-end`}>
              <button
                onClick={() => {
                  setIsCallDetailsModalOpen(false);
                  setSelectedCallLog(null);
                }}
                className={`px-6 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'} transition-colors font-semibold`}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Make Call Modal */}
      {isCallModalOpen && selectedPhoneForCall && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-md w-full shadow-2xl`}>
            {/* Modal Header */}
            <div className={`px-6 py-5 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex items-center justify-between`}>
              <div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Make Outbound Call
                </h2>
                <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                  From: {selectedPhoneForCall.phone_number}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsCallModalOpen(false);
                  setCallToNumber('');
                  setSelectedPhoneForCall(null);
                }}
                className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {/* AI Assistant Info */}
              <div className={`mb-6 p-4 rounded-xl ${isDarkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isDarkMode ? 'bg-blue-800' : 'bg-blue-100'}`}>
                    <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <div>
                    <p className={`text-xs font-semibold uppercase tracking-wider ${isDarkMode ? 'text-blue-400' : 'text-blue-700'}`}>
                      AI Assistant
                    </p>
                    <p className={`text-lg font-semibold ${isDarkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                      {selectedPhoneForCall.assigned_assistant_name}
                    </p>
                  </div>
                </div>
              </div>

              {/* Verified Caller IDs List */}
              <div className="mb-6">
                <label className={`block text-sm font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                  Select Verified Number to Call
                </label>

                {isLoadingCallerIds ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  </div>
                ) : verifiedCallerIds.length > 0 ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {verifiedCallerIds.map((caller, index) => (
                      <button
                        key={index}
                        onClick={() => setCallToNumber(caller.phone_number)}
                        className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                          callToNumber === caller.phone_number
                            ? `${isDarkMode ? 'bg-primary/20 border-primary' : 'bg-primary/10 border-primary'}`
                            : `${isDarkMode ? 'bg-gray-700 border-gray-600 hover:border-gray-500' : 'bg-white border-gray-200 hover:border-gray-300'}`
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-1">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                              callToNumber === caller.phone_number
                                ? 'bg-primary text-white'
                                : `${isDarkMode ? 'bg-gray-600 text-gray-300' : 'bg-gray-200 text-gray-600'}`
                            }`}>
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                              </svg>
                            </div>
                            <div className="min-w-0 flex-1">
                              <h4 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                                {caller.friendly_name || 'Verified Number'}
                              </h4>
                              <p className={`text-sm font-mono ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                {caller.phone_number}
                              </p>
                            </div>
                          </div>
                          {callToNumber === caller.phone_number && (
                            <svg className="w-6 h-6 text-primary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className={`p-6 rounded-xl text-center ${isDarkMode ? 'bg-yellow-900/20 border border-yellow-800' : 'bg-yellow-50 border border-yellow-200'}`}>
                    <svg className="w-12 h-12 mx-auto mb-3 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p className={`text-sm font-semibold mb-2 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-900'}`}>
                      No Verified Caller IDs
                    </p>
                    <p className={`text-xs ${isDarkMode ? 'text-yellow-300' : 'text-yellow-800'}`}>
                      You need to verify caller IDs in your Twilio Console before making outbound calls.
                    </p>
                    <a
                      href="https://console.twilio.com/us1/develop/phone-numbers/manage/verified"
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-block mt-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isDarkMode
                          ? 'bg-yellow-800 hover:bg-yellow-700 text-yellow-200'
                          : 'bg-yellow-600 hover:bg-yellow-700 text-white'
                      }`}
                    >
                      Verify Numbers in Twilio →
                    </a>
                  </div>
                )}
              </div>

              {/* Info Box */}
              <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-green-900/20 border border-green-800' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-start gap-2">
                  <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className={`text-sm font-semibold ${isDarkMode ? 'text-green-400' : 'text-green-900'}`}>
                      How it works
                    </p>
                    <p className={`text-xs mt-1 ${isDarkMode ? 'text-green-300' : 'text-green-800'}`}>
                      The recipient will receive a call from <strong>{selectedPhoneForCall.phone_number}</strong> and will be connected to your AI assistant <strong>{selectedPhoneForCall.assigned_assistant_name}</strong>.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className={`px-6 py-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} flex gap-3`}>
              <button
                onClick={() => {
                  setIsCallModalOpen(false);
                  setCallToNumber('');
                  setSelectedPhoneForCall(null);
                }}
                className={`flex-1 px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-neutral-light hover:bg-neutral-mid/20 text-neutral-dark'} transition-colors font-semibold`}
              >
                Cancel
              </button>
              <button
                onClick={handleMakeCall}
                disabled={isInitiatingCall || !callToNumber.trim()}
                className={`flex-1 px-4 py-3 rounded-xl font-semibold transition-all duration-200 ${
                  isInitiatingCall || !callToNumber.trim()
                    ? 'bg-gray-400 cursor-not-allowed text-gray-600'
                    : 'bg-gradient-to-r from-green-500 to-green-600 text-white hover:shadow-lg hover:shadow-green-500/25'
                }`}
              >
                {isInitiatingCall ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Calling...
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                    Make Call
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

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

export default function PhoneNumbersPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      <PhoneNumbersPageContent />
    </Suspense>
  );
}
