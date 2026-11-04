export type AgentMode = 'coding' | 'hacking' | 'windows';

export type AIProvider = 'gemini' | 'openai' | 'deepseek' | 'grok' | 'meta' | 'claude';

export interface ProviderInfo {
  id: AIProvider;
  name: string;
  defaultModel: string;
  supportsVision: boolean;
  envVar: string;
  keyUrl: string;
}

export interface AgentAction {
  action: 'chat' | 'search_code' | 'read_file' | 'write_file' | 'run_command' | 'screenshot' | 'mouse' | 'keyboard' | 'window' | 'open';
  parameters: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system' | 'action' | 'permission' | 'error';
  content: string;
  timestamp: string;
  actionDetails?: AgentAction;
  commandOutput?: {
    exitCode: number;
    stdout?: string;
    stderr?: string;
  };
  screenshotPath?: string;
}

export interface VirtualFile {
  path: string;
  content: string;
  size: number;
  lastModified: string;
}

export interface BugItem {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium';
  category: 'Runtime Crash' | 'API Quota & Tokens' | 'Context Loss' | 'Performance' | 'Robustness';
  symptom: string;
  rootCause: string;
  fixExplanation: string;
  originalSnippet: string;
  fixedSnippet: string;
}
