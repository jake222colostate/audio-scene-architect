import React, { useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Trash2, ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface ConsolePanelProps {
  logs: string[];
  onClear: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const ConsolePanel: React.FC<ConsolePanelProps> = ({ 
  logs, 
  onClear, 
  isOpen, 
  onToggle 
}) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs are added
  useEffect(() => {
    if (logContainerRef.current && isOpen) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  const copyAllLogs = async () => {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
    } catch (err) {
      console.error('Failed to copy logs:', err);
    }
  };

  const getLogLineStyle = (line: string) => {
    // Error and failure logs
    if (line.includes('ERROR') || line.includes('❌') || line.includes('[FATAL]') || line.includes('[FAIL]')) {
      return 'text-red-400';
    }
    // Warning and cancellation logs
    if (line.includes('WARNING') || line.includes('⚠️') || line.includes('[WARNING]') || line.includes('[CANCELED]')) {
      return 'text-yellow-300';
    }
    // Success logs
    if (line.includes('[SUCCESS]') || line.includes('✅') || line.includes('[FINISH]') || line.includes('[SAVE]')) {
      return 'text-green-400';
    }
    // Request and API logs
    if (line.includes('[REQUEST]') || line.includes('[API]')) {
      return 'text-blue-300';
    }
    // Queue operations
    if (line.includes('[QUEUE]')) {
      return 'text-cyan-300';
    }
    // Engine and model operations
    if (line.includes('[ENGINE]') || line.includes('[MODEL]') || line.includes('⏳')) {
      return 'text-purple-300';
    }
    // Export and file operations
    if (line.includes('[EXPORT]')) {
      return 'text-orange-300';
    }
    // Health monitoring
    if (line.includes('[HEALTH]')) {
      return 'text-teal-300';
    }
    // Info and other logs
    if (line.includes('INFO') || line.includes('ℹ️')) {
      return 'text-gray-300';
    }
    return 'text-gray-400';
  };

  return (
    <div className="console-container bg-gradient-card border border-border rounded-lg overflow-hidden">
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-secondary/20 transition-colors">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-muted-foreground" />
              <span className="font-semibold text-foreground">Console</span>
              <span className="text-xs text-muted-foreground">
                ({logs.length} {logs.length === 1 ? 'log' : 'logs'})
              </span>
            </div>
            <div className="flex items-center gap-2">
              {isOpen && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      copyAllLogs();
                    }}
                    className="h-8 px-2 text-xs"
                  >
                    <Copy className="w-3 h-3 mr-1" />
                    Copy
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onClear();
                    }}
                    className="h-8 px-2 text-xs"
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Clear
                  </Button>
                </>
              )}
              {isOpen ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
          </div>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <div 
            ref={logContainerRef}
            className="console console-container border-t border-border"
          >
            {logs.length === 0 ? (
              <div className="text-gray-500 italic text-center py-8">
                No logs yet. Start generating audio to see live backend logs here.
              </div>
            ) : (
              logs.map((line, idx) => (
                <div 
                  key={idx} 
                  className={`mb-1 ${getLogLineStyle(line)}`}
                >
                  {line}
                </div>
              ))
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
};