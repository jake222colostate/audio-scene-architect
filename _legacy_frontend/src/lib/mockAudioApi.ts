// Mock API for audio generation - simulates FastAPI backend
// This provides immediate functionality while keeping the real backend code intact

export interface GenerateAudioRequest {
  prompt: string;
  duration: number;
  sfx_prompts?: string[];
}

export interface GenerateAudioResponse {
  file_url: string;
  sfx_used: string[];
  status: string;
}

// Simulate audio generation with delay and mock data
export async function generateAudio(data: GenerateAudioRequest): Promise<GenerateAudioResponse> {
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
  
  // Mock filename and response
  const mockFilename = `generated_${Date.now()}.mp3`;
  
  // Generate mock SFX based on prompt keywords
  const sfxKeywords = ['whisper', 'footsteps', 'wind', 'echo', 'creak', 'breath'];
  const mockSfx = sfxKeywords
    .filter(() => Math.random() > 0.6)
    .slice(0, 2);
  
  return {
    file_url: `/mock-audio/${mockFilename}`,
    sfx_used: mockSfx,
    status: "success"
  };
}

// For demo purposes, return a sample audio URL
export function getMockAudioUrl(): string {
  // This returns a publicly available sample audio file for demonstration
  return "https://www.soundjay.com/misc/sounds-1.mp3";
}
