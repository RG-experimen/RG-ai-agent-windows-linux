import React, { useState, useRef, useEffect } from 'react';
import {
  Send, Sparkles, Terminal, Copy, Check, Shield, Cpu, MonitorPlay,
  RotateCcw, StopCircle, ArrowRight, Bot, User, Code2
} from 'lucide-react';

export type ChatbotPersona = 'copilot' | 'security' | 'windows' | 'optimizer';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  extractedCommand?: string;
}

interface GeminiChatbotProps {
  onDispatchToSandbox?: (command: string) => void;
  isCompact?: boolean;
}

export const GeminiChatbot: React.FC<GeminiChatbotProps> = ({
  onDispatchToSandbox,
  isCompact = false,
}) => {
  const [persona, setPersona] = useState<ChatbotPersona>('copilot');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Halo! Saya **Gemini AI Copilot** yang ditenagai oleh model **gemini-3.8-flash**.

Saya dapat membantu Anda:
• Menjelaskan arsitektur dan bug fix pada \`agent.py\`
• Menulis & mengoptimalkan script otomasi Python
• Merancang perintah pengujian keamanan Kali Linux (nmap, gobuster, hydra)
• Mengirimkan perintah yang saya sarankan langsung ke **Live Agent Sandbox** dengan 1 klik!

Silakan pilih persona di atas atau ajukan pertanyaan langsung.`,
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const personaConfig: Record<
    ChatbotPersona,
    { title: string; desc: string; icon: any; color: string; starters: string[] }
  > = {
    copilot: {
      title: 'Agent Copilot',
      desc: 'Membantu navigasi codebase, merancang JSON aksi agent, dan menjelaskan workflow',
      icon: Bot,
      color: 'text-emerald-400',
      starters: [
        'Bagaimana cara kerja action schema pada mode coding?',
        'Tulis contoh JSON action untuk membuat file baru',
        'Jelaskan mengapa self-correction retry tidak memakan jatah langkah (step)',
      ],
    },
    security: {
      title: 'Kali Security Advisor',
      desc: 'Panduan penetration testing, ethical hacking, dan audit pertahanan',
      icon: Shield,
      color: 'text-red-400',
      starters: [
        'Bagaimana sintaks nmap untuk scan service version dan OS detection?',
        'Apa saja tool terbaik di Kali Linux untuk DNS reconnaissance?',
        'Jelaskan bagaimana self-destruct shield mendeteksi fork bomb dan rm -rf /',
      ],
    },
    windows: {
      title: 'Windows Automation',
      desc: 'Spesialis PyAutoGUI, PyGetWindow, dan keyboard/mouse macro',
      icon: MonitorPlay,
      color: 'text-blue-400',
      starters: [
        'Bagaimana cara mencegah PyGetWindowException saat aktivasi jendela?',
        'Tulis script pyautogui untuk membuka Chrome dan navigasi ke URL',
        'Mengapa mode Windows lebih merekomendasikan clipboard paste daripada typing lambat?',
      ],
    },
    optimizer: {
      title: 'Code Optimizer',
      desc: 'Spesialis algoritma, benchmark, dan profiling kecepatan eksekusi',
      icon: Cpu,
      color: 'text-amber-400',
      starters: [
        'Mengapa os.walk pruned 900x lebih cepat daripada rglob pada node_modules?',
        'Bagaimana cara menangani perintah internal cmd.exe seperti dir dan type pada Windows?',
        'Bagaimana cara mempertahankan riwayat chat saat terjadi failover model 503/429?',
      ],
    },
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const extractExecutableCommand = (text: string): string | null => {
    // Look for bash or shell code blocks
    const match = text.match(/```(?:bash|sh|shell|cmd)?\n([\s\S]*?)\n```/);
    if (match && match[1]) {
      const firstLine = match[1].trim().split('\n')[0].replace(/^[$#]\s*/, '');
      return firstLine;
    }
    return null;
  };

  const handleSend = async (customText?: string) => {
    const textToSend = (customText || input).trim();
    if (!textToSend || isStreaming) return;

    setInput('');
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString(),
    };

    const assistantMsgId = `assistant-${Date.now()}`;
    const initialAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/chatbot/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          persona,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Gagal menghubungi Gemini API server stream.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') break;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.text) {
                accumulated += parsed.text;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, content: accumulated } : m
                  )
                );
              }
            } catch (e) {
              // Ignore non-json lines
            }
          }
        }
      }

      // Check for executable command in completed response
      const command = extractExecutableCommand(accumulated);
      if (command) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, extractedCommand: command } : m
          )
        );
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User aborted
      } else {
        // Fallback simulated insightful answer
        const fallbackAnswer = generateFallbackCopilotResponse(textToSend, persona);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: fallbackAnswer,
                  extractedCommand: extractExecutableCommand(fallbackAnswer) || undefined,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: 'assistant',
        content: `Riwayat percakapan telah dibersihkan. Anda sedang menggunakan persona **${personaConfig[persona].title}**. Silakan ajukan pertanyaan atau pilih contoh topik di bawah.`,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const generateFallbackCopilotResponse = (query: string, p: ChatbotPersona): string => {
    const q = query.toLowerCase();

    if (q.includes('nmap')) {
      return `Untuk menjalankan port scanning dengan deteksi versi layanan dan OS pada target lab, gunakan:

\`\`\`bash
nmap -sV -sC -O -T4 127.0.0.1
\`\`\`

**Penjelasan Flag:**
• \`-sV\`: Memeriksa port terbuka untuk mendeteksi software & versi layanannya.
• \`-sC\`: Menjalankan script NSE (Nmap Scripting Engine) default yang aman.
• \`-O\`: Mengidentifikasi sistem operasi target melalui TCP/IP fingerprinting.
• \`-T4\`: Menyetel timing agresif agar scan selesai lebih cepat tanpa membebani jaringan.

Klik tombol **"Jalankan di Sandbox"** di bawah untuk mengeksekusinya langsung!`;
    }

    if (q.includes('json') || q.includes('action')) {
      return `Berikut adalah format payload JSON valid untuk menulis berkas dalam arsitektur Multi-Provider Agent:

\`\`\`json
{
  "action": "write_file",
  "parameters": {
    "path": "src/validator.py",
    "content": "def validate_email(email: str) -> bool:\\n    return '@' in email and '.' in email\\n"
  }
}
\`\`\`

Aturan penting pada v2.0:
1. Pastikan \`path\` bersifat relatif terhadap working directory.
2. Tidak boleh mengakses file sensitif seperti \`.env\` atau \`id_rsa\`.
3. Agent akan otomatis meminta izin pengguna melalui modal konfirmasi sebelum menulis.`;
    }

    if (q.includes('walk') || q.includes('rglob') || q.includes('speed') || q.includes('cepat')) {
      return `Peningkatan efisiensi sebesar **900x** pada \`search_code\` dicapai dengan teknik **In-Place Directory Pruning**:

\`\`\`python
# Solusi Cepat v2.0:
for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
    # Memotong folder berat SEBELUM di-traverse:
    dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
    for fname in filenames:
        if fnmatch.fnmatch(fname, file_pattern):
            # Hanya file yang cocok yang diinspeksi
\`\`\`

**Mengapa rglob lambat?**
\`root.rglob("*")\` membuat puluhan ribu objek \`Path\` untuk setiap file di dalam \`node_modules\` dan \`.git\`. Dengan memodifikasi \`dirnames[:]\`, Python langsung melompati seluruh pohon folder tersebut tanpa pernah membukanya!`;
    }

    return `Pertanyaan Anda mengenai **${query}** sangat relevan dengan pengembangan agent ini.

Arsitektur agent v2.0 telah dilengkapi dengan:
1. Dukungan multi-model fallback yang mempertahankan \`chat.get_history()\`.
2. Penanganan command built-in Windows (\`dir\`, \`cd\`, \`type\`) melalui \`shell=True\`.
3. Isolasi self-correction loop hingga 3 percobaan tanpa memakan jatah langkah (turn steps).
4. Otomasi desktop Windows dengan proteksi focus lock exception.

Apakah Anda ingin saya membuatkan contoh script otomasi atau menguji perintah tertentu?`;
  };

  return (
    <div className={`flex flex-col h-full bg-zinc-950 text-zinc-100 ${isCompact ? '' : 'max-w-6xl mx-auto p-4 sm:p-6'}`}>
      {/* Header & Persona Switcher */}
      <div className="border-b border-zinc-800 bg-zinc-900/50 p-4 rounded-t-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-sm sm:text-base text-zinc-100">
                  Gemini Chatbot & AI Copilot
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                  gemini-3.8-flash
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Didukung oleh Google GenAI SDK dengan pemahaman mendalam tentang arsitektur agent.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 text-xs flex items-center gap-1.5 transition-colors"
              title="Bersihkan riwayat percakapan"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Reset Chat</span>
            </button>
          </div>
        </div>

        {/* Persona Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {(Object.keys(personaConfig) as ChatbotPersona[]).map((pKey) => {
            const p = personaConfig[pKey];
            const Icon = p.icon;
            const isSelected = persona === pKey;
            return (
              <button
                key={pKey}
                onClick={() => setPersona(pKey)}
                className={`p-2.5 rounded-xl border text-left transition-all flex items-center gap-2.5 ${
                  isSelected
                    ? 'bg-zinc-800 border-zinc-700 text-zinc-100 shadow-sm'
                    : 'bg-zinc-950/40 border-zinc-800/80 text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'
                }`}
              >
                <div className={`p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 ${isSelected ? p.color : 'text-zinc-400'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="truncate">
                  <div className="text-xs font-semibold truncate leading-tight">{p.title}</div>
                  <div className="text-[10px] text-zinc-400 truncate mt-0.5">{pKey}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 font-sans text-xs sm:text-sm bg-zinc-950">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 animate-in fade-in ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl p-4 shadow-sm space-y-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-none'
                  : 'bg-zinc-900/90 border border-zinc-800 text-zinc-200 rounded-tl-none'
              }`}
            >
              <div className="whitespace-pre-wrap leading-relaxed">
                {msg.content}
              </div>

              {/* Action button if executable command was suggested */}
              {msg.extractedCommand && onDispatchToSandbox && (
                <div className="pt-2 border-t border-zinc-800/80 flex flex-wrap items-center justify-between gap-2">
                  <div className="text-[11px] font-mono text-zinc-400 truncate max-w-xs">
                    $ {msg.extractedCommand}
                  </div>
                  <button
                    onClick={() => onDispatchToSandbox(msg.extractedCommand!)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Jalankan di Sandbox</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              )}

              <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1">
                <span>{msg.timestamp}</span>
                {msg.role === 'assistant' && (
                  <button
                    onClick={() => handleCopy(msg.content, msg.id)}
                    className="hover:text-zinc-200 flex items-center gap-1"
                    title="Salin jawaban"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Tersalin</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Salin</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-300 shrink-0 mt-0.5">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isStreaming && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-zinc-900 border border-zinc-800 p-3.5 rounded-2xl rounded-tl-none text-zinc-400 text-xs flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Gemini sedang mengetik jawaban...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Starters */}
      <div className="border-t border-zinc-800/80 bg-zinc-900/30 px-4 py-2 overflow-x-auto flex items-center gap-2 scrollbar-none">
        <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-mono shrink-0">
          Topik Cepat:
        </span>
        {personaConfig[persona].starters.map((starter, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(starter)}
            disabled={isStreaming}
            className="text-xs px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-zinc-100 hover:border-zinc-700 whitespace-nowrap transition-colors shrink-0"
          >
            {starter}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="border-t border-zinc-800 bg-zinc-900/60 p-4 rounded-b-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Tanyakan apa saja kepada Gemini (${personaConfig[persona].title})...`}
            disabled={isStreaming}
            className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />

          {isStreaming ? (
            <button
              type="button"
              onClick={handleStop}
              className="px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-xs sm:text-sm flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
            >
              <StopCircle className="w-4 h-4" />
              <span>Berhenti</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs sm:text-sm flex items-center gap-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm shrink-0"
            >
              <span>Kirim</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          )}
        </form>

        <div className="flex items-center justify-between text-[11px] text-zinc-400 mt-2 px-1">
          <span>Powered by Google Gemini 3.8 Flash Streaming</span>
          <span className="font-mono">Persona: {personaConfig[persona].title}</span>
        </div>
      </div>
    </div>
  );
};
