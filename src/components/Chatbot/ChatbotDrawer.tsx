import React from 'react';
import { X, Sparkles, Maximize2 } from 'lucide-react';
import { GeminiChatbot } from './GeminiChatbot';

interface ChatbotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onDispatchToSandbox?: (command: string) => void;
  onExpandToTab?: () => void;
}

export const ChatbotDrawer: React.FC<ChatbotDrawerProps> = ({
  isOpen,
  onClose,
  onDispatchToSandbox,
  onExpandToTab,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[500px] bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      {/* Drawer Header */}
      <div className="p-3 border-b border-zinc-800 bg-zinc-900/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-emerald-500/10 text-emerald-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-semibold text-xs text-zinc-100">Gemini Copilot Assistant</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
            gemini-3.8-flash
          </span>
        </div>

        <div className="flex items-center gap-1">
          {onExpandToTab && (
            <button
              onClick={onExpandToTab}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              title="Buka sebagai Tab Penuh"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            title="Tutup Drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Drawer Body */}
      <div className="flex-1 overflow-hidden">
        <GeminiChatbot onDispatchToSandbox={onDispatchToSandbox} isCompact={true} />
      </div>
    </div>
  );
};
