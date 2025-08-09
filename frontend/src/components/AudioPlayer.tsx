import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Download, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface AudioPlayerProps {
  audioUrl?: string;
  filename?: string;
  isLoading?: boolean;
  generator?: string;
  heavyError?: string | null;
}

export const AudioPlayer = ({ audioUrl, filename, isLoading, generator, heavyError }: AudioPlayerProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioUrl]);

  const togglePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  if (isLoading) {
    return (
      <div className="bg-gradient-card p-6 rounded-lg border border-border animate-fade-in">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-primary/20 rounded-full flex items-center justify-center animate-pulse-glow">
            <Volume2 className="w-8 h-8 text-primary" />
          </div>
          <p className="text-muted-foreground">Generating your cinematic audio...</p>
        </div>
      </div>
    );
  }

  if (!audioUrl) {
    return (
      <div className="bg-gradient-card p-6 rounded-lg border border-border">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-muted/20 rounded-full flex items-center justify-center">
            <Volume2 className="w-8 h-8 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground">Your generated audio will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-card p-6 rounded-lg border border-border space-y-4 animate-fade-in">
      <audio ref={audioRef} src={audioUrl} />

      {/* File Info */}
      {filename && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-foreground font-medium truncate">{filename}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const link = document.createElement('a');
              link.href = audioUrl;
              link.download = filename;
              link.click();
            }}
          >
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
        </div>
      )}

      {generator && (
        <p className="text-xs text-muted-foreground">Generator: {generator === 'heavy' ? 'AI' : 'Fallback'}</p>
      )}
      {heavyError && (
        <p className="text-[10px] text-muted-foreground opacity-70">{heavyError}</p>
      )}

      {/* Player Controls */}
      <div className="space-y-3">
        <div className="flex items-center space-x-4">
          <Button
            onClick={togglePlayPause}
            size="lg"
            className="w-12 h-12 rounded-full bg-gradient-primary hover:shadow-glow-primary transition-all duration-300"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" />
            )}
          </Button>

          <div className="flex-1 space-y-1">
            {/* Progress Bar */}
            <div
              className="h-2 bg-muted rounded-full cursor-pointer relative overflow-hidden"
              onClick={handleSeek}
            >
              <div
                className="h-full bg-gradient-primary transition-all duration-150"
                style={{ width: `${progress}%` }}
              />
            </div>
            
            {/* Time Display */}
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>

        {/* Volume Control */}
        <div className="flex items-center space-x-3">
          <Volume2 className="w-4 h-4 text-muted-foreground" />
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={handleVolumeChange}
            className={cn(
              "flex-1 h-1 bg-muted rounded-lg appearance-none cursor-pointer",
              "slider-thumb:appearance-none slider-thumb:w-3 slider-thumb:h-3",
              "slider-thumb:rounded-full slider-thumb:bg-primary"
            )}
          />
        </div>
      </div>
    </div>
  );
};