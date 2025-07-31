import { useState } from 'react';
import { AudioForm } from '@/components/AudioForm';
import { AudioPlayer } from '@/components/AudioPlayer';
import soundforgeLogo from '@/assets/soundforge-logo.png';
import { useToast } from '@/hooks/use-toast';

interface GeneratedAudio {
  url: string;
  filename: string;
}

const Index = () => {
  const [generatedAudio, setGeneratedAudio] = useState<GeneratedAudio | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleGenerateAudio = async (prompt: string, duration: number) => {
    setIsLoading(true);
    setGeneratedAudio(null);

    try {
      // Send request to FastAPI backend
      const response = await fetch('/generate-audio', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          duration,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.file_url) {
        setGeneratedAudio({
          url: data.file_url,
          filename: data.file_url.split('/').pop() || 'audio.mp3',
        });
        
        toast({
          title: "Audio Generated Successfully!",
          description: "Your cinematic audio is ready to play.",
        });
      }
    } catch (error) {
      console.error('Error generating audio:', error);
      toast({
        title: "Generation Failed",
        description: "There was an error generating your audio. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center space-x-3">
            <img src={soundforgeLogo} alt="SoundForge.AI" className="h-10 w-auto" />
            <div>
              <h1 className="text-xl font-bold text-foreground">SoundForge.AI</h1>
              <p className="text-xs text-muted-foreground">Cinematic Audio Generation</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-2 gap-8 max-w-7xl mx-auto">
          {/* Left Column - Input Form */}
          <div className="space-y-6">
            <AudioForm onSubmit={handleGenerateAudio} isLoading={isLoading} />
          </div>

          {/* Right Column - Audio Player */}
          <div className="space-y-6">
            <AudioPlayer
              audioUrl={generatedAudio?.url}
              filename={generatedAudio?.filename}
              isLoading={isLoading}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-border bg-card/30 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="text-center text-sm text-muted-foreground">
            <p>Built with React + TailwindCSS • Ready for FastAPI backend integration</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
