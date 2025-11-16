// MongoDB Migration Script: Fix Assistant Configurations
// Run with: mongosh "mongodb+srv://..." < fix-assistant-configs.js

print("\n=== Fixing Assistant Configurations ===\n");

// Fix Issue 1: OpenAI Realtime with wrong model IDs
print("1. Fixing OpenAI Realtime assistants with mismatched models...");

// If provider is "openai-realtime", ensure correct models
const realtimeFix = db.ai_assistants.updateMany(
  { provider: "openai-realtime" },
  {
    $set: {
      asr_provider: "openai",
      asr_model: "whisper-1",
      tts_provider: "openai",
      tts_model: "tts-1",
      tts_voice: "alloy",
      llm_provider: "openai-realtime",
      llm_model: "gpt-4o-realtime-preview"
    }
  }
);
print(`   Updated ${realtimeFix.modifiedCount} OpenAI Realtime assistants`);

// Fix assistants with OpenAI ASR but Deepgram model
const asrFix = db.ai_assistants.updateMany(
  {
    asr_provider: "openai",
    asr_model: { $in: ["nova-2", "nova-3", "base", "whisper"] }
  },
  {
    $set: { asr_model: "whisper-1" }
  }
);
print(`   Fixed ${asrFix.modifiedCount} assistants with wrong OpenAI ASR model`);

// Fix assistants with OpenAI TTS but ElevenLabs model
const ttsFix = db.ai_assistants.updateMany(
  {
    tts_provider: "openai",
    tts_model: { $regex: /^eleven_/ }
  },
  {
    $set: {
      tts_model: "tts-1",
      tts_voice: "alloy"
    }
  }
);
print(`   Fixed ${ttsFix.modifiedCount} assistants with wrong OpenAI TTS model`);

print("\n2. Fixing ElevenLabs voice IDs...");

// Fix common invalid ElevenLabs voice names
const elevenLabsVoices = {
  "rachel": "EXAVITQu4vr4xnSDxMaL",  // Sarah
  "bella": "FGY2WhTYpPnrIDTdsKH5",   // Laura
  "alice": "Xb7hH8MSUJpSbSDYk0k2",   // Alice
  "matilda": "XrExE9yKIg1WjnnlVkGX", // Matilda
  "domi": "cgSgspJ2msm6clMCkdW9",    // Jessica
  "antoni": "2EiwWnXFnvU5JabPnv8n",  // Clyde
  "josh": "TX3LPaxmHKxFdv7VOQHJ",    // Liam
  "daniel": "onwK4e9ZLuTAKqWW03F9",  // Daniel
  "george": "JBFqnCBsd6RMkjVDRZzb",  // George
  "charlie": "IKne3meq5aSn9XLyUdCD"  // Charlie
};

let elevenLabsFixed = 0;
for (const [oldVoice, newVoiceId] of Object.entries(elevenLabsVoices)) {
  const result = db.ai_assistants.updateMany(
    { tts_provider: "elevenlabs", tts_voice: oldVoice },
    { $set: { tts_voice: newVoiceId } }
  );
  if (result.modifiedCount > 0) {
    print(`   Replaced "${oldVoice}" with "${newVoiceId}" (${result.modifiedCount} assistants)`);
    elevenLabsFixed += result.modifiedCount;
  }
}
print(`   Total ElevenLabs voices fixed: ${elevenLabsFixed}`);

print("\n3. Fixing Sarvam configurations...");

// Fix Sarvam speaker capitalization
const sarvamSpeakers = [
  "Manisha", "Hitesh", "Abhilash", "Karun", "Anushka", "Vidya",
  "Arya", "Priya", "Ravi", "Sneha", "Aditya", "Chirag", "Harsh",
  "Rahul", "Rohan", "Kiran", "Vikram", "Rajesh", "Anirudh", "Ishaan",
  "Isha", "Ritu", "Sakshi", "Neha", "Pooja", "Simran", "Kavya",
  "Anjali", "Sunita", "Tara", "Kriti"
];

let sarvamVoiceFixed = 0;
for (const speaker of sarvamSpeakers) {
  const result = db.ai_assistants.updateMany(
    { tts_provider: "sarvam", tts_voice: speaker },
    { $set: { tts_voice: speaker.toLowerCase() } }
  );
  if (result.modifiedCount > 0) {
    print(`   Lowercased "${speaker}" (${result.modifiedCount} assistants)`);
    sarvamVoiceFixed += result.modifiedCount;
  }
}
print(`   Total Sarvam voices fixed: ${sarvamVoiceFixed}`);

// Fix deprecated Sarvam model
const sarvamModelFix = db.ai_assistants.updateMany(
  { tts_provider: "sarvam", tts_model: "bulbul:v1" },
  { $set: { tts_model: "bulbul:v2" } }
);
print(`   Updated ${sarvamModelFix.modifiedCount} Sarvam models from v1 to v2`);

print("\n=== Migration Summary ===");
print(`Total assistants modified: ${realtimeFix.modifiedCount + asrFix.modifiedCount + ttsFix.modifiedCount + elevenLabsFixed + sarvamVoiceFixed + sarvamModelFix.modifiedCount}`);

print("\n=== Verifying Assistants ===\n");

// Show all assistants after fix
const assistants = db.ai_assistants.find({}, {
  name: 1,
  provider: 1,
  asr_provider: 1,
  asr_model: 1,
  tts_provider: 1,
  tts_model: 1,
  tts_voice: 1,
  llm_provider: 1,
  llm_model: 1
}).toArray();

print("All Assistants:");
assistants.forEach(a => {
  print(`\n  ${a.name || "Unnamed"} (${a._id})`);
  print(`    Provider: ${a.provider || "custom"}`);
  if (a.provider === "custom" || !a.provider) {
    print(`    ASR: ${a.asr_provider} / ${a.asr_model}`);
    print(`    LLM: ${a.llm_provider} / ${a.llm_model}`);
    print(`    TTS: ${a.tts_provider} / ${a.tts_model} / ${a.tts_voice}`);
  } else if (a.provider === "openai-realtime") {
    print(`    LLM: ${a.llm_provider} / ${a.llm_model}`);
    print(`    TTS: ${a.tts_provider} / ${a.tts_model} / ${a.tts_voice}`);
  }
});

print("\n=== Migration Complete ===\n");
