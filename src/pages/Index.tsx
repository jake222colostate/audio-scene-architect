import React, { useState } from 'react';
import { AudioForm } from '@/components/AudioForm';
import { AudioPlayer } from '@/components/AudioPlayer';
import { ConsolePanel } from '@/components/ConsolePanel';
import soundforgeLogo from '@/assets/soundforge-logo.png';
import { useToast } from '@/hooks/use-toast';

interface GeneratedAudio {
  url: string;
  filename: string;
}

interface AudioRequest {
  filename: string;
  prompt: string;
  status: "queued" | "generating" | "complete" | "canceled" | "error";
}

const Index = () => {
  const [generatedAudio, setGeneratedAudio] = useState<GeneratedAudio | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<{error: string, trace: string, status: number} | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [audioRequests, setAudioRequests] = useState<AudioRequest[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
  const [lastFailedRequest, setLastFailedRequest] = useState<{prompt: string, duration: number} | null>(null);
  const { toast } = useToast();

  // Logging utility function with enhanced error context
  const logLine = (message: string, level: 'INFO' | 'WARNING' | 'ERROR' = 'INFO') => {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${level}: ${message}`;
    setLogs(prev => [...prev, logMessage]);
  };

  // Retry function for failed requests
  const retryLastRequest = async () => {
    if (lastFailedRequest) {
      logLine(`🔄 Retrying failed request: "${lastFailedRequest.prompt.substring(0, 30)}..."`, 'INFO');
      setError(null);
      setErrorMsg("");
      await handleGenerateAudio(lastFailedRequest.prompt, lastFailedRequest.duration);
    }
  };

  // Poll status for all pending requests
  React.useEffect(() => {
    const interval = setInterval(async () => {
      const pendingRequests = audioRequests.filter(req => 
        req.status === "queued" || req.status === "generating"
      );
      
      if (pendingRequests.length > 0) {
        logLine(`⏳ Polling status for ${pendingRequests.length} pending requests`);
      }
      
      for (const request of pendingRequests) {
        try {
          const response = await fetch(`/api/status/${request.filename}`);
          if (response.ok) {
            const statusData = await response.json();
            
            // Log status changes
            if (statusData.status !== request.status) {
              logLine(`📊 Status update for ${request.filename}: ${request.status} → ${statusData.status}`);
            }
            
            setAudioRequests(prev => prev.map(req => 
              req.filename === request.filename 
                ? { ...req, status: statusData.status }
                : req
            ));
            
            // If complete, set as generated audio and show success
            if (statusData.status === "complete" && statusData.file_exists) {
              setGeneratedAudio({
                url: statusData.file_url,
                filename: request.filename
              });
              
              logLine(`✅ Audio generation completed successfully: ${request.filename}`, 'INFO');
              
              toast({
                title: "Audio Generated Successfully!",
                description: `Generated for: "${request.prompt.substring(0, 50)}..."`,
              });
            } else if (statusData.status === "error") {
              logLine(`❌ Audio generation failed: ${request.filename}`, 'ERROR');
              logLine(`🔄 You can retry by clicking "Generate Audio" again`, 'INFO');
              
              toast({
                title: "Generation Failed",
                description: `Failed to generate audio for: "${request.prompt.substring(0, 30)}...". Check console logs and try again.`,
                variant: "destructive",
              });
            }
          }
        } catch (error) {
          logLine(`❌ Failed to poll status for ${request.filename}: ${error}`, 'ERROR');
          console.error(`Failed to poll status for ${request.filename}:`, error);
        }
      }
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(interval);
  }, [audioRequests, toast]);

  const handleCancelAudio = async (filename: string) => {
    try {
      logLine(`🚫 Attempting to cancel audio generation: ${filename}`);
      
      const response = await fetch(`/api/cancel-audio/${filename}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        logLine(`✅ Audio generation canceled successfully: ${filename}`);
        setAudioRequests(prev => prev.map(req => 
          req.filename === filename 
            ? { ...req, status: "canceled" }
            : req
        ));
        
        toast({
          title: "Audio Generation Canceled",
          description: "The audio generation has been canceled.",
        });
      } else {
        logLine(`❌ Failed to cancel audio generation: ${response.statusText}`, 'ERROR');
      }
    } catch (error) {
      logLine(`❌ Cancel request failed: ${error}`, 'ERROR');
      console.error('Failed to cancel audio:', error);
    }
  };

  const handleGenerateAudio = async (prompt: string, duration: number) => {
    setIsLoading(true);
    setIsGenerating(true);
    setError(null);
    setErrorMsg("");

    logLine(`⏳ Sending audio generation request to backend...`);
    logLine(`📝 Prompt: "${prompt.substring(0, 100)}${prompt.length > 100 ? '...' : ''}"`);
    logLine(`⏱️ Duration: ${duration} seconds`);

    try {
      // Call the FastAPI backend
      const response = await fetch('/api/generate-audio', {
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
        const errorData = await response.json().catch(() => ({ 
          error: 'Unknown error', 
          message: 'Server returned an error',
          suggest: 'Try again with a different prompt'
        }));
        
        const errorMessage = errorData.message || errorData.error || `HTTP error! status: ${response.status}`;
        
        logLine(`❌ Backend returned error: ${errorMessage}`, 'ERROR');
        logLine(`📊 Response status: ${response.status}`, 'ERROR');
        if (errorData.suggest) {
          logLine(`💡 Suggestion: ${errorData.suggest}`, 'INFO');
        }
        
        const fullError = {
          error: errorMessage,
          trace: errorData.detail || '',
          status: response.status
        };
        setError(fullError);
        setLastFailedRequest({ prompt, duration });
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Add to audio requests for tracking
      if (data.status === 'queued') {
        const newRequest: AudioRequest = {
          filename: data.filename,
          prompt: prompt,
          status: "queued"
        };
        
        logLine(`✅ Audio generation queued successfully: ${data.filename}`);
        logLine(`🎯 File URL will be: ${data.file_url}`);
        
        setAudioRequests(prev => [newRequest, ...prev]);
        
        toast({
          title: "Audio Generation Queued",
          description: "Your audio has been added to the generation queue.",
        });
      } else {
        logLine(`⚠️ Unexpected response status: ${data.status}`, 'WARNING');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "There was an error generating your audio. Please try again.";
      
      logLine(`❌ Frontend error: ${errorMessage}`, 'ERROR');
      logLine(`🔄 You can retry by clicking the "Retry" button below`, 'INFO');
      
      // Set detailed error message for copyable display
      setErrorMsg(`❌ ${errorMessage}`);
      setLastFailedRequest({ prompt, duration });
      
      // If we don't already have a structured error, create one
      if (typeof err === 'string' || !err || typeof err !== 'object' || !('error' in err)) {
        setError({
          error: errorMessage,
          trace: '',
          status: 0
        });
      }
      
      toast({
        title: "Generation Failed", 
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setIsGenerating(false);
      logLine(`🏁 Audio generation request completed`);
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
            <AudioForm onSubmit={handleGenerateAudio} isLoading={isLoading} error={error} />
            
            {/* Loading State */}
            {isGenerating && (
              <div className="bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 p-3 rounded border border-blue-200 dark:border-blue-800">
                <p className="animate-pulse flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Generating audio... please wait
                </p>
              </div>
            )}
            
            {/* Error Display with Retry Button */}
            {(errorMsg || error) && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-red-600 dark:text-red-400 text-lg">❌</span>
                    <div>
                      <h3 className="text-red-800 dark:text-red-200 font-semibold">Audio Generation Failed</h3>
                      <p className="text-red-700 dark:text-red-300 text-sm mt-1">
                        {error?.error || errorMsg || "An unexpected error occurred"}
                      </p>
                    </div>
                  </div>
                </div>
                
                {lastFailedRequest && (
                  <div className="flex items-center gap-2 pt-2 border-t border-red-200 dark:border-red-700">
                    <button
                      onClick={retryLastRequest}
                      disabled={isLoading}
                      className="bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
                    >
                      {isLoading ? "Retrying..." : "🔄 Retry"}
                    </button>
                    <span className="text-red-600 dark:text-red-400 text-xs">
                      Retry: "{lastFailedRequest.prompt.substring(0, 50)}..."
                    </span>
                  </div>
                )}
                
                {errorMsg && (
                  <pre className="bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 p-2 rounded border border-red-300 dark:border-red-600 overflow-auto text-xs mt-2">
                    {errorMsg}
                  </pre>
                )}
              </div>
            )}
            
            {/* Audio Request Queue Status */}
            {audioRequests.length > 0 && (
              <div className="bg-gradient-card p-4 rounded-lg border border-border space-y-3">
                <h3 className="text-lg font-semibold text-foreground">Audio Generation Queue</h3>
                <div className="space-y-2">
                  {audioRequests.map((request) => (
                    <div key={request.filename} className="flex items-center justify-between p-3 bg-secondary/30 rounded border border-border">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground truncate">
                          {request.prompt.substring(0, 60)}...
                        </p>
                        <p className={`text-xs capitalize ${
                          request.status === 'queued' ? 'text-yellow-600' :
                          request.status === 'generating' ? 'text-blue-600' :
                          request.status === 'complete' ? 'text-green-600' :
                          request.status === 'canceled' ? 'text-gray-600' :
                          'text-red-600'
                        }`}>
                          {request.status === 'queued' ? '⏳ Queued' :
                           request.status === 'generating' ? '🎧 Generating...' :
                           request.status === 'complete' ? '✅ Complete' :
                           request.status === 'canceled' ? '❌ Canceled' :
                           '⚠️ Error'}
                        </p>
                      </div>
                      {(request.status === 'queued' || request.status === 'generating') && (
                        <button
                          onClick={() => handleCancelAudio(request.filename)}
                          className="text-red-600 hover:text-red-800 text-sm underline ml-3"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Audio Player and Console */}
          <div className="space-y-6">
            <AudioPlayer
              audioUrl={generatedAudio?.url}
              filename={generatedAudio?.filename}
              isLoading={isLoading}
            />
            
            {/* Console Panel - Always visible in development, conditionally in production */}
            <ConsolePanel
              logs={logs}
              onClear={() => {
                setLogs([]);
                logLine('🧹 Console cleared by user');
              }}
              isOpen={isConsoleOpen}
              onToggle={() => setIsConsoleOpen(!isConsoleOpen)}
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
