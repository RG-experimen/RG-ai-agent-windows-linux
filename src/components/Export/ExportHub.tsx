import React, { useState, useEffect } from 'react';
import {
  Download, Copy, Check, FileCode, Terminal, Shield, ExternalLink,
  CheckCircle2, FolderDown, Laptop, Monitor, Sparkles
} from 'lucide-react';

export const ExportHub: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string>('agent.py');
  const [fileContent, setFileContent] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  const files = [
    { name: 'agent.py', desc: 'Script Python utama (Production-Ready, Fixed & Optimized)', size: '36 KB' },
    { name: 'requirements.txt', desc: 'Daftar pustaka dependensi (Google GenAI, OpenAI, PyAutoGUI)', size: '480 B' },
    { name: 'run.sh', desc: 'Script peluncur 1-klik untuk Linux / Kali / macOS', size: '420 B' },
    { name: 'run.bat', desc: 'Script peluncur 1-klik untuk Windows', size: '480 B' },
    { name: 'README.md', desc: 'Dokumentasi lengkap panduan & analisis perbaikan bug', size: '4.2 KB' },
  ];

  useEffect(() => {
    fetchFile(selectedFile);
  }, [selectedFile]);

  const fetchFile = async (filename: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/files/${filename}`);
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content || '');
      } else {
        setFileContent('# File dapat diakses langsung di repository workspace root.');
      }
    } catch {
      setFileContent('# File dapat diakses langsung di repository workspace root.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
          <div>
            <div className="flex items-center gap-2">
              <FolderDown className="w-6 h-6 text-emerald-400" />
              <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
                Paket Ekspor & Setup Aplikasi Python Siap Pakai
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1">
              Seluruh berkas aplikasi yang telah diperbaiki, diuji, dan dioptimasi telah dikemas ke dalam satu folder <code className="text-emerald-400 font-mono">multi-provider-ai-agent/</code> dan di-compress menjadi berkas ZIP siap unduh.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <a
              href="/multi-provider-ai-agent.zip"
              download="multi-provider-ai-agent.zip"
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs sm:text-sm flex items-center gap-2 transition-all shadow-md hover:shadow-emerald-500/20 shrink-0"
            >
              <FolderDown className="w-4 h-4" />
              <span>Unduh Paket Lengkap (.ZIP)</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-700/60 text-emerald-100">
                26 KB
              </span>
            </a>

            <button
              onClick={() => handleDownload(selectedFile, fileContent)}
              className="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium text-xs sm:text-sm flex items-center gap-2 transition-colors border border-zinc-700 shrink-0"
            >
              <Download className="w-4 h-4" />
              <span>Unduh {selectedFile}</span>
            </button>
          </div>
        </div>

        {/* Zip Content Summary Banner */}
        <div className="bg-emerald-950/20 border border-emerald-900/40 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shrink-0">
              <FolderDown className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-emerald-300">
                Arsip ZIP: multi-provider-ai-agent.zip (6 Berkas Utama)
              </div>
              <div className="text-zinc-400 text-[11px] mt-0.5 font-mono">
                multi-provider-ai-agent/ [ agent.py · requirements.txt · run.sh · run.bat · README.md · .env.example ]
              </div>
            </div>
          </div>

          <a
            href="/api/download/zip"
            download="multi-provider-ai-agent.zip"
            className="text-xs text-emerald-400 hover:text-emerald-300 underline underline-offset-4 flex items-center gap-1 shrink-0 font-medium"
          >
            <span>Direct Mirror Link</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Quick OS Instructions Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-2">
            <div className="flex items-center gap-2 font-semibold text-xs text-zinc-200">
              <Monitor className="w-4 h-4 text-blue-400" />
              <span>Windows 10 / 11</span>
            </div>
            <div className="bg-black/60 p-2.5 rounded-lg font-mono text-[11px] text-zinc-300 overflow-x-auto space-y-1">
              <div>pip install -r requirements.txt</div>
              <div>set GEMINI_API_KEY=your_key</div>
              <div>python agent.py --windows</div>
            </div>
            <span className="text-[10px] text-zinc-400 block">Dukungan penuh PyAutoGUI & PyGetWindow.</span>
          </div>

          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-2">
            <div className="flex items-center gap-2 font-semibold text-xs text-zinc-200">
              <Shield className="w-4 h-4 text-red-400" />
              <span>Kali Linux / Debian</span>
            </div>
            <div className="bg-black/60 p-2.5 rounded-lg font-mono text-[11px] text-zinc-300 overflow-x-auto space-y-1">
              <div>sudo apt install python3-tk scrot</div>
              <div>pip install -r requirements.txt</div>
              <div>python3 agent.py --hacking</div>
            </div>
            <span className="text-[10px] text-zinc-400 block">Full shell access dengan double-confirmation shield.</span>
          </div>

          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-2">
            <div className="flex items-center gap-2 font-semibold text-xs text-zinc-200">
              <Laptop className="w-4 h-4 text-emerald-400" />
              <span>macOS / Umum</span>
            </div>
            <div className="bg-black/60 p-2.5 rounded-lg font-mono text-[11px] text-zinc-300 overflow-x-auto space-y-1">
              <div>pip install -r requirements.txt</div>
              <div>export GEMINI_API_KEY=your_key</div>
              <div>python3 agent.py --coding</div>
            </div>
            <span className="text-[10px] text-zinc-400 block">Pruned os.walk super cepat untuk developer tools.</span>
          </div>
        </div>

        {/* File Tabs & Code Preview */}
        <div className="space-y-3 pt-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              {files.map((f) => (
                <button
                  key={f.name}
                  onClick={() => setSelectedFile(f.name)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono flex items-center gap-2 transition-colors ${
                    selectedFile === f.name
                      ? 'bg-zinc-800 text-emerald-400 border border-zinc-700 shadow-sm font-semibold'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>{f.name}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono flex items-center gap-1.5 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Tersalin!' : 'Salin Kode'}</span>
              </button>
            </div>
          </div>

          {/* Code Viewer */}
          <div className="relative rounded-xl border border-zinc-800 bg-black/90 p-4 font-mono text-xs overflow-x-auto max-h-[500px]">
            {loading ? (
              <div className="text-zinc-400 p-8 text-center">Memuat berkas...</div>
            ) : (
              <pre className="text-zinc-200 whitespace-pre leading-relaxed">{fileContent}</pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
