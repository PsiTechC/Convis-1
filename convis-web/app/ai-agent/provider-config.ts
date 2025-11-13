// Enhanced Provider Configuration with Complete Voice and Model Options
// All pricing data accurate as of January 2025

export const ENHANCED_TTS_VOICES = {
  cartesia: [
    { value: 'sonic', label: 'Sonic - Fast, natural voice', gender: 'neutral', accent: 'American' },
    { value: 'stella', label: 'Stella - Warm, friendly female', gender: 'female', accent: 'American' },
    { value: 'marcus', label: 'Marcus - Professional male', gender: 'male', accent: 'American' },
    { value: 'luna', label: 'Luna - Soft, gentle female', gender: 'female', accent: 'American' },
    { value: 'phoenix', label: 'Phoenix - Energetic male', gender: 'male', accent: 'American' },
    { value: 'aurora', label: 'Aurora - Clear, professional female', gender: 'female', accent: 'American' },
    { value: 'orion', label: 'Orion - Deep, authoritative male', gender: 'male', accent: 'American' },
    { value: 'nova', label: 'Nova - Bright, engaging female', gender: 'female', accent: 'American' }
  ],
  elevenlabs: [
    // Female voices - American
    { value: 'rachel', label: 'Rachel - Young female American', gender: 'female', accent: 'American' },
    { value: 'domi', label: 'Domi - Strong female American', gender: 'female', accent: 'American' },
    { value: 'bella', label: 'Bella - Soft young American female', gender: 'female', accent: 'American' },
    { value: 'elli', label: 'Elli - Emotional young female', gender: 'female', accent: 'American' },
    { value: 'emily', label: 'Emily - Calm American female', gender: 'female', accent: 'American' },
    { value: 'grace', label: 'Grace - Southern American female', gender: 'female', accent: 'American' },
    { value: 'sarah', label: 'Sarah - Soft young female', gender: 'female', accent: 'American' },
    // Female voices - British
    { value: 'charlotte', label: 'Charlotte - English female', gender: 'female', accent: 'British' },
    { value: 'alice', label: 'Alice - British female', gender: 'female', accent: 'British' },
    { value: 'matilda', label: 'Matilda - Warm British female', gender: 'female', accent: 'British' },
    // Male voices - American
    { value: 'antoni', label: 'Antoni - Well-rounded male', gender: 'male', accent: 'American' },
    { value: 'josh', label: 'Josh - Deep American male', gender: 'male', accent: 'American' },
    { value: 'arnold', label: 'Arnold - Crisp American male', gender: 'male', accent: 'American' },
    { value: 'adam', label: 'Adam - Deep American male', gender: 'male', accent: 'American' },
    { value: 'sam', label: 'Sam - Young American male', gender: 'male', accent: 'American' },
    { value: 'ethan', label: 'Ethan - American male', gender: 'male', accent: 'American' },
    { value: 'michael', label: 'Michael - American male', gender: 'male', accent: 'American' },
    { value: 'thomas', label: 'Thomas - Young American male', gender: 'male', accent: 'American' },
    // Male voices - British
    { value: 'callum', label: 'Callum - Hoarse British male', gender: 'male', accent: 'British' },
    { value: 'daniel', label: 'Daniel - Deep British male', gender: 'male', accent: 'British' },
    { value: 'george', label: 'George - Warm British male', gender: 'male', accent: 'British' },
    { value: 'harry', label: 'Harry - Anxious young male', gender: 'male', accent: 'British' },
    { value: 'joseph', label: 'Joseph - British male', gender: 'male', accent: 'British' },
    // Male voices - Other
    { value: 'charlie', label: 'Charlie - Australian male', gender: 'male', accent: 'Australian' },
    { value: 'fin', label: 'Fin - Irish male', gender: 'male', accent: 'Irish' },
    { value: 'james', label: 'James - Australian male', gender: 'male', accent: 'Australian' }
  ],
  openai: [
    { value: 'alloy', label: 'Alloy - Neutral, balanced', gender: 'neutral', accent: 'American' },
    { value: 'echo', label: 'Echo - Male voice', gender: 'male', accent: 'American' },
    { value: 'fable', label: 'Fable - British male', gender: 'male', accent: 'British' },
    { value: 'onyx', label: 'Onyx - Deep male', gender: 'male', accent: 'American' },
    { value: 'nova', label: 'Nova - Female voice', gender: 'female', accent: 'American' },
    { value: 'shimmer', label: 'Shimmer - Soft female', gender: 'female', accent: 'American' }
  ],
  sarvam: [
    { value: 'Manisha', label: 'Manisha - Female Hindi/English', gender: 'female', accent: 'Indian' },
    { value: 'Hitesh', label: 'Hitesh - Male Hindi/English', gender: 'male', accent: 'Indian' },
    { value: 'Abhilash', label: 'Abhilash - Male Hindi', gender: 'male', accent: 'Indian' },
    { value: 'Karun', label: 'Karun - Male Hindi', gender: 'male', accent: 'Indian' },
    { value: 'Anushka', label: 'Anushka - Female Hindi', gender: 'female', accent: 'Indian' },
    { value: 'Vidya', label: 'Vidya - Female Hindi', gender: 'female', accent: 'Indian' },
    { value: 'Arya', label: 'Arya - Female Hindi', gender: 'female', accent: 'Indian' },
    { value: 'Priya', label: 'Priya - Female Hindi', gender: 'female', accent: 'Indian' },
    { value: 'Ravi', label: 'Ravi - Male Hindi', gender: 'male', accent: 'Indian' },
    { value: 'Sneha', label: 'Sneha - Female Hindi', gender: 'female', accent: 'Indian' }
  ],
};

// Enhanced ASR Models with all available options
export const ENHANCED_ASR_MODELS = {
  deepgram: [
    { value: 'nova-2', label: 'Nova-2 (Latest, Most Accurate)', cost: 0.0043, latency: 75, costPerMin: 0.0043 },
    { value: 'nova-3', label: 'Nova-3 (Beta, Improved)', cost: 0.0059, latency: 80, costPerMin: 0.0059 },
    { value: 'whisper', label: 'Whisper (Good Accuracy)', cost: 0.0048, latency: 100, costPerMin: 0.0048 },
    { value: 'base', label: 'Base (Standard)', cost: 0.0125, latency: 85, costPerMin: 0.0125 }
  ],
  openai: [
    { value: 'whisper-1', label: 'Whisper-1 (General Purpose)', cost: 0.006, latency: 250, costPerMin: 0.006 }
  ],
  sarvam: [
    { value: 'saarika:v1', label: 'Saarika V1 (Indian Languages)', cost: 0.004, latency: 120, costPerMin: 0.004 },
    { value: 'saarika:v2', label: 'Saarika V2 (Improved)', cost: 0.005, latency: 110, costPerMin: 0.005 }
  ],
  google: [
    { value: 'default', label: 'Google Speech-to-Text Standard', cost: 0.006, latency: 130, costPerMin: 0.006 },
    { value: 'latest_long', label: 'Latest Long (Better for Long Audio)', cost: 0.009, latency: 145, costPerMin: 0.009 }
  ]
};

// Enhanced TTS Models with accurate per-character costs
export const ENHANCED_TTS_MODELS = {
  cartesia: [
    { value: 'sonic-english', label: 'Sonic English (Ultra-Fast)', cost: 0.025, latency: 100, costPerChar: 0.000025 }
  ],
  elevenlabs: [
    { value: 'eleven_turbo_v2', label: 'Eleven Turbo V2 (Fast, High Quality)', cost: 0.18, latency: 150, costPerChar: 0.00018 },
    { value: 'eleven_turbo_v2_5', label: 'Eleven Turbo V2.5 (Latest, Best Quality)', cost: 0.18, latency: 130, costPerChar: 0.00018 },
    { value: 'eleven_multilingual_v2', label: 'Eleven Multilingual V2', cost: 0.18, latency: 180, costPerChar: 0.00018 },
    { value: 'eleven_monolingual_v1', label: 'Eleven Monolingual V1 (English Only)', cost: 0.18, latency: 200, costPerChar: 0.00018 }
  ],
  openai: [
    { value: 'tts-1', label: 'TTS-1 (Fast, Good Quality)', cost: 0.015, latency: 250, costPerChar: 0.000015 },
    { value: 'tts-1-hd', label: 'TTS-1-HD (High Quality)', cost: 0.030, latency: 300, costPerChar: 0.000030 }
  ],
  sarvam: [
    { value: 'bulbul:v1', label: 'Bulbul V1 (Hindi/Indian)', cost: 0.004, latency: 120, costPerChar: 0.000004 },
    { value: 'bulbul:v2', label: 'Bulbul V2 (Better Quality)', cost: 0.006, latency: 130, costPerChar: 0.000006 }
  ]
};

// Enhanced LLM Models with accurate per-token costs
// For Custom Provider: Only OpenAI supported (5 best models from cheapest to expensive)
export const ENHANCED_LLM_MODELS = {
  openai: [
    // Sorted from cheapest/fastest to most expensive/capable
    { value: 'gpt-4o-mini', label: 'GPT-4O Mini - Cheapest & Fastest ($0.38/1M tokens)', costInput: 0.15, costOutput: 0.60, latency: 400, cost: '0.00038', speed: 'Fastest' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo - Very Fast ($1.00/1M tokens)', costInput: 0.50, costOutput: 1.50, latency: 300, cost: '0.001', speed: 'Very Fast' },
    { value: 'gpt-4o', label: 'GPT-4O - Balanced Performance ($6.25/1M tokens)', costInput: 2.50, costOutput: 10.00, latency: 800, cost: '0.00625', speed: 'Fast' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo - High Quality ($20/1M tokens)', costInput: 10.00, costOutput: 30.00, latency: 1000, cost: '0.02', speed: 'Moderate' },
    { value: 'o1-mini', label: 'O1 Mini - Most Expensive ($15/1M tokens)', costInput: 3.00, costOutput: 12.00, latency: 1200, cost: '0.015', speed: 'Advanced Reasoning' }
  ],
  'openai-realtime': [
    { value: 'gpt-4o-realtime-preview', label: 'GPT-4O Realtime Preview', cost: 0.30, latency: 320, costPerMin: 0.30 },
    { value: 'gpt-4o-realtime-preview-2024-10-01', label: 'GPT-4O Realtime 2024-10-01', cost: 0.30, latency: 320, costPerMin: 0.30 },
    { value: 'gpt-4o-realtime', label: 'GPT-4O Realtime (Stable)', cost: 0.30, latency: 280, costPerMin: 0.30 },
    { value: 'gpt-4o-mini-realtime-preview', label: 'GPT-4O Mini Realtime Preview', cost: 0.30, latency: 200, costPerMin: 0.30 },
    { value: 'gpt-4o-mini-realtime', label: 'GPT-4O Mini Realtime (Stable)', cost: 0.30, latency: 200, costPerMin: 0.30 }
  ]
};

// Twilio Cost
export const TWILIO_COST_PER_MIN = {
  usd: 0.014,
  inr: 5.5
};
