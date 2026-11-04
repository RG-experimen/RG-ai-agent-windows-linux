import React from 'react';
import { Terminal, Shield, Zap, Code2, Download, MonitorPlay, Sparkles, MessageSquare } from 'lucide-react';

export type TabType = 'sandbox' | 'chatbot' | 'inspector' | 'benchmark' | 'windows' | 'export';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  systemHealthy: boolean;
  onToggleDrawer?: () => void;
  isDrawerOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  systemHealthy,
  onToggleDrawer,
  isDrawerOpen,
}) => {
  const tabs = [
    { id: 'sandbox' as TabType, label: 'Agent Sandbox', icon: Terminal },
    { id: 'chatbot' as TabType, label: 'Gemini Chatbot', icon: Sparkles, badge: 'Live AI' },
    { id: 'inspector' as TabType, label: 'Bug Fixes & Diff', icon: Shield, badge: '7 Fixed' },
    { id: 'benchmark' as TabType, label: 'Performance Lab', icon: Zap, badge: '900x' },
    { id: 'windows' as TabType, label: 'Desktop Automation', icon: MonitorPlay },
    { id: 'export' as TabType, label: 'Export & Setup', icon: Download },
  ];

  return (
    <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Identity */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-inner">
              <Code2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-zinc-100 text-sm sm:text-base tracking-tight">
                  Multi-Provider AI Agent
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-emerald-400 font-mono">
                  v2.0 Fixed & Optimized
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span>Coding</span>
                <span aria-hidden="true">·</span>
                <span>Kali Hacking</span>
                <span aria-hidden="true">·</span>
                <span>Windows Control</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs (Functional Segmented Buttons) */}
          <nav className="hidden md:flex items-center gap-1 bg-zinc-900/90 p-1 rounded-xl border border-zinc-800">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-zinc-800 text-zinc-100 shadow-sm border border-zinc-700/60'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-zinc-400'}`} />
                  <span>{tab.label}</span>
                  {tab.badge && (
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                        isActive
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Status Indicator & Drawer Toggle */}
          <div className="flex items-center gap-2.5">
            <a
              href="/multi-provider-ai-agent.zip"
              download="multi-provider-ai-agent.zip"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
              title="Unduh semua berkas dalam paket ZIP"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Unduh ZIP</span>
            </a>

            {onToggleDrawer && (
              <button
                onClick={onToggleDrawer}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  isDrawerOpen
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-zinc-900 text-zinc-300 border-zinc-800 hover:border-zinc-700 hover:text-zinc-100'
                }`}
                title="Buka / Tutup Drawer Gemini Copilot (Alt+C)"
              >
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span className="hidden sm:inline">Copilot Assistant</span>
              </button>
            )}

            <div className="flex items-center gap-2 text-xs text-zinc-400 bg-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-800 font-mono">
              <span className={`w-2 h-2 rounded-full ${systemHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="hidden sm:inline">Python 3.10:</span>
              <span className="text-zinc-200">Ready</span>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Bar */}
        <div className="flex md:hidden overflow-x-auto py-2 border-t border-zinc-800/60 gap-1.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-zinc-800 text-zinc-100 border border-zinc-700'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
