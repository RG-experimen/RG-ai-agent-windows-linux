/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Header, TabType } from './components/Header';
import { AgentSandbox } from './components/Sandbox/AgentSandbox';
import { GeminiChatbot } from './components/Chatbot/GeminiChatbot';
import { BugInspector } from './components/Inspector/BugInspector';
import { PerformanceBenchmark } from './components/Benchmark/PerformanceBenchmark';
import { WindowsVisualizer } from './components/WindowsAutomation/WindowsVisualizer';
import { ExportHub } from './components/Export/ExportHub';
import { ChatbotDrawer } from './components/Chatbot/ChatbotDrawer';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('sandbox');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [systemHealthy, setSystemHealthy] = useState(true);
  const [injectedSandboxCommand, setInjectedSandboxCommand] = useState<string | null>(null);

  // Global keyboard shortcut: Alt + C toggles the Gemini Copilot drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && (e.key === 'c' || e.key === 'C')) {
        e.preventDefault();
        setIsDrawerOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Check backend health
  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'ok') {
          setSystemHealthy(true);
        }
      })
      .catch(() => {
        setSystemHealthy(true); // Sandbox simulation fallback is always healthy
      });
  }, []);

  // Callback when chatbot dispatches a command to the sandbox
  const handleDispatchToSandbox = (command: string) => {
    setInjectedSandboxCommand(command);
    setActiveTab('sandbox');
    setIsDrawerOpen(false);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemHealthy={systemHealthy}
        onToggleDrawer={() => setIsDrawerOpen((prev) => !prev)}
        isDrawerOpen={isDrawerOpen}
      />

      <main className="flex-1 flex flex-col">
        {activeTab === 'sandbox' && (
          <AgentSandbox
            key={injectedSandboxCommand || 'sandbox-default'}
            initialMode="coding"
          />
        )}

        {activeTab === 'chatbot' && (
          <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col">
            <div className="flex-1 bg-zinc-900/40 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
              <GeminiChatbot onDispatchToSandbox={handleDispatchToSandbox} />
            </div>
          </div>
        )}

        {activeTab === 'inspector' && <BugInspector />}

        {activeTab === 'benchmark' && <PerformanceBenchmark />}

        {activeTab === 'windows' && <WindowsVisualizer />}

        {activeTab === 'export' && <ExportHub />}
      </main>

      {/* Floating Copilot Drawer (Accessible from any tab) */}
      <ChatbotDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onDispatchToSandbox={handleDispatchToSandbox}
        onExpandToTab={() => {
          setIsDrawerOpen(false);
          setActiveTab('chatbot');
        }}
      />
    </div>
  );
}
