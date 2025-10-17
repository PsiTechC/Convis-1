'use client';

import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CreateCampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  isDarkMode: boolean;
  userId: string;
}

interface AIAgent {
  id: string;
  name: string;
  description?: string;
}

interface PhoneNumber {
  _id: string;
  phone_number: string;
  friendly_name?: string;
}

export default function CreateCampaignModal({
  isOpen,
  onClose,
  onSuccess,
  isDarkMode,
  userId
}: CreateCampaignModalProps) {
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [aiAgents, setAiAgents] = useState<AIAgent[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Form data
  const [formData, setFormData] = useState({
    name: '',
    country: 'US',
    assistant_id: '',
    caller_id: '',
    timezone: 'America/New_York',
    start_time: '09:00',
    end_time: '17:00',
    working_days: [0, 1, 2, 3, 4], // Mon-Fri
    start_date: '',
    end_date: '',
    max_attempts: 3,
    retry_delays: '15,60,1440',
    calendar_enabled: false,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'CA', name: 'Canada' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'AU', name: 'Australia' },
    { code: 'IN', name: 'India' },
  ];

  const timezones = [
    { value: 'America/New_York', label: 'Eastern Time (ET)' },
    { value: 'America/Chicago', label: 'Central Time (CT)' },
    { value: 'America/Denver', label: 'Mountain Time (MT)' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
    { value: 'America/Toronto', label: 'Toronto' },
    { value: 'Europe/London', label: 'London' },
    { value: 'Asia/Kolkata', label: 'India' },
    { value: 'Australia/Sydney', label: 'Sydney' },
  ];

  const weekDays = [
    { value: 0, label: 'Mon' },
    { value: 1, label: 'Tue' },
    { value: 2, label: 'Wed' },
    { value: 3, label: 'Thu' },
    { value: 4, label: 'Fri' },
    { value: 5, label: 'Sat' },
    { value: 6, label: 'Sun' },
  ];

  useEffect(() => {
    if (isOpen) {
      fetchAIAgents();
      fetchPhoneNumbers();
    }
  }, [isOpen]);

  const fetchAIAgents = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/ai-assistants/user/${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        console.log('AI Agents API response:', data);
        console.log('AI Agents list:', data.assistants);
        setAiAgents(data.assistants || []);
      } else {
        console.error('Failed to fetch AI agents:', response.status, await response.text());
      }
    } catch (error) {
      console.error('Error fetching AI agents:', error);
    }
  };

  const fetchPhoneNumbers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/phone-numbers/user/${userId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPhoneNumbers(data.phone_numbers || []);
      }
    } catch (error) {
      console.error('Error fetching phone numbers:', error);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const toggleWorkingDay = (day: number) => {
    setFormData(prev => ({
      ...prev,
      working_days: prev.working_days.includes(day)
        ? prev.working_days.filter(d => d !== day)
        : [...prev.working_days, day].sort()
    }));
  };

  const validateStep = (currentStep: number): boolean => {
    const newErrors: Record<string, string> = {};

    if (currentStep === 1) {
      if (!formData.name.trim()) newErrors.name = 'Campaign name is required';
      if (!formData.assistant_id) newErrors.assistant_id = 'Please select an AI agent';
      if (!formData.caller_id) newErrors.caller_id = 'Please select a phone number';
      if (!formData.country) newErrors.country = 'Please select a country';
    }

    if (currentStep === 2) {
      if (!formData.timezone) newErrors.timezone = 'Please select a timezone';
      if (!formData.start_time) newErrors.start_time = 'Start time is required';
      if (!formData.end_time) newErrors.end_time = 'End time is required';
      if (formData.working_days.length === 0) newErrors.working_days = 'Select at least one day';
      if (formData.start_date && formData.end_date) {
        if (new Date(formData.end_date) < new Date(formData.start_date)) {
          newErrors.end_date = 'End date must be after start date';
        }
      }
    }

    if (currentStep === 3) {
      if (!csvFile) newErrors.csvFile = 'Please upload a CSV file with leads';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    setStep(step - 1);
  };

  const handleSubmit = async () => {
    if (!validateStep(step)) return;

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');

      // Step 1: Create campaign
      const campaignData = {
        user_id: userId,
        name: formData.name,
        country: formData.country,
        caller_id: formData.caller_id,
        assistant_id: formData.assistant_id,
        working_window: {
          timezone: formData.timezone,
          start: formData.start_time,
          end: formData.end_time,
          days: formData.working_days
        },
        retry_policy: {
          max_attempts: formData.max_attempts,
          retry_after_minutes: formData.retry_delays.split(',').map(Number)
        },
        pacing: {
          calls_per_minute: 1,
          max_concurrent: 1
        },
        start_at: formData.start_date ? new Date(formData.start_date).toISOString() : null,
        stop_at: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      };

      console.log('Creating campaign with data:', campaignData);
      console.log('API URL:', `${API_URL}/api/campaigns`);

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const campaignResponse = await fetch(`${API_URL}/api/campaigns`, {
        method: 'POST',
        headers,
        body: JSON.stringify(campaignData)
      });

      console.log('Response status:', campaignResponse.status);
      console.log('Response headers:', campaignResponse.headers);

      if (!campaignResponse.ok) {
        const errorText = await campaignResponse.text();
        console.error('Campaign creation failed - Raw response:', errorText);

        let errorData: any = {};
        try {
          errorData = JSON.parse(errorText);
        } catch (e) {
          console.error('Could not parse error response as JSON');
        }

        throw new Error(errorData.detail || errorData.message || `Failed to create campaign (${campaignResponse.status})`);
      }

      const campaign = await campaignResponse.json();
      const campaignId = campaign.id || campaign._id;

      // Step 2: Upload leads CSV
      if (csvFile) {
        const formDataUpload = new FormData();
        formDataUpload.append('file', csvFile);

        const uploadResponse = await fetch(
          `${API_URL}/api/campaigns/${campaignId}/leads/upload`,
          {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formDataUpload
          }
        );

        if (!uploadResponse.ok) {
          throw new Error('Failed to upload leads');
        }

        const uploadResult = await uploadResponse.json();
        console.log('Upload result:', uploadResult);
      }

      // Success!
      onSuccess();
      resetForm();
      onClose();
    } catch (error: any) {
      console.error('Error creating campaign:', error);
      alert(error.message || 'Failed to create campaign. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setStep(1);
    setFormData({
      name: '',
      country: 'US',
      assistant_id: '',
      caller_id: '',
      timezone: 'America/New_York',
      start_time: '09:00',
      end_time: '17:00',
      working_days: [0, 1, 2, 3, 4],
      start_date: '',
      end_date: '',
      max_attempts: 3,
      retry_delays: '15,60,1440',
      calendar_enabled: false,
    });
    setCsvFile(null);
    setErrors({});
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setErrors({ csvFile: 'Please upload a CSV file' });
        return;
      }
      setCsvFile(file);
      setErrors(prev => ({ ...prev, csvFile: '' }));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl w-full max-w-2xl my-8`}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-dark'}`}>
              Create New Campaign
            </h2>
            <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Step {step} of 3
            </p>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'} transition-colors`}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="px-6 pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-medium ${step >= 1 ? 'text-primary' : isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Basic Info
            </span>
            <span className={`text-sm font-medium ${step >= 2 ? 'text-primary' : isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Schedule
            </span>
            <span className={`text-sm font-medium ${step >= 3 ? 'text-primary' : isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Upload Leads
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${(step / 3) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Form Content */}
        <div className="p-6">
          {/* Step 1: Basic Information */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Campaign Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="e.g., Q1 Sales Outreach"
                  className={`w-full px-4 py-3 rounded-lg border ${
                    errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  } ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                />
                {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Target Country *
                </label>
                <select
                  value={formData.country}
                  onChange={(e) => handleInputChange('country', e.target.value)}
                  className={`w-full px-4 py-3 rounded-lg border ${
                    errors.country ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  } ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                >
                  <option value="">Select Country</option>
                  {countries.map(country => (
                    <option key={country.code} value={country.code}>{country.name}</option>
                  ))}
                </select>
                {errors.country && <p className="text-red-500 text-sm mt-1">{errors.country}</p>}
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  AI Agent *
                </label>
                <select
                  value={formData.assistant_id}
                  onChange={(e) => handleInputChange('assistant_id', e.target.value)}
                  className={`w-full px-4 py-3 rounded-lg border ${
                    errors.assistant_id ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  } ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                >
                  <option value="">Select AI Agent</option>
                  {aiAgents.map(agent => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
                {errors.assistant_id && <p className="text-red-500 text-sm mt-1">{errors.assistant_id}</p>}
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Caller Phone Number *
                </label>
                <select
                  value={formData.caller_id}
                  onChange={(e) => handleInputChange('caller_id', e.target.value)}
                  className={`w-full px-4 py-3 rounded-lg border ${
                    errors.caller_id ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  } ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                >
                  <option value="">Select Phone Number</option>
                  {phoneNumbers.map(phone => (
                    <option key={phone._id} value={phone.phone_number}>
                      {phone.friendly_name || phone.phone_number}
                    </option>
                  ))}
                </select>
                {errors.caller_id && <p className="text-red-500 text-sm mt-1">{errors.caller_id}</p>}
              </div>
            </div>
          )}

          {/* Step 2: Schedule Configuration */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Timezone *
                </label>
                <select
                  value={formData.timezone}
                  onChange={(e) => handleInputChange('timezone', e.target.value)}
                  className={`w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                >
                  {timezones.map(tz => (
                    <option key={tz.value} value={tz.value}>{tz.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Start Time *
                  </label>
                  <input
                    type="time"
                    value={formData.start_time}
                    onChange={(e) => handleInputChange('start_time', e.target.value)}
                    className={`w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    End Time *
                  </label>
                  <input
                    type="time"
                    value={formData.end_time}
                    onChange={(e) => handleInputChange('end_time', e.target.value)}
                    className={`w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                  />
                </div>
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Working Days *
                </label>
                <div className="flex gap-2">
                  {weekDays.map(day => (
                    <button
                      key={day.value}
                      type="button"
                      onClick={() => toggleWorkingDay(day.value)}
                      className={`flex-1 py-2 px-3 rounded-lg font-medium transition-colors ${
                        formData.working_days.includes(day.value)
                          ? 'bg-primary text-white'
                          : isDarkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {day.label}
                    </button>
                  ))}
                </div>
                {errors.working_days && <p className="text-red-500 text-sm mt-1">{errors.working_days}</p>}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Campaign Start Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => handleInputChange('start_date', e.target.value)}
                    className={`w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Campaign End Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => handleInputChange('end_date', e.target.value)}
                    className={`w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'} focus:ring-2 focus:ring-primary focus:border-transparent`}
                  />
                  {errors.end_date && <p className="text-red-500 text-sm mt-1">{errors.end_date}</p>}
                </div>
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Retry Settings
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={`block text-xs mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Max Attempts
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={formData.max_attempts}
                      onChange={(e) => handleInputChange('max_attempts', parseInt(e.target.value))}
                      className={`w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'}`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      Retry Delays (minutes)
                    </label>
                    <input
                      type="text"
                      value={formData.retry_delays}
                      onChange={(e) => handleInputChange('retry_delays', e.target.value)}
                      placeholder="15,60,1440"
                      className={`w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 ${isDarkMode ? 'bg-gray-700 text-white' : 'bg-white text-dark'}`}
                    />
                  </div>
                </div>
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Comma-separated values in minutes (e.g., 15,60,1440 = 15min, 1hr, 1day)
                </p>
              </div>

              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.calendar_enabled}
                    onChange={(e) => handleInputChange('calendar_enabled', e.target.checked)}
                    className="w-5 h-5 text-primary rounded focus:ring-2 focus:ring-primary"
                  />
                  <span className={`text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Enable calendar booking (auto-book appointments from conversations)
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Step 3: Upload Leads */}
          {step === 3 && (
            <div className="space-y-4">
              <div className={`${isDarkMode ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} border rounded-lg p-4`}>
                <h3 className={`font-semibold mb-2 ${isDarkMode ? 'text-blue-300' : 'text-blue-900'}`}>
                  CSV Format Requirements
                </h3>
                <ul className={`text-sm space-y-1 ${isDarkMode ? 'text-blue-200' : 'text-blue-800'}`}>
                  <li>• Required column: <code className="font-mono bg-blue-900/20 px-1 rounded">phone</code></li>
                  <li>• Optional columns: <code className="font-mono bg-blue-900/20 px-1 rounded">name</code>, <code className="font-mono bg-blue-900/20 px-1 rounded">email</code></li>
                  <li>• Phone numbers can be in any format (will be auto-validated)</li>
                  <li>• Maximum file size: 10MB</li>
                </ul>
              </div>

              <div>
                <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Upload Leads CSV *
                </label>
                <div className={`border-2 border-dashed rounded-lg p-8 text-center ${
                  csvFile ? 'border-green-500 bg-green-50 dark:bg-green-900/20' :
                  errors.csvFile ? 'border-red-500 bg-red-50 dark:bg-red-900/20' :
                  isDarkMode ? 'border-gray-600 bg-gray-700' : 'border-gray-300 bg-gray-50'
                }`}>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="hidden"
                    id="csv-upload"
                  />
                  <label htmlFor="csv-upload" className="cursor-pointer">
                    {csvFile ? (
                      <div>
                        <svg className="w-12 h-12 mx-auto mb-2 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className={`font-medium ${isDarkMode ? 'text-green-300' : 'text-green-700'}`}>
                          {csvFile.name}
                        </p>
                        <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          {(csvFile.size / 1024).toFixed(2)} KB
                        </p>
                        <button
                          type="button"
                          onClick={() => setCsvFile(null)}
                          className="mt-2 text-sm text-primary hover:underline"
                        >
                          Change file
                        </button>
                      </div>
                    ) : (
                      <div>
                        <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className={`font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          Click to upload or drag and drop
                        </p>
                        <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          CSV file (MAX. 10MB)
                        </p>
                      </div>
                    )}
                  </label>
                </div>
                {errors.csvFile && <p className="text-red-500 text-sm mt-1">{errors.csvFile}</p>}
              </div>

              <div className={`${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'} rounded-lg p-4`}>
                <h4 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-dark'}`}>
                  Example CSV Format:
                </h4>
                <pre className={`text-xs p-3 rounded ${isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-white text-gray-700'} overflow-x-auto`}>
{`phone,name,email
+12125551234,John Doe,john@example.com
+14155552345,Jane Smith,jane@example.com
+13105553456,Bob Johnson,bob@example.com`}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className={`flex items-center justify-between p-6 border-t ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <button
            onClick={step === 1 ? onClose : handleBack}
            disabled={isLoading}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              isDarkMode
                ? 'bg-gray-700 text-white hover:bg-gray-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {step === 1 ? 'Cancel' : 'Back'}
          </button>

          <div className="flex gap-2">
            {step < 3 ? (
              <button
                onClick={handleNext}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating...
                  </>
                ) : (
                  'Create Campaign'
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
