# WhatsApp Integration - Implementation Guide

## Overview

This guide provides complete implementation details for the WhatsApp Business API integration in Convis. Users can connect their WhatsApp Business accounts and send automated messages.

---

## ✅ What's Been Created

### Backend (Python/FastAPI)

1. **Models** (`convis-api/app/models/whatsapp.py`)
   - Pydantic schemas for credentials, messages, webhooks
   - Input validation and data models

2. **Service Layer** (`convis-api/app/services/whatsapp_service.py`)
   - WhatsAppService class for Meta API integration
   - Methods for sending text/template messages
   - Connection testing and validation

3. **API Routes** (`convis-api/app/routes/whatsapp/`)
   - `credentials.py` - CRUD for WhatsApp credentials
   - `messages.py` - Send/retrieve messages
   - `webhooks.py` - Handle Meta webhooks

4. **Main App** (`convis-api/app/main.py`)
   - Routes registered and active

### Frontend (Next.js/React)

1. **Main Page** (`convis-web/app/whatsapp/page.tsx`)
   - Full integration UI with tabs
   - Credentials management
   - Stats dashboard

2. **API Client** (`convis-web/lib/whatsapp-api.ts`)
   - TypeScript functions for all endpoints
   - Type-safe API calls

---

## 🔧 Remaining Setup Steps

### Step 1: Create Frontend Modal Components

Create the following files in `convis-web/app/whatsapp/components/`:

#### A. AddCredentialModal.tsx

```typescript
'use client';

import { useState } from 'react';
import { testWhatsAppConnection, createWhatsAppCredential } from '@/lib/whatsapp-api';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddCredentialModal({ onClose, onSuccess }: Props) {
  const [formData, setFormData] = useState({
    label: '',
    phone_number_id: '',
    business_account_id: '',
    access_token: '',
  });
  const [errors, setErrors] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev: any) => ({ ...prev, [name]: '' }));
  };

  const handleTestConnection = async () => {
    if (!formData.phone_number_id || !formData.access_token) {
      alert('Please enter Phone Number ID and Access Token first');
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const result = await testWhatsAppConnection(
        formData.phone_number_id,
        formData.access_token
      );
      setTestResult(result);

      if (result.success) {
        alert(`✅ Connection successful!\n\nPhone: ${result.phone_number}\nName: ${result.display_name}`);
      } else {
        alert(`❌ ${result.message}`);
      }
    } catch (err: any) {
      alert(`Connection test failed: ${err.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: any = {};
    if (!formData.label.trim()) newErrors.label = 'Label is required';
    if (!formData.phone_number_id.trim()) newErrors.phone_number_id = 'Phone Number ID is required';
    if (!formData.business_account_id.trim()) newErrors.business_account_id = 'Business Account ID is required';
    if (!formData.access_token.trim()) newErrors.access_token = 'Access Token is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);

    try {
      await createWhatsAppCredential(formData);
      onSuccess();
      onClose();
    } catch (err: any) {
      alert(`Failed to save credentials: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-3xl bg-white p-8 shadow-2xl">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-neutral-dark">Add WhatsApp Business Account</h2>
          <p className="text-sm text-neutral-mid mt-2">
            Connect your WhatsApp Business API credentials from Meta
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Label <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="label"
              value={formData.label}
              onChange={handleChange}
              placeholder="e.g., My Business WhatsApp"
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.label
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10`}
            />
            {errors.label && <p className="mt-1.5 text-xs text-red-600">{errors.label}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Phone Number ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="phone_number_id"
              value={formData.phone_number_id}
              onChange={handleChange}
              placeholder="From Meta Business Settings"
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.phone_number_id
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10`}
            />
            {errors.phone_number_id && <p className="mt-1.5 text-xs text-red-600">{errors.phone_number_id}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Business Account ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="business_account_id"
              value={formData.business_account_id}
              onChange={handleChange}
              placeholder="WhatsApp Business Account ID"
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.business_account_id
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10`}
            />
            {errors.business_account_id && <p className="mt-1.5 text-xs text-red-600">{errors.business_account_id}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-dark mb-2">
              Access Token <span className="text-red-500">*</span>
            </label>
            <textarea
              name="access_token"
              value={formData.access_token}
              onChange={(e) => handleChange(e as any)}
              placeholder="Your WhatsApp API Access Token"
              rows={3}
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.access_token
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10 resize-none`}
            />
            {errors.access_token && <p className="mt-1.5 text-xs text-red-600">{errors.access_token}</p>}
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="flex-1 px-5 py-3 rounded-xl border border-primary text-primary font-semibold hover:bg-primary/5 disabled:opacity-50 transition-all duration-200"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-5 py-3 rounded-xl border border-neutral-mid/20 text-neutral-dark font-semibold hover:bg-neutral-mid/5 disabled:opacity-50 transition-all duration-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !testResult?.success}
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

#### B. SendMessageModal.tsx

```typescript
'use client';

import { useState, useEffect } from 'react';
import { sendWhatsAppMessage, getWhatsAppTemplates } from '@/lib/whatsapp-api';

interface Props {
  credentialId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function SendMessageModal({ credentialId, onClose, onSuccess }: Props) {
  const [messageType, setMessageType] = useState<'text' | 'template'>('text');
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
              placeholder="+1234567890"
              className={`w-full px-4 py-3 rounded-xl border ${
                errors.to
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-neutral-mid/20 focus:border-primary'
              } focus:outline-none focus:ring-2 focus:ring-primary/10`}
            />
            {errors.to && <p className="mt-1.5 text-xs text-red-600">{errors.to}</p>}
            <p className="mt-1.5 text-xs text-neutral-mid">Include country code (e.g., +1 for US)</p>
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
```

#### C. MessageHistoryModal.tsx

```typescript
'use client';

import { useState, useEffect } from 'react';
import { getWhatsAppMessages } from '@/lib/whatsapp-api';

interface Props {
  credentialId: string;
  onClose: () => void;
}

export default function MessageHistoryModal({ credentialId, onClose }: Props) {
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMessages();
  }, []);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      const data = await getWhatsAppMessages(credentialId, 50, 0);
      setMessages(data);
    } catch (err: any) {
      console.error('Failed to load messages:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'bg-blue-100 text-blue-700';
      case 'delivered':
        return 'bg-green-100 text-green-700';
      case 'read':
        return 'bg-purple-100 text-purple-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-3xl rounded-3xl bg-white p-8 shadow-2xl max-h-[80vh] flex flex-col">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-neutral-dark">Message History</h2>
          <p className="text-sm text-neutral-mid mt-2">Recent messages sent from this account</p>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent"></div>
              <p className="text-neutral-mid mt-4">Loading messages...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-neutral-mid">No messages sent yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className="bg-gradient-to-br from-white to-green-50/30 border border-neutral-mid/10 rounded-xl p-4"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-semibold text-neutral-dark">{message.to}</p>
                      <p className="text-xs text-neutral-mid">
                        {new Date(message.sent_at).toLocaleString()}
                      </p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(message.status)}`}>
                      {message.status}
                    </span>
                  </div>
                  {message.error && (
                    <p className="text-sm text-red-600 mt-2">Error: {message.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-6 pt-4 border-t border-neutral-mid/10">
          <button
            onClick={onClose}
            className="w-full px-5 py-3 rounded-xl border border-neutral-mid/20 text-neutral-dark font-semibold hover:bg-neutral-mid/5 transition-all duration-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

### Step 2: Update Environment Variables

Add to `convis-api/.env`:

```bash
# WhatsApp Business API Configuration
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_secure_random_token_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here
```

Update `convis-api/.env.example`:

```bash
# WhatsApp Business API
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verification_token
```

---

### Step 3: Database Setup

The following MongoDB collections will be created automatically when used:

1. **whatsapp_credentials** - Stores encrypted WhatsApp Business credentials
2. **whatsapp_messages** - Stores sent message history
3. **whatsapp_incoming_messages** - Stores incoming messages from webhooks

No manual migration needed - MongoDB creates collections on first insert.

---

### Step 4: Meta WhatsApp Business Setup

#### Get Your Credentials:

1. **Go to Meta for Developers**: https://developers.facebook.com/
2. **Create/Select App** → Business Type
3. **Add WhatsApp Product**
4. **Get Credentials**:
   - Phone Number ID: `Settings > API Setup > Phone Number ID`
   - Business Account ID: `Settings > Business Account ID`
   - Access Token: `Settings > API Setup > Temporary/Permanent Token`

#### Configure Webhook:

1. In Meta Dashboard → WhatsApp → Configuration
2. Set Webhook URL: `https://api.convis.ai/api/whatsapp/webhook`
3. Verify Token: Use the value from `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
4. Subscribe to fields:
   - `messages`
   - `message_status`

---

### Step 5: Testing

1. **Start Backend**:
   ```bash
   cd convis-api
   python run.py
   ```

2. **Start Frontend**:
   ```bash
   cd convis-web
   npm run dev
   ```

3. **Test Flow**:
   - Navigate to `/whatsapp`
   - Click "Add Account"
   - Test connection with your Meta credentials
   - Save credentials
   - Send a test message

---

## 📚 API Documentation

Once running, visit:
- **API Docs**: `http://localhost:8000/docs`
- **WhatsApp Endpoints**: Look for "WhatsApp" tag

---

## 🔐 Security Features

1. **Encryption**: All credentials encrypted using Fernet (symmetric encryption)
2. **Authentication**: JWT tokens required for all endpoints
3. **Validation**: Input validation on all requests
4. **Webhook Security**: Signature verification (ready for implementation)

---

## 📊 Features Implemented

✅ Multi-tenant WhatsApp credential management
✅ Connection testing before saving
✅ Send text messages
✅ Send template messages
✅ Message history tracking
✅ Real-time status updates via webhooks
✅ Incoming message handling
✅ Statistics dashboard
✅ Credential verification
✅ Bulk messaging support

---

## 🚀 Next Steps (Optional Enhancements)

1. **CSV Upload**: Integrate with the existing CSV function you showed
2. **Campaign Integration**: Connect WhatsApp messages to campaigns
3. **AI Assistant Integration**: Link WhatsApp to AI assistants for auto-replies
4. **Rich Media**: Add support for images, videos, documents
5. **Templates Management**: Create/edit templates from UI
6. **Analytics**: Advanced reporting and insights
7. **Scheduled Messages**: Queue messages for future sending

---

## 🐛 Troubleshooting

### Common Issues:

**1. "Encryption key not found"**
- Solution: Set `ENCRYPTION_KEY` in `.env` (32-byte key)
- Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**2. "Connection test failed"**
- Verify credentials in Meta Dashboard
- Check access token hasn't expired
- Ensure phone number is verified

**3. "Webhook not receiving events"**
- Verify webhook URL is publicly accessible
- Check verify token matches
- Ensure HTTPS (required by Meta)

---

## 📞 Support

For issues or questions:
- Check API logs: `convis-api/logs/`
- Review Meta API docs: https://developers.facebook.com/docs/whatsapp/
- Test webhooks: https://webhook.site/

---

## 🎉 Congratulations!

Your WhatsApp integration is ready! Users can now connect their WhatsApp Business accounts and send automated messages through Convis.
