import React from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/contexts/ToastContext';

interface ApiKeyItemProps {
  apiKey: {
    id: string;
    name: string;
    key: string;
    created: string;
    last: string;
    scopes: string[];
  };
  onRevoke: (id: string) => void;
  onCopy: (key: string) => void;
  isGenerating: boolean;
}

export function ApiKeyItem({
  apiKey,
  onRevoke,
  onCopy,
  isGenerating
}: ApiKeyItemProps) {
  const { showToast } = useToast();

  const handleCopy = () => {
    onCopy(apiKey.key);
    showToast('Key copied to clipboard');
  };

  return (
    <div className="border border-border p-4 relative group">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-foreground">{apiKey.name}</span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
          >
            copy
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-danger hover:text-danger"
            onClick={() => onRevoke(apiKey.id)}
          >
            revoke
          </Button>
        </div>
      </div>
      <div className="font-mono text-[10px] text-muted-foreground break-all mb-2">{apiKey.key}</div>
      <div className="flex gap-4 text-[10px] font-mono text-muted-foreground">
        <span>created {apiKey.created}</span>
        <span>last used {apiKey.last}</span>
        <span>scopes · {apiKey.scopes.join(', ')}</span>
      </div>
    </div>
  );
}