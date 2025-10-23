'use client';

import { useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface LeadRecord {
  id: string;
  first_name?: string | null;
  last_name?: string | null;
  name?: string | null;
  raw_number?: string | null;
  e164?: string | null;
  email?: string | null;
  batch_name?: string | null;
  timezone?: string | null;
  status: string;
  attempts: number;
  custom_fields?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface LeadViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  campaignId: string;
  isDarkMode: boolean;
}

export default function LeadViewerModal({
  isOpen,
  onClose,
  campaignId,
  isDarkMode,
}: LeadViewerModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leads, setLeads] = useState<LeadRecord[]>([]);

  useEffect(() => {
    if (!isOpen) return;

    const fetchLeads = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/campaigns/${campaignId}/leads?limit=500`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });

        if (!response.ok) {
          const errorText = await response.text().catch(() => '');
          throw new Error(errorText || 'Failed to load leads');
        }

        const data = await response.json();
        setLeads(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Error loading leads:', err);
        setError(err instanceof Error ? err.message : 'Failed to load leads');
      } finally {
        setIsLoading(false);
      }
    };

    fetchLeads();
  }, [isOpen, campaignId]);

  if (!isOpen) return null;

  const backgroundClass = isDarkMode ? 'bg-gray-900/70' : 'bg-black/40';
  const panelClass = isDarkMode ? 'bg-gray-800 text-gray-100' : 'bg-white text-neutral-dark';
  const borderColor = isDarkMode ? 'border-gray-700' : 'border-neutral-mid/20';

  const formatDateTime = (value?: string) => {
    if (!value) return '—';
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  const formatCustomFieldValue = (value: unknown) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  const getDisplayName = (lead: LeadRecord) => {
    if (lead.first_name || lead.last_name) {
      return `${lead.first_name ?? ''} ${lead.last_name ?? ''}`.trim() || lead.name || '—';
    }
    return lead.name || '—';
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center px-4 py-6 ${backgroundClass}`}>
      <div className={`${panelClass} w-full max-w-5xl rounded-2xl shadow-xl border ${borderColor} max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-mid/10 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold">Campaign Leads</h2>
            <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
              Review the leads that were uploaded for this campaign.
            </p>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
            aria-label="Close lead viewer"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-4 overflow-y-auto">
          {isLoading ? (
            <div className="flex w-full items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          ) : error ? (
            <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800 text-red-200' : 'bg-red-50 border-red-200 text-red-700'} border rounded-xl px-4 py-3`}>
              {error}
            </div>
          ) : leads.length === 0 ? (
            <div className={`${isDarkMode ? 'bg-gray-900/50 border-gray-700 text-gray-300' : 'bg-neutral-light border-neutral-mid/20 text-neutral-600'} border rounded-xl px-4 py-6 text-center`}>
              No leads uploaded yet for this campaign.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-neutral-mid/10 dark:divide-gray-700 text-sm">
                <thead className={isDarkMode ? 'bg-gray-900 text-gray-300' : 'bg-neutral-light text-neutral-mid'}>
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Batch</th>
                    <th className="px-4 py-3 text-left font-semibold">First Name</th>
                    <th className="px-4 py-3 text-left font-semibold">Last Name</th>
                    <th className="px-4 py-3 text-left font-semibold">Full Name</th>
                    <th className="px-4 py-3 text-left font-semibold">Contact Number</th>
                    <th className="px-4 py-3 text-left font-semibold">Timezone</th>
                    <th className="px-4 py-3 text-left font-semibold">Email</th>
                    <th className="px-4 py-3 text-left font-semibold">Status</th>
                    <th className="px-4 py-3 text-left font-semibold">Attempts</th>
                    <th className="px-4 py-3 text-left font-semibold">Updated</th>
                    <th className="px-4 py-3 text-left font-semibold">Custom Fields</th>
                  </tr>
                </thead>
                <tbody className={isDarkMode ? 'divide-y divide-gray-700 text-gray-200' : 'divide-y divide-neutral-mid/10 text-neutral-dark'}>
                  {leads.map((lead) => (
                    <tr key={lead.id}>
                      <td className="px-4 py-3">{lead.batch_name || '—'}</td>
                      <td className="px-4 py-3">{lead.first_name || '—'}</td>
                      <td className="px-4 py-3">{lead.last_name || '—'}</td>
                      <td className="px-4 py-3">{getDisplayName(lead)}</td>
                      <td className="px-4 py-3 font-mono">{lead.e164 || lead.raw_number || '—'}</td>
                      <td className="px-4 py-3">{lead.timezone || '—'}</td>
                      <td className="px-4 py-3">{lead.email || '—'}</td>
                      <td className="px-4 py-3 capitalize">{lead.status}</td>
                      <td className="px-4 py-3 text-center">{lead.attempts}</td>
                      <td className="px-4 py-3">{formatDateTime(lead.updated_at)}</td>
                      <td className="px-4 py-3">
                        {lead.custom_fields && Object.keys(lead.custom_fields).length > 0 ? (
                          <div className="space-y-1">
                            {Object.entries(lead.custom_fields).map(([key, value]) => (
                              <div key={key} className="text-xs">
                                <span className="font-semibold">{key}:</span> {formatCustomFieldValue(value)}
                              </div>
                            ))}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className={`px-6 py-4 border-t ${borderColor} flex justify-end`}>
          <button
            onClick={onClose}
            className={`px-6 py-2 rounded-lg font-medium ${isDarkMode ? 'bg-gray-700 text-white hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors`}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
