'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { NAV_ITEMS, NavigationItem } from '../components/Navigation';
import { TopBar } from '../components/TopBar';

type SupportedProvider = 'openai' | 'anthropic' | 'azure_openai' | 'google' | 'custom';

const DEFAULT_CALL_GREETING =
  "Greet the user with 'Hello there! I am an AI voice assistant that will help you with any questions you may have. Please ask me anything you want to know.'";

interface KnowledgeBaseFile {
  filename: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  file_path: string;
}

interface DatabaseConfig {
  enabled: boolean;
  type: string;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  table_name: string;
  search_columns: string[];
}

interface AIAssistant {
  id: string;
  user_id: string;
  name: string;
  system_message: string;
  voice: string;
  temperature: number;
  call_greeting: string;
  has_api_key: boolean;
  api_key_id?: string | null;
  api_key_label?: string | null;
  api_key_provider?: SupportedProvider | null;
  knowledge_base_files: KnowledgeBaseFile[];
  has_knowledge_base: boolean;
  database_config?: DatabaseConfig | null;
  created_at: string;
  updated_at: string;
}

interface AIAssistantListResponse {
  assistants: AIAssistant[];
  total: number;
}

interface AssistantTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  system_message: string;
  voice: string;
  temperature: number;
  color: string;
}

interface StoredApiKey {
  id: string;
  label: string;
  provider: SupportedProvider;
}

const PROVIDER_LABELS: Record<SupportedProvider, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  azure_openai: 'Azure OpenAI',
  google: 'Google Vertex',
  custom: 'Custom Provider',
};

interface VoiceOption {
  value: string;
  label: string;
  gender: 'Male' | 'Female' | 'Neutral';
  accent: string;
  description: string;
}

const getKnowledgeBaseFileKey = (file: KnowledgeBaseFile) =>
  file.file_path || `${file.filename}-${file.uploaded_at}`;

const dedupeKnowledgeBaseFiles = (files: KnowledgeBaseFile[]) => {
  const seen = new Set<string>();
  return files.filter((file) => {
    const key = getKnowledgeBaseFileKey(file);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};

const VOICE_OPTIONS: VoiceOption[] = [
  { value: 'alloy', label: 'Alloy', gender: 'Neutral', accent: 'American', description: 'Balanced and versatile' },
  { value: 'ash', label: 'Ash', gender: 'Male', accent: 'British', description: 'Clear and articulate' },
  { value: 'ballad', label: 'Ballad', gender: 'Male', accent: 'American', description: 'Smooth and calm' },
  { value: 'cedar', label: 'Cedar', gender: 'Male', accent: 'American', description: 'Warm and steady' },
  { value: 'coral', label: 'Coral', gender: 'Female', accent: 'American', description: 'Bright and friendly' },
  { value: 'echo', label: 'Echo', gender: 'Male', accent: 'American', description: 'Professional and clear' },
  { value: 'fable', label: 'Fable', gender: 'Female', accent: 'British', description: 'Expressive and engaging' },
  { value: 'marin', label: 'Marin', gender: 'Female', accent: 'Australian', description: 'Energetic and upbeat' },
  { value: 'nova', label: 'Nova', gender: 'Female', accent: 'American', description: 'Youthful and energetic' },
  { value: 'onyx', label: 'Onyx', gender: 'Male', accent: 'American', description: 'Deep and authoritative' },
  { value: 'sage', label: 'Sage', gender: 'Female', accent: 'American', description: 'Soft and reassuring' },
  { value: 'shimmer', label: 'Shimmer', gender: 'Female', accent: 'American', description: 'Cheerful and warm' },
  { value: 'verse', label: 'Verse', gender: 'Male', accent: 'American', description: 'Conversational and natural' },
];

const ASSISTANT_TEMPLATES: AssistantTemplate[] = [
  {
    id: 'customer-support',
    name: 'Customer Support Agent',
    description: 'Handle customer inquiries, provide support, and resolve issues professionally',
    icon: '💬',
    system_message: 'You are a professional and friendly customer support agent. Your goal is to help customers resolve their issues efficiently while maintaining a positive and empathetic tone. Always listen carefully to their concerns, provide clear solutions, and ensure customer satisfaction.',
    voice: 'alloy',
    temperature: 0.7,
    color: 'from-blue-500 to-blue-600',
  },
  {
    id: 'sales-assistant',
    name: 'Sales Assistant',
    description: 'Engage prospects, answer questions, and drive sales conversations',
    icon: '💼',
    system_message: 'You are a knowledgeable and persuasive sales assistant. Your role is to understand customer needs, present product benefits effectively, handle objections professionally, and guide prospects through the sales process. Be consultative, not pushy.',
    voice: 'nova',
    temperature: 0.8,
    color: 'from-green-500 to-green-600',
  },
  {
    id: 'appointment-scheduler',
    name: 'Appointment Scheduler',
    description: 'Book appointments, manage calendars, and send reminders',
    icon: '📅',
    system_message: 'You are an efficient appointment scheduling assistant. Help users book, reschedule, and manage appointments. Check availability, confirm details, send reminders, and ensure smooth scheduling. Be organized and detail-oriented.',
    voice: 'shimmer',
    temperature: 0.5,
    color: 'from-purple-500 to-purple-600',
  },
  {
    id: 'lead-qualifier',
    name: 'Lead Qualification Agent',
    description: 'Qualify leads by asking relevant questions and gathering information',
    icon: '🎯',
    system_message: 'You are a lead qualification specialist. Ask targeted questions to understand prospect needs, budget, timeline, and decision-making process. Gather essential information to determine if the lead is qualified. Be professional and conversational.',
    voice: 'onyx',
    temperature: 0.6,
    color: 'from-orange-500 to-orange-600',
  },
  {
    id: 'receptionist',
    name: 'Virtual Receptionist',
    description: 'Greet callers, route calls, and provide basic information',
    icon: '📞',
    system_message: 'You are a professional virtual receptionist. Greet callers warmly, understand their needs, provide information about the company, and route calls appropriately. Handle inquiries efficiently while maintaining a friendly demeanor.',
    voice: 'echo',
    temperature: 0.6,
    color: 'from-pink-500 to-pink-600',
  },
  {
    id: 'feedback-collector',
    name: 'Feedback Collection Agent',
    description: 'Gather customer feedback and conduct satisfaction surveys',
    icon: '⭐',
    system_message: 'You are a feedback collection specialist. Conduct surveys, gather customer opinions, and collect testimonials. Ask thoughtful questions, encourage honest feedback, and make the process enjoyable. Be appreciative and non-intrusive.',
    voice: 'fable',
    temperature: 0.7,
    color: 'from-yellow-500 to-yellow-600',
  },
];

export default function AIAgentPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [assistants, setAssistants] = useState<AIAssistant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [activeNav, setActiveNav] = useState('AI Agent');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [modalStep, setModalStep] = useState<'template' | 'form'>('template');
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingAssistantId, setEditingAssistantId] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deletingAssistant, setDeletingAssistant] = useState<AIAssistant | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isViewDetailsOpen, setIsViewDetailsOpen] = useState(false);
  const [viewingAssistant, setViewingAssistant] = useState<AIAssistant | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [knowledgeBaseFiles, setKnowledgeBaseFiles] = useState<KnowledgeBaseFile[]>([]);
  const [isDocumentPreviewOpen, setIsDocumentPreviewOpen] = useState(false);
  const [previewingDocument, setPreviewingDocument] = useState<KnowledgeBaseFile | null>(null);
  const [documentContent, setDocumentContent] = useState<string>('');
  const [loadingDocumentContent, setLoadingDocumentContent] = useState(false);
  const [apiKeys, setApiKeys] = useState<StoredApiKey[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);
  const [keysError, setKeysError] = useState<string | null>(null);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    system_message: '',
    voice: 'alloy',
    temperature: 0.5,
    api_key_id: '',
    call_greeting: DEFAULT_CALL_GREETING,
  });
  const [databaseConfig, setDatabaseConfig] = useState({
    enabled: false,
    type: 'postgresql',
    host: '',
    port: '5432',
    database: '',
    username: '',
    password: '',
    table_name: '',
    search_columns: [] as string[],
  });
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
      const resolvedUserId = userData.clientId || userData._id || userData.id;
      if (resolvedUserId) {
        fetchAssistants(resolvedUserId, token);
        fetchApiKeyOptions(resolvedUserId, token);
      }
    }

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }
  }, [router]);

  useEffect(() => {
    if (isEditMode || formData.api_key_id || apiKeys.length === 0) {
      return;
    }

    const preferredKey = apiKeys.find((key) => key.provider === 'openai') || apiKeys[0];
    if (preferredKey) {
      setFormData((prev) => ({
        ...prev,
        api_key_id: preferredKey.id,
      }));
    }
  }, [apiKeys, isEditMode, formData.api_key_id]);

  const fetchApiKeyOptions = async (userId: string, token: string) => {
    try {
      setIsLoadingKeys(true);
      setKeysError(null);
      const response = await fetch(`${API_URL}/api/ai-keys/user/${userId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to retrieve saved API keys');
      }

      setApiKeys(Array.isArray(data.keys) ? data.keys.map((key: any) => ({
        id: key.id,
        label: key.label,
        provider: key.provider,
      })) : []);
    } catch (err) {
      setKeysError(err instanceof Error ? err.message : 'Failed to load saved API keys.');
      setApiKeys([]);
    } finally {
      setIsLoadingKeys(false);
    }
  };

  const fetchAssistants = async (userId: string, token: string) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/ai-assistants/user/${userId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch AI assistants');
      }

      const data: AIAssistantListResponse = await response.json();
      setAssistants(data.assistants || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAssistant = async () => {
    const token = localStorage.getItem('token');
    const userId = user?.clientId || user?._id || user?.id;

    if (!token || !userId) {
      setCreateError('User not authenticated');
      return;
    }

    if (!formData.name.trim()) {
      setCreateError('Assistant name is required');
      return;
    }

    if (!formData.system_message.trim()) {
      setCreateError('System message is required');
      return;
    }

    if (!formData.api_key_id) {
      setCreateError('Select an API key from settings to continue');
      return;
    }

    try {
      setIsCreating(true);
      setCreateError(null);

      if (isEditMode && editingAssistantId) {
        // Update existing assistant
        const response = await fetch(`${API_URL}/api/ai-assistants/${editingAssistantId}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: formData.name,
            system_message: formData.system_message,
            voice: formData.voice,
            temperature: formData.temperature,
            api_key_id: formData.api_key_id,
            call_greeting: formData.call_greeting,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to update assistant');
        }

        // Save database configuration if enabled
        if (databaseConfig.enabled) {
          const dbResponse = await fetch(
            `${API_URL}/api/ai-assistants/database/${editingAssistantId}/save-config`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(databaseConfig),
            }
          );

          if (!dbResponse.ok) {
            console.error('Failed to save database configuration');
          }
        }
      } else {
        // Create new assistant
        const response = await fetch(`${API_URL}/api/ai-assistants`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            name: formData.name,
            system_message: formData.system_message,
            voice: formData.voice,
            temperature: formData.temperature,
            api_key_id: formData.api_key_id,
            call_greeting: formData.call_greeting,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create assistant');
        }
      }

      // Reset form and close modal
      setFormData({
        name: '',
        system_message: '',
        voice: 'alloy',
        temperature: 0.8,
        api_key_id: '',
        call_greeting: DEFAULT_CALL_GREETING,
      });
      setIsCreateModalOpen(false);
      setIsEditMode(false);
      setEditingAssistantId(null);

      // Refresh the assistants list
      await fetchAssistants(userId, token);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : isEditMode ? 'Failed to update assistant' : 'Failed to create assistant');
    } finally {
      setIsCreating(false);
    }
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'temperature' ? parseFloat(value) : value,
    }));
  };

  const handleVoiceDemo = async (voiceId: string) => {
    // Stop currently playing audio if any
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      URL.revokeObjectURL(audioElement.src);
    }

    // If clicking the same voice that's playing, stop it
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
      setAudioElement(null);
      return;
    }

    try {
      const resolvedUserId = user?.clientId || user?._id || user?.id;
      if (!resolvedUserId) {
        alert('We could not resolve your user information. Please refresh the page and try again.');
        return;
      }

      const selectedKey = apiKeys.find((key) => key.id === formData.api_key_id);
      if (!selectedKey) {
        alert('Please select an API key before previewing a voice.');
        return;
      }

      if (selectedKey.provider !== 'openai') {
        alert('Voice demos currently require an OpenAI API key. Please choose an OpenAI key from the list.');
        return;
      }

      const token = localStorage.getItem('token');
      setPlayingVoice(voiceId);

      // Sample text for demo
      const demoText = "Hello! This is a sample of my voice. I'm here to assist you with your conversations.";

      // Call backend API to generate audio
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/ai-assistants/voice-demo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
          voice: voiceId,
          text: demoText,
          user_id: resolvedUserId,
          api_key_id: selectedKey.id,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate voice sample');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setPlayingVoice(null);
        setAudioElement(null);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = (e) => {
        console.error('Audio playback error:', e);
        setPlayingVoice(null);
        setAudioElement(null);
        URL.revokeObjectURL(audioUrl);
      };

      setAudioElement(audio);
      await audio.play();
    } catch (error) {
      console.error('Error playing voice demo:', error);
      setPlayingVoice(null);
      setAudioElement(null);
      const message = error instanceof Error ? error.message : 'Failed to play voice demo. Please check your API configuration.';
      alert(message);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Validate file types and sizes
    const allowedTypes = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();

      if (!allowedTypes.includes(fileExtension)) {
        setUploadError(`Invalid file type for ${file.name}. Allowed: PDF, DOCX, XLSX, TXT`);
        return;
      }

      if (file.size > maxSize) {
        setUploadError(`File ${file.name} is too large. Maximum size is 50MB`);
        return;
      }
    }

    if (!isEditMode || !editingAssistantId) {
      setUploadError('Please save the assistant first before uploading files');
      return;
    }

    setUploadingFile(true);
    setUploadError(null);

    try {
      // Upload files sequentially to avoid overwhelming the server
      const uploadedFiles = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(
          `${API_URL}/api/ai-assistants/knowledge-base/${editingAssistantId}/upload`,
          {
            method: 'POST',
            body: formData,
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`Failed to upload ${file.name}: ${errorData.detail || 'Unknown error'}`);
        }

        const data = await response.json();
        uploadedFiles.push(data.file);
      }

      // Add all new files to the list
      setKnowledgeBaseFiles(prev => dedupeKnowledgeBaseFiles([...prev, ...uploadedFiles]));

      // Reset file input
      e.target.value = '';

      // Refresh assistants list to get updated data
      if (user) {
        const token = localStorage.getItem('token');
        const resolvedUserId = user?.clientId || user?._id || user?.id;
        if (token && resolvedUserId) {
          await fetchAssistants(resolvedUserId, token);
        }
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload files');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleTestConnection = async () => {
    if (!editingAssistantId) return;

    setTestingConnection(true);
    setConnectionStatus(null);

    try {
      const response = await fetch(
        `${API_URL}/api/ai-assistants/database/${editingAssistantId}/test-connection`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(databaseConfig),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to test connection');
      }

      setConnectionStatus('Success! Database connection established.');
    } catch (err: any) {
      setConnectionStatus(`Connection failed: ${err.message}`);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleDeleteFile = async (filename: string) => {
    if (!isEditMode || !editingAssistantId) return;

    if (!confirm(`Are you sure you want to delete ${filename}?`)) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/ai-assistants/knowledge-base/${editingAssistantId}/files/${encodeURIComponent(filename)}`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete file');
      }

      // Remove file from list
      setKnowledgeBaseFiles(prev => prev.filter(f => f.filename !== filename));

      // Refresh assistants list
      if (user) {
        const token = localStorage.getItem('token');
        const resolvedUserId = user?.clientId || user?._id || user?.id;
        if (token && resolvedUserId) {
          await fetchAssistants(resolvedUserId, token);
        }
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to delete file');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const displayProviderLabel = (provider?: SupportedProvider | null) => {
    if (!provider) return 'Unknown Provider';
    return PROVIDER_LABELS[provider] || provider;
  };

  const handleViewDocument = async (assistantId: string, file: KnowledgeBaseFile) => {
    setPreviewingDocument(file);
    setIsDocumentPreviewOpen(true);
    setLoadingDocumentContent(true);
    setDocumentContent('');

    try {
      const response = await fetch(
        `${API_URL}/api/ai-assistants/knowledge-base/${assistantId}/preview/${encodeURIComponent(file.filename)}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch document content');
      }

      const data = await response.json();
      setDocumentContent(data.extracted_text || 'No content available');
    } catch (err: any) {
      setDocumentContent('Error loading document content: ' + (err.message || 'Unknown error'));
    } finally {
      setLoadingDocumentContent(false);
    }
  };

  const closeDocumentPreview = () => {
    setIsDocumentPreviewOpen(false);
    setPreviewingDocument(null);
    setDocumentContent('');
  };

  const openCreateModal = () => {
    setIsCreateModalOpen(true);
    setModalStep('template');
    setCreateError(null);
    const token = localStorage.getItem('token');
    const resolvedUserId = user?.clientId || user?._id || user?.id;
    if (token && resolvedUserId) {
      fetchApiKeyOptions(resolvedUserId, token);
    }
  };

  const closeCreateModal = () => {
    setIsCreateModalOpen(false);
    setModalStep('template');
    setCreateError(null);
    setUploadError(null);
    setIsEditMode(false);
    setEditingAssistantId(null);
    setKnowledgeBaseFiles([]);
    setFormData({
      name: '',
      system_message: '',
      voice: 'alloy',
      temperature: 0.8,
      api_key_id: '',
      call_greeting: DEFAULT_CALL_GREETING,
    });
  };

  const openEditModal = async (assistant: AIAssistant) => {
    setFormData({
      name: assistant.name,
      system_message: assistant.system_message,
      voice: assistant.voice,
      temperature: assistant.temperature,
      api_key_id: assistant.api_key_id || '',
      call_greeting: assistant.call_greeting || DEFAULT_CALL_GREETING,
    });
    setKnowledgeBaseFiles(dedupeKnowledgeBaseFiles(assistant.knowledge_base_files || []));

    // Load database configuration if available
    if (assistant.database_config) {
      setDatabaseConfig(assistant.database_config);
    } else {
      // Reset to default if no config exists
      setDatabaseConfig({
        enabled: false,
        type: 'postgresql',
        host: '',
        port: '5432',
        database: '',
        username: '',
        password: '',
        table_name: '',
        search_columns: [],
      });
    }

    setIsEditMode(true);
    setEditingAssistantId(assistant.id);
    setModalStep('form');
    setIsCreateModalOpen(true);
    setCreateError(null);
    setUploadError(null);
    setConnectionStatus(null);
    const token = localStorage.getItem('token');
    const resolvedUserId = user?.clientId || user?._id || user?.id;
    if (token && resolvedUserId) {
      fetchApiKeyOptions(resolvedUserId, token);
    }
  };

  const selectTemplate = (template: AssistantTemplate) => {
    setFormData({
      name: template.name,
      system_message: template.system_message,
      voice: template.voice,
      temperature: template.temperature,
      api_key_id: '',
      call_greeting: DEFAULT_CALL_GREETING,
    });
    setModalStep('form');
  };

  const startFromScratch = () => {
    setFormData({
      name: '',
      system_message: '',
      voice: 'alloy',
      temperature: 0.8,
      api_key_id: '',
      call_greeting: DEFAULT_CALL_GREETING,
    });
    setModalStep('form');
  };

  const goBackToTemplates = () => {
    if (isEditMode) {
      // If in edit mode, close modal instead of going back to templates
      closeCreateModal();
    } else {
      setModalStep('template');
    }
  };

  const openDeleteModal = (assistant: AIAssistant) => {
    setDeletingAssistant(assistant);
    setIsDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    setDeletingAssistant(null);
    setIsDeleteModalOpen(false);
  };

  const handleDeleteAssistant = async () => {
    if (!deletingAssistant) return;

    const token = localStorage.getItem('token');
    const userId = user?.clientId || user?._id || user?.id;

    if (!token || !userId) {
      return;
    }

    try {
      setIsDeleting(true);

      const response = await fetch(`${API_URL}/api/ai-assistants/${deletingAssistant.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete assistant');
      }

      // Close modal and refresh list
      closeDeleteModal();
      await fetchAssistants(userId, token);
    } catch (err) {
      console.error('Error deleting assistant:', err);
      // You could add error state here if needed
    } finally {
      setIsDeleting(false);
    }
  };

  const openViewDetails = (assistant: AIAssistant) => {
    setViewingAssistant(assistant);
    setIsViewDetailsOpen(true);
  };

  const closeViewDetails = () => {
    setViewingAssistant(null);
    setIsViewDetailsOpen(false);
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
    router.push(navItem.href);
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
        <TopBar
          isDarkMode={isDarkMode}
          toggleTheme={toggleTheme}
          onLogout={handleLogout}
          userInitial={userInitial}
          userLabel={userGreeting}
          onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)}
        />

        {/* Page Content */}
        <main className="p-6">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                AI Assistants
              </h1>
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                Manage your AI voice assistants and their configurations
              </p>
            </div>
            <button
              onClick={openCreateModal}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary to-primary/90 text-white rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 transition-all duration-200"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create New Assistant
            </button>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'} border rounded-xl p-6`}>
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <h3 className={`font-semibold ${isDarkMode ? 'text-red-400' : 'text-red-800'} mb-1`}>Error Loading Assistants</h3>
                  <p className={`text-sm ${isDarkMode ? 'text-red-300' : 'text-red-700'}`}>{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && assistants.length === 0 && (
            <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-12 text-center shadow-sm`}>
              <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-10 h-10 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <h3 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                No AI Assistants Yet
              </h3>
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mb-6`}>
                Get started by creating your first AI voice assistant
              </p>
              <button
                onClick={openCreateModal}
                className="px-6 py-3 bg-gradient-to-r from-primary to-primary/90 text-white rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 transition-all duration-200"
              >
                Create Your First Assistant
              </button>
            </div>
          )}

          {/* Assistants Grid */}
          {!isLoading && !error && assistants.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {assistants.map((assistant) => (
                <div
                  key={assistant.id}
                  className={`${isDarkMode ? 'bg-gray-800 hover:bg-gray-750' : 'bg-white hover:shadow-lg'} rounded-2xl p-6 shadow-sm transition-all duration-200 cursor-pointer border ${isDarkMode ? 'border-gray-700' : 'border-transparent'}`}
                >
                  {/* Assistant Icon */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                    <button
                      onClick={() => openDeleteModal(assistant)}
                      className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-red-900/20 text-gray-400 hover:text-red-400' : 'hover:bg-red-50 text-neutral-mid hover:text-red-500'} transition-colors`}
                      title="Delete Assistant"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>

                  {/* Assistant Info */}
                  <h3 className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    {assistant.name}
                  </h3>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mb-3 line-clamp-2`}>
                    {assistant.system_message}
                  </p>

                  {/* API Key Status Badge */}
                  <div className="mb-3">
                    {assistant.has_api_key ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-500/10 text-green-500 border border-green-500/20">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        API Key Configured
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/20">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        No API Key
                      </span>
                    )}
                    {assistant.api_key_label && (
                      <p className={`mt-2 text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Using: <span className="font-semibold text-primary">{assistant.api_key_label}</span>
                        {assistant.api_key_provider ? ` • ${displayProviderLabel(assistant.api_key_provider)}` : ''}
                      </p>
                    )}
                    {assistant.has_knowledge_base && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        {assistant.knowledge_base_files?.length || 0} {assistant.knowledge_base_files?.length === 1 ? 'Document' : 'Documents'}
                      </span>
                    )}
                  </div>

                  {/* Assistant Details */}
                  <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1">
                      <svg className={`w-4 h-4 ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.536a5 5 0 001.414 1.06m2.828-9.9a9 9 0 012.828 0" />
                      </svg>
                      <span className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>{assistant.voice}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <svg className={`w-4 h-4 ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <span className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Temp: {assistant.temperature}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 mt-4 pt-4 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}">
                    <button
                      onClick={() => openEditModal(assistant)}
                      className="flex-1 px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm font-semibold hover:bg-primary/20 transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => openViewDetails(assistant)}
                      className={`flex-1 px-4 py-2 ${isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-neutral-light text-neutral-dark'} rounded-lg text-sm font-semibold hover:opacity-80 transition-opacity`}
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stats Section */}
          {!isLoading && !error && assistants.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl p-6 shadow-sm`}>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <div>
                    <p className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      {assistants.length}
                    </p>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                      Total Assistants
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        ></div>
      )}

      {/* Create Assistant Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl ${modalStep === 'template' ? 'max-w-5xl' : 'max-w-2xl'} w-full max-h-[90vh] overflow-y-auto shadow-2xl`}>
            {/* Modal Header */}
            <div className={`flex items-center justify-between p-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <div className="flex items-center gap-3">
                {modalStep === 'form' && (
                  <button
                    onClick={goBackToTemplates}
                    className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
                  >
                    <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                )}
                <div>
                  <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    {isEditMode
                      ? 'Edit AI Assistant'
                      : (modalStep === 'template' ? 'Choose a Template' : 'Configure AI Assistant')}
                  </h2>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>
                    {isEditMode
                      ? 'Update your AI voice assistant settings'
                      : (modalStep === 'template'
                        ? 'Select a pre-configured template or start from scratch'
                        : 'Customize your AI voice assistant settings')}
                  </p>
                </div>
              </div>
              <button
                onClick={closeCreateModal}
                className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
              >
                <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Template Selection Step */}
            {modalStep === 'template' && (
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {ASSISTANT_TEMPLATES.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => selectTemplate(template)}
                      className={`text-left p-6 rounded-xl border-2 ${isDarkMode ? 'border-gray-700 hover:border-primary bg-gray-750' : 'border-neutral-mid/20 hover:border-primary bg-white'} hover:shadow-lg transition-all duration-200 group`}
                    >
                      <div className={`w-14 h-14 bg-gradient-to-br ${template.color} rounded-xl flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition-transform`}>
                        {template.icon}
                      </div>
                      <h3 className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                        {template.name}
                      </h3>
                      <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} line-clamp-2`}>
                        {template.description}
                      </p>
                    </button>
                  ))}
                </div>

                {/* Start from Scratch Option */}
                <div className={`border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} pt-6`}>
                  <button
                    onClick={startFromScratch}
                    className={`w-full p-6 rounded-xl border-2 border-dashed ${isDarkMode ? 'border-gray-600 hover:border-primary bg-gray-750' : 'border-neutral-mid/30 hover:border-primary bg-neutral-light/30'} hover:shadow-lg transition-all duration-200 group`}
                  >
                    <div className="flex items-center justify-center gap-4">
                      <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${isDarkMode ? 'bg-gray-700 group-hover:bg-primary/20' : 'bg-white group-hover:bg-primary/10'} transition-colors`}>
                        <svg className={`w-8 h-8 ${isDarkMode ? 'text-gray-400 group-hover:text-primary' : 'text-neutral-mid group-hover:text-primary'} transition-colors`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </div>
                      <div className="text-left">
                        <h3 className={`font-bold text-lg ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                          Start from Scratch
                        </h3>
                        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                          Create a custom AI assistant with your own configuration
                        </p>
                      </div>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {/* Form Step - Configuration */}
            {modalStep === 'form' && (
              <div className="p-6 space-y-6">
                {createError && (
                <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'} border rounded-xl p-4`}>
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <p className={`text-sm ${isDarkMode ? 'text-red-400' : 'text-red-700'}`}>{createError}</p>
                  </div>
                </div>
              )}

              {/* Assistant Name */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  Assistant Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  placeholder="e.g., Customer Support Agent"
                  className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-neutral-mid/20 text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                />
              </div>

              {/* Call Greeting */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  Call Greeting
                </label>
                <textarea
                  name="call_greeting"
                  value={formData.call_greeting}
                  onChange={handleFormChange}
                  placeholder="Opening message that plays when the call connects..."
                  rows={3}
                  className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-neutral-mid/20 text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none`}
                />
                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-2`}>
                  The caller hears this before the conversation begins. Mention disclaimers or technology disclosures here.
                </p>
              </div>

              {/* System Message */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  Agent persona and prompt <span className="text-red-500">*</span>
                </label>
                <textarea
                  name="system_message"
                  value={formData.system_message}
                  onChange={handleFormChange}
                  placeholder="Describe the assistant's role and behavior..."
                  rows={5}
                  className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-neutral-mid/20 text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none`}
                />
                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-2`}>
                  This message defines how the AI assistant will behave and respond to users.
                </p>
              </div>

              {/* Stored API Keys */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  LLM provider <span className="text-red-500">*</span>
                </label>
                <div className={`rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-800/60' : 'border-neutral-mid/20 bg-neutral-light/40'} p-4`}> 
                  {isLoadingKeys ? (
                    <div className="flex items-center justify-center py-4">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                    </div>
                  ) : apiKeys.length > 0 ? (
                    <div className="space-y-3">
                      <select
                        name="api_key_id"
                        value={formData.api_key_id}
                        onChange={handleFormChange}
                        className={`w-full px-4 py-3 rounded-xl border ${isDarkMode ? 'bg-gray-900 border-gray-700 text-white' : 'bg-white border-neutral-mid/20 text-neutral-dark'} focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all cursor-pointer`}
                      >
                        <option value="" disabled={apiKeys.length > 0}>
                          {apiKeys.length === 0 ? 'No API keys available' : 'Select an API key'}
                        </option>
                        {apiKeys.map((key) => (
                          <option key={key.id} value={key.id}>
                            {key.label} • {displayProviderLabel(key.provider)}
                          </option>
                        ))}
                      </select>
                      <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Keys are managed in your Settings. Assigning a key here links it permanently until you change it.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreateModalOpen(false);
                          router.push('/settings');
                        }}
                        className={`text-xs font-medium mt-1 inline-flex items-center gap-1 ${isDarkMode ? 'text-primary hover:text-primary/80' : 'text-primary hover:text-primary/80'}`}
                      >
                        Manage keys in Settings
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3 text-sm">
                      <p className={isDarkMode ? 'text-gray-300' : 'text-neutral-mid'}>
                        No API keys saved yet. Add your provider credentials in the Settings → AI API Keys tab before creating assistants.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreateModalOpen(false);
                          router.push('/settings');
                        }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-primary/80 text-white text-sm font-semibold shadow-sm hover:shadow-md transition-all"
                      >
                        Go to Settings
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
                {keysError && (
                  <p className={`text-xs mt-2 ${isDarkMode ? 'text-red-300' : 'text-red-600'}`}>
                    {keysError}
                  </p>
                )}
              </div>

              {/* Voice Selection */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-3`}>
                  Agent voice selection
                </label>
                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mb-4`}>
                  Click on a voice to select it, and use the play button to hear a demo
                </p>
                <div className={`rounded-xl border ${isDarkMode ? 'border-gray-600 bg-gray-700/30' : 'border-neutral-mid/20 bg-white'} max-h-[400px] overflow-y-auto`}>
                  {VOICE_OPTIONS.map((voice, index) => (
                    <div
                      key={voice.value}
                      className={`flex items-center justify-between p-4 cursor-pointer transition-all ${
                        index !== VOICE_OPTIONS.length - 1 ? (isDarkMode ? 'border-b border-gray-600' : 'border-b border-neutral-mid/10') : ''
                      } ${
                        formData.voice === voice.value
                          ? isDarkMode
                            ? 'bg-primary/20 hover:bg-primary/25'
                            : 'bg-primary/10 hover:bg-primary/15'
                          : isDarkMode
                            ? 'hover:bg-gray-700/50'
                            : 'hover:bg-neutral-mid/5'
                      }`}
                      onClick={() => setFormData(prev => ({ ...prev, voice: voice.value }))}
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                          formData.voice === voice.value
                            ? 'bg-primary text-white'
                            : isDarkMode
                              ? 'bg-gray-600 text-gray-200'
                              : 'bg-neutral-mid/10 text-neutral-dark'
                        }`}>
                          {voice.gender === 'Male' ? '👨' : voice.gender === 'Female' ? '👩' : '🧑'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                              {voice.label}
                            </h4>
                            {formData.voice === voice.value && (
                              <svg className="w-4 h-4 text-primary flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                              {voice.gender}
                            </span>
                            <span className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid/60'}`}>•</span>
                            <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                              {voice.accent} Accent
                            </span>
                          </div>
                          <p className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid/80'}`}>
                            {voice.description}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleVoiceDemo(voice.value);
                        }}
                        disabled={playingVoice !== null && playingVoice !== voice.value}
                        className={`flex-shrink-0 p-2.5 rounded-full transition-all ${
                          playingVoice === voice.value
                            ? 'bg-primary text-white shadow-lg scale-110'
                            : isDarkMode
                              ? 'bg-gray-600 text-gray-200 hover:bg-gray-500 disabled:opacity-30 disabled:cursor-not-allowed'
                              : 'bg-neutral-mid/10 text-neutral-dark hover:bg-neutral-mid/20 disabled:opacity-30 disabled:cursor-not-allowed'
                        }`}
                        title={playingVoice === voice.value ? 'Stop' : 'Play demo'}
                      >
                        {playingVoice === voice.value ? (
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                          </svg>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Temperature */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  Temperature: {formData.temperature}
                </label>
                <input
                  type="range"
                  name="temperature"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.temperature}
                  onChange={handleFormChange}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                />
                <div className="flex justify-between text-xs mt-2">
                  <span className={isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}>More Focused (0)</span>
                  <span className={isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}>More Creative (1)</span>
                </div>
                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-2`}>
                  Controls randomness. Lower values make responses more focused, higher values more creative.
                </p>
              </div>

              {/* Knowledge Base */}
              {isEditMode && (
                <div className={`rounded-xl border ${isDarkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200'} p-6`}>
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    <div>
                      <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                        Knowledge Base
                      </h3>
                      <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Upload documents for the AI to reference during conversations
                      </p>
                    </div>
                  </div>

                  {uploadError && (
                    <div className={`${isDarkMode ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'} border rounded-xl p-3 mb-4`}>
                      <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className={`text-sm ${isDarkMode ? 'text-red-400' : 'text-red-600'}`}>{uploadError}</p>
                      </div>
                    </div>
                  )}

                  {/* File Upload */}
                  <div className="mb-4">
                    <label className={`flex items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                      uploadingFile
                        ? 'opacity-50 cursor-not-allowed'
                        : isDarkMode
                          ? 'border-gray-600 hover:border-primary hover:bg-gray-700/50'
                          : 'border-neutral-mid/30 hover:border-primary hover:bg-white'
                    }`}>
                      <div className="text-center">
                        {uploadingFile ? (
                          <>
                            <svg className="animate-spin h-8 w-8 mx-auto mb-2 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>Uploading...</p>
                          </>
                        ) : (
                          <>
                            <svg className="w-8 h-8 mx-auto mb-2 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <p className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-1`}>
                              Click to upload or drag and drop
                            </p>
                            <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                              PDF, DOCX, XLSX, TXT (max 50MB) - Multiple files supported
                            </p>
                          </>
                        )}
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.docx,.doc,.xlsx,.xls,.txt"
                        onChange={handleFileUpload}
                        disabled={uploadingFile}
                        multiple
                      />
                    </label>
                  </div>

                  {/* Uploaded Files List */}
                  {knowledgeBaseFiles.length > 0 && (
                    <div className="space-y-2">
                      <p className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                        Uploaded Files ({knowledgeBaseFiles.length})
                      </p>
                      {knowledgeBaseFiles.map((file) => (
                        <div
                          key={getKnowledgeBaseFileKey(file)}
                          className={`flex items-center justify-between p-3 rounded-lg ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-neutral-mid/10'}`}
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                              file.file_type === 'pdf'
                                ? 'bg-red-100 text-red-600'
                                : file.file_type === 'docx' || file.file_type === 'doc'
                                  ? 'bg-blue-100 text-blue-600'
                                  : file.file_type === 'xlsx' || file.file_type === 'xls'
                                    ? 'bg-green-100 text-green-600'
                                    : 'bg-gray-100 text-gray-600'
                            }`}>
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} truncate`}>
                                {file.filename}
                              </p>
                              <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                                {formatFileSize(file.file_size)} • {file.file_type.toUpperCase()}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteFile(file.filename)}
                            className={`ml-2 p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700 text-gray-400 hover:text-red-400' : 'hover:bg-red-50 text-neutral-mid hover:text-red-600'} transition-colors flex-shrink-0`}
                            title="Delete file"
                          >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {knowledgeBaseFiles.length === 0 && (
                    <p className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-neutral-mid'} text-center py-4`}>
                      No documents uploaded yet. The AI will use general knowledge.
                    </p>
                  )}
                </div>
              )}

              {!isEditMode && (
                <div className={`rounded-xl border ${isDarkMode ? 'bg-blue-900/20 border-blue-800' : 'bg-blue-50 border-blue-200'} p-4`}>
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className={`text-sm ${isDarkMode ? 'text-blue-400' : 'text-blue-700'}`}>
                      Knowledge Base files can be uploaded after creating the assistant
                    </p>
                  </div>
                </div>
              )}

              {/* Database Integration */}
              {isEditMode && (
                <div className={`rounded-xl border ${isDarkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gradient-to-br from-green-50 to-emerald-50 border-green-200'} p-6`}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                      </svg>
                      <div>
                        <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                          Database Integration
                        </h3>
                        <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                          Connect to your database to query user information in real-time
                        </p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={databaseConfig.enabled}
                        onChange={(e) => setDatabaseConfig({...databaseConfig, enabled: e.target.checked})}
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 dark:peer-focus:ring-green-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-green-600"></div>
                    </label>
                  </div>

                  {databaseConfig.enabled && (
                    <div className="space-y-4">
                      {connectionStatus && (
                        <div className={`${connectionStatus.includes('Success') ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} border rounded-xl p-3`}>
                          <p className={`text-sm ${connectionStatus.includes('Success') ? 'text-green-700' : 'text-red-700'}`}>
                            {connectionStatus}
                          </p>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Database Type
                          </label>
                          <select
                            value={databaseConfig.type}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, type: e.target.value, port: e.target.value === 'postgresql' ? '5432' : e.target.value === 'mysql' ? '3306' : '27017'})}
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          >
                            <option value="postgresql">PostgreSQL</option>
                            <option value="mysql">MySQL</option>
                            <option value="mongodb">MongoDB</option>
                          </select>
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Host
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.host}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, host: e.target.value})}
                            placeholder="localhost or IP address"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Port
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.port}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, port: e.target.value})}
                            placeholder="5432"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Database Name
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.database}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, database: e.target.value})}
                            placeholder="database_name"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Username
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.username}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, username: e.target.value})}
                            placeholder="db_username"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Password
                          </label>
                          <input
                            type="password"
                            value={databaseConfig.password}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, password: e.target.value})}
                            placeholder="••••••••"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Table Name
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.table_name}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, table_name: e.target.value})}
                            placeholder="users, customers, etc."
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>

                        <div>
                          <label className={`block text-sm font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            Search Columns (comma-separated)
                          </label>
                          <input
                            type="text"
                            value={databaseConfig.search_columns.join(', ')}
                            onChange={(e) => setDatabaseConfig({...databaseConfig, search_columns: e.target.value.split(',').map(col => col.trim()).filter(col => col)})}
                            placeholder="name, email, phone, policy_number"
                            className={`w-full px-4 py-3 rounded-xl ${isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-neutral-mid/30 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary transition-all`}
                          />
                        </div>
                      </div>

                      <button
                        onClick={handleTestConnection}
                        disabled={testingConnection}
                        className={`w-full px-4 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-green-600 hover:bg-green-700' : 'bg-green-600 hover:bg-green-700'} text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2`}
                      >
                        {testingConnection ? (
                          <>
                            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Testing Connection...
                          </>
                        ) : (
                          <>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Test Database Connection
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Modal Footer */}
              <div className={`flex items-center justify-end gap-3 p-6 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
                <button
                  onClick={closeCreateModal}
                  disabled={isCreating}
                  className={`px-6 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateAssistant}
                  disabled={isCreating || isLoadingKeys || !formData.api_key_id || apiKeys.length === 0}
                  className="px-6 py-3 bg-gradient-to-r from-primary to-primary/90 text-white rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isCreating ? (
                    <>
                      <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {isEditMode ? 'Updating...' : 'Creating...'}
                    </>
                  ) : (
                    isEditMode ? 'Update Assistant' : 'Create Assistant'
                  )}
                </button>
              </div>
            </div>
          )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && deletingAssistant && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-md w-full shadow-2xl`}>
            {/* Modal Header */}
            <div className={`p-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                    Delete AI Assistant
                  </h2>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>
                    This action cannot be undone
                  </p>
                </div>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              <p className={`${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} mb-4`}>
                Are you sure you want to delete <span className="font-bold">{deletingAssistant.name}</span>?
              </p>
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                All settings and configurations for this assistant will be permanently removed.
              </p>
            </div>

            {/* Modal Footer */}
            <div className={`flex items-center justify-end gap-3 p-6 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <button
                onClick={closeDeleteModal}
                disabled={isDeleting}
                className={`px-6 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAssistant}
                disabled={isDeleting}
                className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Deleting...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete Assistant
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Details Modal */}
      {isViewDetailsOpen && viewingAssistant && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl`}>
            {/* Modal Header */}
            <div className={`p-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center">
                    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <div>
                    <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      {viewingAssistant.name}
                    </h2>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>
                      AI Assistant Details
                    </p>
                  </div>
                </div>
                <button
                  onClick={closeViewDetails}
                  className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
                >
                  <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {/* System Message */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-3`}>
                  System Message
                </label>
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'} ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                  <p className="whitespace-pre-wrap">{viewingAssistant.system_message}</p>
                </div>
              </div>

              {/* Call Greeting */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-3`}>
                  Call Greeting
                </label>
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'} ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                  <p className="whitespace-pre-wrap">{viewingAssistant.call_greeting || DEFAULT_CALL_GREETING}</p>
                </div>
              </div>

              {/* Configuration Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* API Key Status */}
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    API Key Status
                  </label>
                  <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                    {viewingAssistant.has_api_key ? (
                      <>
                        <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className={`font-semibold text-green-500`}>
                          Configured
                        </span>
                        {viewingAssistant.api_key_label && (
                          <span className={`${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} text-xs`}>
                            • {viewingAssistant.api_key_label}
                            {viewingAssistant.api_key_provider ? ` (${displayProviderLabel(viewingAssistant.api_key_provider)})` : ''}
                          </span>
                        )}
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <span className={`font-semibold text-red-500`}>
                          Not Configured
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Voice */}
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    Voice
                  </label>
                  <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                    <svg className={`w-5 h-5 ${isDarkMode ? 'text-primary' : 'text-primary'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.536a5 5 0 001.414 1.06m2.828-9.9a9 9 0 012.828 0" />
                    </svg>
                    <span className={`font-semibold capitalize ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      {viewingAssistant.voice}
                    </span>
                  </div>
                </div>

                {/* Temperature */}
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    Temperature
                  </label>
                  <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                    <svg className={`w-5 h-5 ${isDarkMode ? 'text-primary' : 'text-primary'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span className={`font-semibold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      {viewingAssistant.temperature}
                    </span>
                  </div>
                </div>

                {/* Created At */}
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    Created
                  </label>
                  <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                    <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      {new Date(viewingAssistant.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                </div>

                {/* Updated At */}
                <div>
                  <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                    Last Updated
                  </label>
                  <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                    <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                      {new Date(viewingAssistant.updated_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Assistant ID */}
              <div>
                <label className={`block text-sm font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} mb-2`}>
                  Assistant ID
                </label>
                <div className={`flex items-center gap-3 p-4 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                  <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                  </svg>
                  <code className={`text-sm font-mono ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'}`}>
                    {viewingAssistant.id}
                  </code>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className={`flex items-center justify-between p-6 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <button
                onClick={closeViewDetails}
                className={`px-6 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors`}
              >
                Close
              </button>
              <div className="flex gap-3">
                {viewingAssistant.has_knowledge_base && viewingAssistant.knowledge_base_files && viewingAssistant.knowledge_base_files.length > 0 && (
                  <button
                    onClick={() => {
                      // Show document list modal
                      setIsDocumentPreviewOpen(true);
                    }}
                    className={`px-6 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-600 hover:bg-blue-700'} text-white transition-colors flex items-center gap-2`}
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    View Documents ({viewingAssistant.knowledge_base_files.length})
                  </button>
                )}
                <button
                  onClick={() => {
                    closeViewDetails();
                    openDeleteModal(viewingAssistant);
                  }}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-semibold transition-colors flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Delete
                </button>
                <button
                  onClick={() => {
                    closeViewDetails();
                    openEditModal(viewingAssistant);
                  }}
                  className="px-6 py-3 bg-gradient-to-r from-primary to-primary/90 text-white rounded-xl font-semibold hover:shadow-xl hover:shadow-primary/20 transition-all duration-200 flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Document Preview Modal */}
      {isDocumentPreviewOpen && viewingAssistant && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
          <div className={`${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl flex flex-col`}>
            {/* Modal Header */}
            <div className={`p-6 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                  </div>
                  <div>
                    <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                      {previewingDocument ? previewingDocument.filename : 'Knowledge Base Documents'}
                    </h2>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'} mt-1`}>
                      {previewingDocument ? 'Extracted Content' : `${viewingAssistant.knowledge_base_files?.length || 0} documents available`}
                    </p>
                  </div>
                </div>
                <button
                  onClick={closeDocumentPreview}
                  className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
                >
                  <svg className={`w-6 h-6 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6">
              {!previewingDocument ? (
                // Document List View
                <div className="space-y-3">
                  {viewingAssistant.knowledge_base_files && viewingAssistant.knowledge_base_files.map((file) => (
                    <div
                      key={file.filename}
                      className={`p-4 rounded-xl border ${isDarkMode ? 'bg-gray-900 border-gray-700 hover:border-gray-600' : 'bg-white border-neutral-mid/10 hover:border-blue-300'} transition-all cursor-pointer group`}
                      onClick={() => handleViewDocument(viewingAssistant.id, file)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          file.file_type === 'pdf'
                            ? 'bg-red-100 text-red-600'
                            : file.file_type === 'docx' || file.file_type === 'doc'
                              ? 'bg-blue-100 text-blue-600'
                              : file.file_type === 'xlsx' || file.file_type === 'xls'
                                ? 'bg-green-100 text-green-600'
                                : 'bg-gray-100 text-gray-600'
                        }`}>
                          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`text-base font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'} truncate group-hover:text-blue-600 transition-colors`}>
                            {file.filename}
                          </p>
                          <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                            {formatFileSize(file.file_size)} • {file.file_type.toUpperCase()} • Uploaded {new Date(file.uploaded_at).toLocaleDateString()}
                          </p>
                        </div>
                        <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400 group-hover:text-blue-400' : 'text-neutral-mid group-hover:text-blue-600'} transition-colors flex-shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                // Document Content View
                <div className="space-y-4">
                  <button
                    onClick={() => {
                      setPreviewingDocument(null);
                      setDocumentContent('');
                    }}
                    className={`flex items-center gap-2 text-sm ${isDarkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'} transition-colors`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back to documents
                  </button>

                  {loadingDocumentContent ? (
                    <div className="flex flex-col items-center justify-center py-12">
                      <svg className="animate-spin h-12 w-12 text-primary mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                        Extracting document content...
                      </p>
                    </div>
                  ) : (
                    <div className={`p-6 rounded-xl ${isDarkMode ? 'bg-gray-900' : 'bg-neutral-light'}`}>
                      <div className={`flex items-center gap-3 mb-4 pb-4 border-b ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          previewingDocument.file_type === 'pdf'
                            ? 'bg-red-100 text-red-600'
                            : previewingDocument.file_type === 'docx' || previewingDocument.file_type === 'doc'
                              ? 'bg-blue-100 text-blue-600'
                              : previewingDocument.file_type === 'xlsx' || previewingDocument.file_type === 'xls'
                                ? 'bg-green-100 text-green-600'
                                : 'bg-gray-100 text-gray-600'
                        }`}>
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div>
                          <p className={`font-medium ${isDarkMode ? 'text-white' : 'text-neutral-dark'}`}>
                            {previewingDocument.filename}
                          </p>
                          <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`}>
                            {formatFileSize(previewingDocument.file_size)} • {previewingDocument.file_type.toUpperCase()}
                          </p>
                        </div>
                      </div>
                      <div className={`prose prose-sm max-w-none ${isDarkMode ? 'prose-invert' : ''}`}>
                        <pre className={`whitespace-pre-wrap font-sans text-sm ${isDarkMode ? 'text-gray-300' : 'text-neutral-dark'} leading-relaxed`}>
                          {documentContent}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className={`p-6 border-t ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'}`}>
              <button
                onClick={closeDocumentPreview}
                className={`px-6 py-3 rounded-xl font-semibold ${isDarkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-neutral-light text-neutral-dark hover:bg-neutral-mid/20'} transition-colors`}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
