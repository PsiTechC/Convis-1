'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { NAV_ITEMS, NavigationItem } from '../components/Navigation';
import { TopBar } from '../components/TopBar';

interface User {
  id?: string;
  _id?: string;
  clientId?: string;
  email: string;
  companyName?: string;
  phoneNumber?: string;
}

type SupportedProvider = 'openai' | 'anthropic' | 'azure_openai' | 'google' | 'custom';

interface StoredApiKey {
  id: string;
  user_id: string;
  provider: SupportedProvider;
  label: string;
  description?: string | null;
  last_four: string;
  created_at: string;
  updated_at: string;
}

interface ApiKeyFormState {
  label: string;
  provider: SupportedProvider;
  api_key: string;
  description: string;
}

const PROVIDER_OPTIONS: { value: SupportedProvider; label: string; helper: string }[] = [
  { value: 'openai', label: 'OpenAI', helper: 'Supports GPT-4o Realtime and standard completions' },
  { value: 'anthropic', label: 'Anthropic', helper: 'Claude models for text generation' },
  { value: 'azure_openai', label: 'Azure OpenAI', helper: 'Managed OpenAI via Microsoft Azure' },
  { value: 'google', label: 'Google Vertex', helper: 'Gemini & PaLM APIs via Google Cloud' },
  { value: 'custom', label: 'Custom Provider', helper: 'Any other compatible AI API' },
];

function getUserInitials(name?: string, email?: string): string {
  if (name?.trim()) {
    const parts = name.trim().split(/\s+/).slice(0, 2);
    const initials = parts.map((part) => part[0]?.toUpperCase()).join('');
    if (initials) {
      return initials;
    }
  }
  if (email?.trim()) {
    return email.trim()[0]?.toUpperCase() || 'U';
  }
  return 'U';
}

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'apiKeys'>('profile');

  // Profile form data
  const [profileData, setProfileData] = useState({
    companyName: '',
    email: '',
    phoneNumber: '',
  });

  // Password form data
  const [passwordData, setPasswordData] = useState({
    newPassword: '',
    confirmPassword: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [apiKeys, setApiKeys] = useState<StoredApiKey[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [editingKey, setEditingKey] = useState<StoredApiKey | null>(null);
  const [keyForm, setKeyForm] = useState<ApiKeyFormState>({
    label: '',
    provider: 'openai',
    api_key: '',
    description: '',
  });
  const [showKeyValue, setShowKeyValue] = useState(false);
  const [keyFormError, setKeyFormError] = useState<string | null>(null);
  const [deletingKeyId, setDeletingKeyId] = useState<string | null>(null);
  const fetchApiKeys = async (userId: string, token: string) => {
    try {
      setIsLoadingKeys(true);
      setKeyError(null);
      const response = await fetch(`${API_URL}/api/ai-keys/user/${userId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch saved API keys');
      }

      setApiKeys(Array.isArray(data.keys) ? data.keys : []);
    } catch (err) {
      setKeyError(err instanceof Error ? err.message : 'Unable to retrieve saved API keys.');
      setApiKeys([]);
    } finally {
      setIsLoadingKeys(false);
    }
  };

  const resetKeyModal = () => {
    setEditingKey(null);
    setKeyForm({
      label: '',
      provider: 'openai',
      api_key: '',
      description: '',
    });
    setShowKeyValue(false);
    setKeyFormError(null);
  };

  const closeKeyModal = () => {
    setIsKeyModalOpen(false);
    resetKeyModal();
  };

  const openAddKeyModal = () => {
    resetKeyModal();
    setIsKeyModalOpen(true);
  };

  const openEditKeyModal = (key: StoredApiKey) => {
    setEditingKey(key);
    setKeyForm({
      label: key.label,
      provider: key.provider,
      api_key: '',
      description: key.description || '',
    });
    setShowKeyValue(false);
    setKeyFormError(null);
    setIsKeyModalOpen(true);
  };

  const handleKeyFormChange = (field: keyof ApiKeyFormState, value: string) => {
    setKeyForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSaveApiKey = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setKeyFormError(null);

    const token = localStorage.getItem('token');
    const resolvedUserId = user?.clientId || user?._id || user?.id;

    if (!token || !resolvedUserId) {
      setKeyFormError('You must be logged in to manage API keys.');
      return;
    }

    if (!keyForm.label.trim()) {
      setKeyFormError('Please provide a label to help identify this key.');
      return;
    }

    if (!editingKey && !keyForm.api_key.trim()) {
      setKeyFormError('The API key value is required.');
      return;
    }

    try {
      setIsSavingKey(true);
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      if (editingKey) {
        const payload: Record<string, unknown> = {};
        if (keyForm.label.trim() && keyForm.label.trim() !== editingKey.label) {
          payload.label = keyForm.label.trim();
        }
        if (keyForm.provider !== editingKey.provider) {
          payload.provider = keyForm.provider;
        }
        if ((keyForm.description || '').trim() !== (editingKey.description || '')) {
          payload.description = keyForm.description.trim();
        }
        if (keyForm.api_key.trim()) {
          payload.api_key = keyForm.api_key.trim();
        }

        if (Object.keys(payload).length === 0) {
          setKeyFormError('No changes detected. Update a field before saving.');
          return;
        }

        const response = await fetch(`${API_URL}/api/ai-keys/${editingKey.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(payload),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to update API key.');
        }
      } else {
        const payload = {
          user_id: resolvedUserId,
          provider: keyForm.provider,
          label: keyForm.label.trim(),
          api_key: keyForm.api_key.trim(),
          description: keyForm.description.trim() || undefined,
        };

        const response = await fetch(`${API_URL}/api/ai-keys/`, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to save API key.');
        }
      }

      await fetchApiKeys(resolvedUserId, token);
      setSuccessMessage(editingKey ? 'API key updated successfully!' : 'API key added successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
      closeKeyModal();
    } catch (err) {
      setKeyFormError(err instanceof Error ? err.message : 'Failed to save API key.');
    } finally {
      setIsSavingKey(false);
    }
  };

  const handleDeleteApiKey = async (key: StoredApiKey) => {
    const token = localStorage.getItem('token');
    const resolvedUserId = user?.clientId || user?._id || user?.id;

    if (!token || !resolvedUserId) {
      setKeyError('You must be logged in to delete API keys.');
      return;
    }

    const confirmed = window.confirm(`Delete API key "${key.label}"? Assistants using it will need a new key.`);
    if (!confirmed) {
      return;
    }

    try {
      setDeletingKeyId(key.id);
      const response = await fetch(`${API_URL}/api/ai-keys/${key.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok && response.status !== 204) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to delete API key.');
      }

      await fetchApiKeys(resolvedUserId, token);
      setSuccessMessage('API key deleted successfully.');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setKeyError(err instanceof Error ? err.message : 'Failed to delete API key.');
    } finally {
      setDeletingKeyId(null);
    }
  };

  const displayProviderLabel = (provider: SupportedProvider) => {
    const option = PROVIDER_OPTIONS.find((opt) => opt.value === provider);
    return option ? option.label : provider;
  };

  const formatDateDisplay = (value: string) => {
    try {
      return new Date(value).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return value;
    }
  };

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.convis.ai';

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
      setProfileData({
        companyName: userData.companyName || '',
        email: userData.email || '',
        phoneNumber: userData.phoneNumber || '',
      });

      const resolvedUserId = userData.clientId || userData._id || userData.id;
      if (resolvedUserId) {
        fetchApiKeys(resolvedUserId, token);
      }
    }

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }
  }, [router]);

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
    router.push(navItem.href);
  };

  const navigationItems = useMemo(() => NAV_ITEMS, []);
  const userInitial = useMemo(() => getUserInitials(user?.companyName || user?.fullName || user?.name, user?.email), [user]);
  const userGreeting = useMemo(() => {
    const candidates = [
      user?.firstName,
      user?.fullName,
      user?.name,
      user?.username,
      user?.email,
      user?.companyName,
    ].filter((value) => typeof value === 'string' && value.trim().length > 0) as string[];

    if (candidates.length === 0) return undefined;
    const preferred = candidates[0];
    if (preferred.includes('@')) {
      return preferred.split('@')[0];
    }
    return preferred.split(' ')[0];
  }, [user]);


  const userInitials = getUserInitials(profileData.companyName, profileData.email);
  const companyDisplayName = profileData.companyName?.trim() || 'Your company name';
  const emailDisplay = profileData.email || 'Add email address';
  const phoneDisplay = profileData.phoneNumber || 'Add phone number';

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfileData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateProfileForm = () => {
    const newErrors: Record<string, string> = {};

    if (!profileData.companyName.trim()) {
      newErrors.companyName = 'Company name is required';
    }

    if (!profileData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(profileData.email)) {
      newErrors.email = 'Email is invalid';
    }

    if (!profileData.phoneNumber.trim()) {
      newErrors.phoneNumber = 'Phone number is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePasswordForm = () => {
    const newErrors: Record<string, string> = {};

    if (!passwordData.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (passwordData.newPassword.length < 6) {
      newErrors.newPassword = 'Password must be at least 6 characters';
    }

    if (!passwordData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (passwordData.newPassword !== passwordData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrors({});

    if (!validateProfileForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      const userId = user?.id || user?._id || user?.clientId;

      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          companyName: profileData.companyName,
          email: profileData.email,
          phoneNumber: profileData.phoneNumber,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update profile');
      }

      const updatedUser = await response.json();

      // Update local storage
      const updatedUserData = { ...user, ...profileData };
      localStorage.setItem('user', JSON.stringify(updatedUserData));
      setUser(updatedUserData);

      setSuccessMessage('Profile updated successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      if (error instanceof Error) {
        setErrors({ submit: error.message });
      } else {
        setErrors({ submit: 'Failed to update profile. Please try again.' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrors({});

    if (!validatePasswordForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/forgot_password/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: user?.email,
          newPassword: passwordData.newPassword,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update password');
      }

      setSuccessMessage('Password changed successfully!');
      setPasswordData({ newPassword: '', confirmPassword: '' });
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      if (error instanceof Error) {
        setErrors({ submit: error.message });
      } else {
        setErrors({ submit: 'Failed to change password. Please try again.' });
      }
    } finally {
      setIsLoading(false);
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
                onClick={() => handleNavigation(item)}
                className={`w-full flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-start'} ${isSidebarCollapsed ? 'px-3' : 'px-4'} py-3 rounded-xl transition-all duration-200 group ${
                  item.name === 'Settings'
                    ? `${isDarkMode ? 'bg-gray-700 text-white' : 'bg-primary/10 text-primary'} font-medium`
                    : `${isDarkMode ? 'text-gray-400 hover:bg-gray-700 hover:text-white' : 'text-neutral-mid hover:bg-neutral-light hover:text-primary'}`
                }`}
              >
                <svg className={`w-6 h-6 flex-shrink-0 ${isSidebarCollapsed ? '' : 'mr-3'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {item.icon}
                </svg>
                {!isSidebarCollapsed && (
                  <span className="whitespace-nowrap">{item.name}</span>
                )}
              </button>
            ))}
          </nav>

          {/* Logout Button */}
          <div className="p-4 border-t border-neutral-mid/10">
            <button
              onClick={handleLogout}
              className={`w-full flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-start'} ${isSidebarCollapsed ? 'px-3' : 'px-4'} py-3 rounded-xl transition-all duration-200 ${isDarkMode ? 'text-red-400 hover:bg-red-500/10' : 'text-red-600 hover:bg-red-50'}`}
            >
              <svg className={`w-6 h-6 flex-shrink-0 ${isSidebarCollapsed ? '' : 'mr-3'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              {!isSidebarCollapsed && <span>Logout</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`${isSidebarCollapsed ? 'lg:ml-20' : 'lg:ml-20'} transition-all duration-300`}>
        <TopBar
          isDarkMode={isDarkMode}
          toggleTheme={toggleTheme}
          onLogout={handleLogout}
          userInitial={userInitial}
          userLabel={userGreeting}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
        />

        {/* Page Content */}
        <main className="px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-6xl space-y-6">
            <header>
              <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>Settings</h1>
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>Update your workspace preferences, billing details, and integrations.</p>
            </header>

            <section className={`overflow-hidden rounded-3xl border shadow-xl ${isDarkMode ? 'bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 border-gray-700/70' : 'bg-gradient-to-r from-primary/10 via-white to-primary/5 border-primary/10'}`}>
              <div className="grid items-center gap-8 p-6 sm:p-8 lg:p-10 lg:grid-cols-[1.1fr_0.9fr]">
                <div className="space-y-4">
                  <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${isDarkMode ? 'bg-primary/20 text-primary/80' : 'bg-primary/10 text-primary'}`}>
                    Account Snapshot
                  </span>
                  <h2 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    Customize your Convis experience
                  </h2>
                  <p className={`${isDarkMode ? 'text-gray-300' : 'text-neutral-mid'} max-w-xl`}>
                    Keep your workspace information, preferences, and security details current. All updates sync instantly across your team.
                  </p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className={`rounded-2xl border px-4 py-3 backdrop-blur ${isDarkMode ? 'border-gray-700/70 bg-gray-900/60 text-gray-200' : 'border-white/70 bg-white/80 text-neutral-dark shadow-sm'}`}>
                      <p className="text-xs uppercase tracking-wide opacity-70">Email</p>
                      <p className="font-semibold truncate">{emailDisplay}</p>
                    </div>
                    <div className={`rounded-2xl border px-4 py-3 backdrop-blur ${isDarkMode ? 'border-gray-700/70 bg-gray-900/60 text-gray-200' : 'border-white/70 bg-white/80 text-neutral-dark shadow-sm'}`}>
                      <p className="text-xs uppercase tracking-wide opacity-70">Phone</p>
                      <p className="font-semibold truncate">{phoneDisplay}</p>
                    </div>
                  </div>
                </div>
                <div className="relative h-48 sm:h-52 lg:h-60">
                  <div className={`absolute inset-0 rounded-[28px] ${isDarkMode ? 'bg-primary/15' : 'bg-white/70'} backdrop-blur-sm`} />
                  <Image
                    src="/window.svg"
                    alt="Settings illustration"
                    fill
                    priority
                    className="object-contain p-6"
                  />
                </div>
              </div>
            </section>

            {successMessage && (
              <div className={`border rounded-2xl p-4 ${isDarkMode ? 'bg-green-900/40 border-green-700' : 'bg-green-50 border-green-200'}`}>
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm font-medium">{successMessage}</p>
                </div>
              </div>
            )}

            {errors.submit && (
              <div className={`border rounded-2xl p-4 ${isDarkMode ? 'bg-red-900/40 border-red-700' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm font-medium">{errors.submit}</p>
                </div>
              </div>
            )}

            <div className={`${isDarkMode ? 'bg-gray-800/90 border-gray-700' : 'bg-white border-neutral-mid/10'} border rounded-3xl shadow-xl overflow-hidden`}>
              <div className="grid gap-0 lg:grid-cols-[320px_1fr]">
                <aside className={`p-6 sm:p-8 space-y-6 ${isDarkMode ? 'bg-gray-900/40 border-b border-gray-700/70 lg:border-b-0 lg:border-r' : 'bg-gradient-to-b from-primary/5 via-white to-white border-b border-neutral-mid/10 lg:border-b-0 lg:border-r'}`}>
                  <div className="flex flex-col items-center gap-5 text-center lg:items-start lg:text-left">
                    <div className={`w-24 h-24 rounded-3xl flex items-center justify-center text-2xl font-semibold ${isDarkMode ? 'bg-primary/20 text-primary/80 border border-primary/40' : 'bg-primary/10 text-primary border border-primary/20'}`}>
                      {userInitials}
                    </div>
                    <div className="space-y-1">
                      <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                        {companyDisplayName}
                      </h3>
                      <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>{emailDisplay}</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <h4 className={`text-xs font-semibold uppercase tracking-wide ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Account Details
                      </h4>
                      <ul className="mt-3 space-y-3">
                        <li className={`flex items-center gap-3 text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                          <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${isDarkMode ? 'bg-gray-800 text-primary' : 'bg-primary/10 text-primary'}`}>
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l9 6 9-6M5 5h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z" />
                            </svg>
                          </span>
                          <span className="truncate">{emailDisplay}</span>
                        </li>
                        <li className={`flex items-center gap-3 text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                          <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${isDarkMode ? 'bg-gray-800 text-primary' : 'bg-primary/10 text-primary'}`}>
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2 5a2 2 0 012-2h1.28a1 1 0 01.948.684l1.284 3.853a1 1 0 01-.502 1.21l-1.607.804a11.042 11.042 0 006.236 6.236l.804-1.607a1 1 0 011.21-.502l3.853 1.284a1 1 0 01.684.948V20a2 2 0 01-2 2h-1C7.82 22 2 16.18 2 9V7a2 2 0 012-2z" />
                            </svg>
                          </span>
                          <span className="truncate">{phoneDisplay}</span>
                        </li>
                      </ul>
                    </div>
                    <div className={`${isDarkMode ? 'border border-gray-700/80 bg-gray-900/50' : 'border border-primary/20 bg-primary/10'} rounded-2xl p-4`}>
                      <p className={`text-xs leading-relaxed ${isDarkMode ? 'text-gray-300' : 'text-primary/90'}`}>
                        Pro tip: Keep your contact details accurate so notifications and billing updates always reach you.
                      </p>
                    </div>
                  </div>
                </aside>
                <div className="flex flex-col">
                  <div className={`flex flex-col sm:flex-row border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
                    <button
                      onClick={() => setActiveTab('profile')}
                      className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${activeTab === 'profile'
                        ? `${isDarkMode ? 'text-primary bg-gray-800 border-b-2 border-primary' : 'text-primary bg-primary/5 border-b-2 border-primary'}`
                        : `${isDarkMode ? 'text-gray-400 hover:text-white hover:bg-gray-800/80' : 'text-neutral-mid hover:text-neutral-dark hover:bg-neutral-light/60'}`}`}
                    >
                      Profile Information
                    </button>
                    <button
                      onClick={() => setActiveTab('password')}
                      className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${activeTab === 'password'
                        ? `${isDarkMode ? 'text-primary bg-gray-800 border-b-2 border-primary' : 'text-primary bg-primary/5 border-b-2 border-primary'}`
                        : `${isDarkMode ? 'text-gray-400 hover:text-white hover:bg-gray-800/80' : 'text-neutral-mid hover:text-neutral-dark hover:bg-neutral-light/60'}`}`}
                    >
                      Change Password
                    </button>
                    <button
                      onClick={() => setActiveTab('apiKeys')}
                      className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${activeTab === 'apiKeys'
                        ? `${isDarkMode ? 'text-primary bg-gray-800 border-b-2 border-primary' : 'text-primary bg-primary/5 border-b-2 border-primary'}`
                        : `${isDarkMode ? 'text-gray-400 hover:text-white hover:bg-gray-800/80' : 'text-neutral-mid hover:text-neutral-dark hover:bg-neutral-light/60'}`}`}
                    >
                      AI API Keys
                    </button>
                  </div>
                  <div className="p-6 sm:p-8">
                    {activeTab === 'profile' && (
                      <form onSubmit={handleProfileSubmit} className="space-y-6">
                        <div>
                          <label htmlFor="companyName" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-2`}>
                            Company Name
                          </label>
                          <input
                            type="text"
                            id="companyName"
                            name="companyName"
                            value={profileData.companyName}
                            onChange={handleProfileChange}
                            className={`w-full px-4 py-3 rounded-xl border ${errors.companyName
                              ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                              : `${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-neutral-mid/20 bg-white'} focus:border-primary focus:ring-2 focus:ring-primary/10`
                            } focus:outline-none transition-all duration-200`}
                            placeholder="Your company name"
                          />
                          {errors.companyName && (
                            <p className="mt-1.5 text-xs text-red-600">{errors.companyName}</p>
                          )}
                        </div>

                        <div>
                          <label htmlFor="email" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-2`}>
                            Email Address
                          </label>
                          <input
                            type="email"
                            id="email"
                            name="email"
                            value={profileData.email}
                            onChange={handleProfileChange}
                            className={`w-full px-4 py-3 rounded-xl border ${errors.email
                              ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                              : `${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-neutral-mid/20 bg-white'} focus:border-primary focus:ring-2 focus:ring-primary/10`
                            } focus:outline-none transition-all duration-200`}
                            placeholder="your@email.com"
                          />
                          {errors.email && (
                            <p className="mt-1.5 text-xs text-red-600">{errors.email}</p>
                          )}
                        </div>

                        <div>
                          <label htmlFor="phoneNumber" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-2`}>
                            Phone Number
                          </label>
                          <input
                            type="tel"
                            id="phoneNumber"
                            name="phoneNumber"
                            value={profileData.phoneNumber}
                            onChange={handleProfileChange}
                            className={`w-full px-4 py-3 rounded-xl border ${errors.phoneNumber
                              ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                              : `${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-neutral-mid/20 bg-white'} focus:border-primary focus:ring-2 focus:ring-primary/10`
                            } focus:outline-none transition-all duration-200`}
                            placeholder="+1 (555) 000-0000"
                          />
                          {errors.phoneNumber && (
                            <p className="mt-1.5 text-xs text-red-600">{errors.phoneNumber}</p>
                          )}
                        </div>

                        <button
                          type="submit"
                          disabled={isLoading}
                          className="w-full bg-gradient-to-r from-primary to-primary/90 text-white py-3.5 px-6 rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isLoading ? (
                            <span className="flex items-center justify-center gap-2">
                              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Updating...
                            </span>
                          ) : (
                            'Update Profile'
                          )}
                        </button>
                      </form>
                    )}

                    {activeTab === 'password' && (
                      <form onSubmit={handlePasswordSubmit} className="space-y-6">
                        <div>
                          <label htmlFor="newPassword" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-2`}>
                            New Password
                          </label>
                          <div className="relative">
                            <input
                              type={showNewPassword ? 'text' : 'password'}
                              id="newPassword"
                              name="newPassword"
                              value={passwordData.newPassword}
                              onChange={handlePasswordChange}
                              className={`w-full px-4 py-3 rounded-xl border ${errors.newPassword
                                ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                                : `${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-neutral-mid/20 bg-white'} focus:border-primary focus:ring-2 focus:ring-primary/10`
                              } focus:outline-none transition-all duration-200 pr-11`}
                              placeholder="Enter new password"
                            />
                            <button
                              type="button"
                              onClick={() => setShowNewPassword(!showNewPassword)}
                              className={`absolute right-3 top-1/2 -translate-y-1/2 ${isDarkMode ? 'text-gray-400 hover:text-white' : 'text-neutral-mid hover:text-primary'} transition-colors p-1.5 rounded-lg hover:bg-primary/5`}
                            >
                              {showNewPassword ? (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                                </svg>
                              ) : (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                              )}
                            </button>
                          </div>
                          {errors.newPassword && (
                            <p className="mt-1.5 text-xs text-red-600">{errors.newPassword}</p>
                          )}
                        </div>

                        <div>
                          <label htmlFor="confirmPassword" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-2`}>
                            Confirm New Password
                          </label>
                          <div className="relative">
                            <input
                              type={showConfirmPassword ? 'text' : 'password'}
                              id="confirmPassword"
                              name="confirmPassword"
                              value={passwordData.confirmPassword}
                              onChange={handlePasswordChange}
                              className={`w-full px-4 py-3 rounded-xl border ${errors.confirmPassword
                                ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                                : `${isDarkMode ? 'border-gray-600 bg-gray-700 text-white' : 'border-neutral-mid/20 bg-white'} focus:border-primary focus:ring-2 focus:ring-primary/10`
                              } focus:outline-none transition-all duration-200 pr-11`}
                              placeholder="Confirm new password"
                            />
                            <button
                              type="button"
                              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                              className={`absolute right-3 top-1/2 -translate-y-1/2 ${isDarkMode ? 'text-gray-400 hover:text-white' : 'text-neutral-mid hover:text-primary'} transition-colors p-1.5 rounded-lg hover:bg-primary/5`}
                            >
                              {showConfirmPassword ? (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                                </svg>
                              ) : (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                              )}
                            </button>
                          </div>
                          {errors.confirmPassword && (
                            <p className="mt-1.5 text-xs text-red-600">{errors.confirmPassword}</p>
                          )}
                        </div>

                        <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-700/50' : 'bg-blue-50'} border ${isDarkMode ? 'border-gray-600' : 'border-blue-100'}`}>
                          <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-blue-800'}`}>
                            <strong>Note:</strong> Your password must be at least 6 characters long.
                          </p>
                        </div>

                        <button
                          type="submit"
                          disabled={isLoading}
                          className="w-full bg-gradient-to-r from-primary to-primary/90 text-white py-3.5 px-6 rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isLoading ? (
                            <span className="flex items-center justify-center gap-2">
                              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Changing Password...
                            </span>
                          ) : (
                            'Change Password'
                          )}
                        </button>
                      </form>
                    )}

                    {activeTab === 'apiKeys' && (
                      <div className="space-y-6">
                        <div className={`flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-2xl border ${isDarkMode ? 'border-gray-700 bg-gray-900/60' : 'border-primary/15 bg-primary/5'} p-6`}>
                          <div className="space-y-1">
                            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>Manage AI Provider Keys</h3>
                            <p className={`${isDarkMode ? 'text-gray-300' : 'text-neutral-mid'} text-sm max-w-2xl`}>
                              Securely store API keys from OpenAI, Anthropic, Azure OpenAI, and more. Saved keys can be selected when configuring AI assistants and are fully encrypted at rest.
                            </p>
                          </div>
                          <button
                            onClick={openAddKeyModal}
                            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-primary to-primary/80 text-white font-semibold shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all duration-200"
                          >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Add API Key
                          </button>
                        </div>

                        {keyError && (
                          <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800 text-red-300' : 'bg-red-50 border-red-200 text-red-700'} border rounded-xl p-4 text-sm`}>
                            {keyError}
                          </div>
                        )}

                        {isLoadingKeys ? (
                          <div className="flex items-center justify-center py-16">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
                          </div>
                        ) : apiKeys.length > 0 ? (
                          <div className="space-y-4">
                            {apiKeys.map((key) => (
                              <div
                                key={key.id}
                                className={`rounded-2xl border ${isDarkMode ? 'border-gray-700 bg-gray-900/70' : 'border-neutral-mid/10 bg-white'} p-6 flex flex-col gap-4`}
                              >
                                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                                  <div>
                                    <div className="flex flex-wrap items-center gap-2">
                                      <h4 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                                        {key.label}
                                      </h4>
                                      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${isDarkMode ? 'bg-primary/15 text-primary' : 'bg-primary/10 text-primary'}`}>
                                        {displayProviderLabel(key.provider)}
                                      </span>
                                    </div>
                                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>
                                      •••• {key.last_four}
                                    </p>
                                    {key.description && (
                                      <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                                        {key.description}
                                      </p>
                                    )}
                                  </div>
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => openEditKeyModal(key)}
                                      className={`px-4 py-2 rounded-lg text-sm font-medium ${isDarkMode ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-neutral-light hover:bg-neutral-mid/10 text-neutral-dark'} transition-colors`}
                                    >
                                      Edit
                                    </button>
                                    <button
                                      onClick={() => handleDeleteApiKey(key)}
                                      disabled={deletingKeyId === key.id}
                                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${isDarkMode ? 'bg-red-900/30 text-red-400 hover:bg-red-900/50' : 'bg-red-50 text-red-600 hover:bg-red-100'} disabled:opacity-50 disabled:cursor-not-allowed`}
                                    >
                                      {deletingKeyId === key.id ? 'Deleting…' : 'Delete'}
                                    </button>
                                  </div>
                                </div>
                                <div className={`grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                                  <div>
                                    <span className="block text-xs uppercase tracking-wide opacity-70">Created</span>
                                    <span>{formatDateDisplay(key.created_at)}</span>
                                  </div>
                                  <div>
                                    <span className="block text-xs uppercase tracking-wide opacity-70">Updated</span>
                                    <span>{formatDateDisplay(key.updated_at)}</span>
                                  </div>
                                  <div>
                                    <span className="block text-xs uppercase tracking-wide opacity-70">Provider</span>
                                    <span>{displayProviderLabel(key.provider)}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className={`rounded-2xl border-dashed border-2 ${isDarkMode ? 'border-gray-700 text-gray-400' : 'border-neutral-mid/30 text-neutral-mid'} p-10 text-center space-y-3`}>
                            <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center bg-primary/10 text-primary">
                              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                            <h4 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>No API keys added yet</h4>
                            <p className="text-sm max-w-xl mx-auto">
                              Save your provider API keys once and reuse them across all voice assistants. Click <span className="font-semibold text-primary">Add API Key</span> to secure your first key.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>

        {isKeyModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
            <div className={`w-full max-w-lg rounded-3xl border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-neutral-mid/10'} p-6 sm:p-8 relative shadow-2xl`}>
              <button
                onClick={closeKeyModal}
                className={`absolute right-4 top-4 p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-800 text-gray-400 hover:text-white' : 'hover:bg-neutral-light text-neutral-mid hover:text-neutral-dark'} transition-colors`}
                aria-label="Close modal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              <div className="space-y-6 mt-4">
                <div>
                  <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {editingKey ? 'Edit API Key' : 'Add a New API Key'}
                  </h3>
                  <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-sm mt-1`}>
                    {editingKey
                      ? 'Update the key details. Leave the API Key field blank to keep the current secret.'
                      : 'Provide a descriptive label and paste your API key exactly as provided by the AI vendor.'}
                  </p>
                </div>

                {keyFormError && (
                  <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800 text-red-200' : 'bg-red-50 border-red-200 text-red-700'} border rounded-xl p-3 text-sm`}>
                    {keyFormError}
                  </div>
                )}

                <form onSubmit={handleSaveApiKey} className="space-y-5">
                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-neutral-dark'}`}>
                      Key Label <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={keyForm.label}
                      onChange={(event) => handleKeyFormChange('label', event.target.value)}
                      className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-800 text-white placeholder-gray-500' : 'border-neutral-mid/20 bg-white text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                      placeholder="Production Realtime Key"
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-neutral-dark'}`}>
                      Provider <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={keyForm.provider}
                      onChange={(event) => handleKeyFormChange('provider', event.target.value as SupportedProvider)}
                      className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-800 text-white' : 'border-neutral-mid/20 bg-white text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                    >
                      {PROVIDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'}`}>
                      {PROVIDER_OPTIONS.find((option) => option.value === keyForm.provider)?.helper}
                    </p>
                  </div>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-neutral-dark'}`}>
                      API Key {editingKey ? <span className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-xs font-normal`}>(leave blank to keep existing)</span> : <span className="text-red-500">*</span>}
                    </label>
                    <div className="relative">
                      <input
                        type={showKeyValue ? 'text' : 'password'}
                        value={keyForm.api_key}
                        onChange={(event) => handleKeyFormChange('api_key', event.target.value)}
                        className={`w-full px-4 py-3 pr-12 rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-800 text-white placeholder-gray-500' : 'border-neutral-mid/20 bg-white text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                        placeholder={editingKey ? 'Enter a new key if you want to rotate it' : 'sk-...'}
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeyValue(!showKeyValue)}
                        className={`absolute right-3 top-1/2 -translate-y-1/2 px-2 py-1 rounded-lg text-xs font-medium ${isDarkMode ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors`}
                      >
                        {showKeyValue ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-neutral-dark'}`}>
                      Description <span className={`${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'} text-xs font-normal`}>(optional)</span>
                    </label>
                    <textarea
                      rows={3}
                      value={keyForm.description}
                      onChange={(event) => handleKeyFormChange('description', event.target.value)}
                      className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-800 text-white placeholder-gray-500' : 'border-neutral-mid/20 bg-white text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none`}
                      placeholder="Notes about rate limits or usage context"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={closeKeyModal}
                      className={`px-4 py-2 rounded-lg text-sm font-medium ${isDarkMode ? 'text-gray-300 hover:bg-gray-800' : 'text-neutral-mid hover:bg-neutral-light'}`}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingKey}
                      className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-primary to-primary/80 text-white text-sm font-semibold shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {isSavingKey ? 'Saving…' : editingKey ? 'Update Key' : 'Save Key'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
