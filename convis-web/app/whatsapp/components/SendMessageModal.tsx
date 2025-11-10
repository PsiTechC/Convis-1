'use client';

import { useState, useEffect } from 'react';
import { sendWhatsAppMessage, getWhatsAppTemplates } from '@/lib/whatsapp-api';

interface Props {
  credentialId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function SendMessageModal({ credentialId, onClose, onSuccess }: Props) {
  const [messageType, setMessageType] = useState<'text' | 'template'>('template');
  const [to, setTo] = useState('');
  const [text, setText] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [errors, setErrors] = useState<any>({});

  useEffect(() => {
    if (messageType === 'template') {
      fetchTemplates();
    }
  }, [messageType]);

  const fetchTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const data = await getWhatsAppTemplates(credentialId);
      setTemplates(data);
    } catch (err: any) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: any = {};
    if (!to.trim()) newErrors.to = 'Phone number is required';
    if (messageType === 'text' && !text.trim()) newErrors.text = 'Message text is required';
    if (messageType === 'template' && !templateName) newErrors.templateName = 'Please select a template';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);

    try {
      await sendWhatsAppMessage({
        credential_id: credentialId,
        to: to.startsWith('+') ? to : `+${to}`,
        message_type: messageType,
        text: messageType === 'text' ? text : undefined,
        template_name: messageType === 'template' ? templateName : undefined,
      });

      alert('✅ Message sent successfully!');
      onSuccess();
      onClose();
    } catch (err: any) {
      alert(`Failed to send message: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-3xl bg-white p-8 shadow-2xl">
        <h2 className="text-2xl font-bold text-neutral-dark mb-6">Send WhatsApp Message</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Message Type
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="text"
                  checked={messageType === 'text'}
                  onChange={() => setMessageType('text')}
                  className="text-primary"
                />
                <span>Text Message</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="template"
                  checked={messageType === 'template'}
                  onChange={() => setMessageType('template')}
                  className="text-primary"
                />
                <span>Template</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Recipient Phone Number <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                setErrors((prev: any) => ({ ...prev, to: '' }));
              }}
              placeholder="+919131296862"
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.to
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10`}
            />
            {errors.to && <p className="mt-1.5 text-xs text-red-600">{errors.to}</p>}
            <p className="mt-1.5 text-xs text-neutral-mid">Include country code (e.g., +91 for India)</p>
          </div>

          {messageType === 'text' ? (
            <div>
              <label className="block text-sm font-medium text-neutral-dark mb-2">
                Message <span className="text-red-500">*</span>
              </label>
              <textarea
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  setErrors((prev: any) => ({ ...prev, text: '' }));
                }}
                placeholder="Type your message..."
                rows={4}
                className={`w-full px-4 py-3 rounded-xl border ${
                  errors.text
                    ? 'border-red-300 focus:border-red-500'
                    : 'border-neutral-mid/20 focus:border-primary'
                } focus:outline-none focus:ring-2 focus:ring-primary/10 resize-none`}
              />
              {errors.text && <p className="mt-1.5 text-xs text-red-600">{errors.text}</p>}
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-neutral-dark mb-2">
                Template <span className="text-red-500">*</span>
              </label>
              {loadingTemplates ? (
                <p className="text-sm text-neutral-mid">Loading templates...</p>
              ) : templates.length === 0 ? (
                <p className="text-sm text-neutral-mid">No templates available</p>
              ) : (
                <select
                  value={templateName}
                  onChange={(e) => {
                    setTemplateName(e.target.value);
                    setErrors((prev: any) => ({ ...prev, templateName: '' }));
                  }}
                  className={`w-full px-4 py-3 rounded-xl border ${
                    errors.templateName
                      ? 'border-red-300 focus:border-red-500'
                      : 'border-neutral-mid/20 focus:border-primary'
                  } focus:outline-none focus:ring-2 focus:ring-primary/10`}
                >
                  <option value="">Select a template</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.name}>
                      {template.name} ({template.status})
                    </option>
                  ))}
                </select>
              )}
              {errors.templateName && <p className="mt-1.5 text-xs text-red-600">{errors.templateName}</p>}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-5 py-3 rounded-xl border border-neutral-mid/20 text-neutral-dark font-semibold hover:bg-neutral-mid/5 disabled:opacity-50 transition-all duration-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-5 py-3 rounded-xl bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold shadow-lg hover:shadow-xl disabled:opacity-50 transition-all duration-200"
            >
              {loading ? 'Sending...' : 'Send Message'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
