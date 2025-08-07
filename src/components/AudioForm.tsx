import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Wand2, Clock } from 'lucide-react';

interface AudioFormProps {
  onSubmit: (prompt: string, duration: number) => void;
  isLoading: boolean;
  error?: { error: string; trace: string; status: number } | null;
}

export const AudioForm = ({ onSubmit, isLoading, error }: AudioFormProps) => {
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState<string>('60');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const dur = parseInt(duration, 10);

    if (isNaN(dur) || dur < 10 || dur > 60) {
      alert('Duration must be between 10 and 60 seconds.');
      return;
    }
    if (!prompt.trim()) {
      alert('Please enter a prompt.');
      return;
    }
    onSubmit(prompt.trim(), dur);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {/* Prompt */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="prompt" className="text-foreground/80">Audio Prompt</Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder='e.g., "spaceship corridor hum", "leaves crunching under footsteps"'
            className="min-h-[120px] bg-secondary/50 border-border"
          />
        </div>

        {/* Duration */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="duration" className="text-foreground/80 flex items-center gap-2">
            <Clock className="w-4 h-4" /> Duration (10–60s)
          </Label>
          <input
            id="duration"
            type="number"
            min={10}
            max={60}
            step={1}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            className="bg-secondary/50 border border-border rounded-md px-3 py-2 outline-none focus:border-primary"
          />
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between">
          <Button type="submit" disabled={isLoading}>
            <Wand2 className="w-4 h-4 mr-2" />
            {isLoading ? 'Generating…' : 'Generate Audio'}
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-destructive/10 text-destructive p-4 rounded-md border border-destructive/20 overflow-auto font-mono text-sm whitespace-pre-wrap">
            <div className="font-semibold mb-1">Error</div>
            <div>{error.error}</div>
            {error.trace && (
              <>
                <div className="mt-2 font-semibold">Trace</div>
                <pre className="whitespace-pre-wrap">{error.trace}</pre>
              </>
            )}
          </div>
        )}
      </form>
    </div>
  );
};

export default AudioForm;
