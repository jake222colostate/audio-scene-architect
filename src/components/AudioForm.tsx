import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Wand2, Clock } from 'lucide-react';

interface AudioFormProps {
  onSubmit: (prompt: string, duration: number) => void;
  isLoading: boolean;
}

export const AudioForm = ({ onSubmit, isLoading }: AudioFormProps) => {
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState<string>('60');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      onSubmit(prompt.trim(), parseInt(duration));
    }
  };

  const examplePrompts = [
    "Epic battle scene with orchestral crescendo and thunderous drums",
    "Mysterious forest ambiance with subtle magic and whispers",
    "Futuristic cityscape with electronic undertones and distant traffic",
    "Romantic piano melody under a starlit sky with gentle strings"
  ];

  return (
    <div className="bg-gradient-card p-6 rounded-lg border border-border space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-semibold text-foreground">Generate Cinematic Audio</h2>
        <p className="text-sm text-muted-foreground">
          Describe your scene and let AI create the perfect soundtrack
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Prompt Input */}
        <div className="space-y-3">
          <Label htmlFor="prompt" className="text-sm font-medium text-foreground">
            Scene Description
          </Label>
          <Textarea
            id="prompt"
            placeholder="Describe the cinematic scene you want audio for..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[120px] resize-none bg-secondary/50 border-border focus:border-primary transition-colors"
            disabled={isLoading}
          />
          
          {/* Example Prompts */}
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">Try these examples:</p>
            <div className="grid gap-2">
              {examplePrompts.map((example, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setPrompt(example)}
                  className="text-left text-xs p-2 rounded bg-muted/50 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                  disabled={isLoading}
                >
                  "{example}"
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Duration Selection */}
        <div className="space-y-3">
          <Label htmlFor="duration" className="text-sm font-medium text-foreground flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Duration
          </Label>
          <Select value={duration} onValueChange={setDuration} disabled={isLoading}>
            <SelectTrigger className="bg-secondary/50 border-border focus:border-primary">
              <SelectValue placeholder="Select duration" />
            </SelectTrigger>
            <SelectContent className="bg-popover border-border">
              <SelectItem value="30">30 seconds</SelectItem>
              <SelectItem value="60">60 seconds</SelectItem>
              <SelectItem value="90">90 seconds</SelectItem>
              <SelectItem value="120">120 seconds</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={!prompt.trim() || isLoading}
          className="w-full bg-gradient-primary hover:shadow-glow-primary transition-all duration-300 font-medium"
          size="lg"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-primary-foreground/20 border-t-primary-foreground rounded-full animate-spin mr-2" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 className="w-4 h-4 mr-2" />
              Generate Audio
            </>
          )}
        </Button>
      </form>
    </div>
  );
};