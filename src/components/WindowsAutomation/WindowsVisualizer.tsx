import React, { useState } from 'react';
import {
  MonitorPlay, MousePointer, Keyboard, AppWindow, Camera, Play,
  Copy, CheckCircle2, RefreshCw, Terminal, Layers
} from 'lucide-react';

export const WindowsVisualizer: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: 520, y: 340 });
  const [clickRipples, setClickRipples] = useState<Array<{ id: number; x: number; y: number }>>([]);
  const [activeWindow, setActiveWindow] = useState<'vscode' | 'notepad' | 'terminal' | 'chrome'>('vscode');
  const [windowStates, setWindowStates] = useState({
    vscode: { minimized: false, maximized: false },
    notepad: { minimized: false, maximized: false },
    terminal: { minimized: false, maximized: false },
    chrome: { minimized: true, maximized: false },
  });
  const [editorText, setEditorText] = useState(
    `# VS Code - sample_automation.py\nimport pyautogui\nimport time\n\nprint("Windows Mode Automation Active")\n# Agent types via clipboard paste for speed & reliability\n`
  );
  const [keyboardStream, setKeyboardStream] = useState<string[]>([
    'hotkey: ctrl + n',
    'paste: # VS Code - sample_automation.py',
    'hotkey: ctrl + s',
  ]);
  const [screenshots, setScreenshots] = useState<string[]>([
    'screen_20261104_102812.png',
  ]);

  const triggerClick = (x: number, y: number) => {
    setMousePos({ x, y });
    const newRipple = { id: Date.now(), x, y };
    setClickRipples((prev) => [...prev, newRipple]);
    setTimeout(() => {
      setClickRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
    }, 600);
  };

  const simulateOpenApp = (app: 'vscode' | 'notepad' | 'terminal' | 'chrome') => {
    setActiveWindow(app);
    setWindowStates((prev) => ({
      ...prev,
      [app]: { minimized: false, maximized: false },
    }));
    setKeyboardStream((prev) => [`open: ${app}`, ...prev.slice(0, 5)]);
    triggerClick(450, 280);
  };

  const simulateTypePaste = () => {
    const snippet = `\n# Added by agent\ndef auto_task():\n    print("Task completed")\n`;
    setEditorText((prev) => prev + snippet);
    setKeyboardStream((prev) => [
      'paste: def auto_task()... via pyperclip',
      'press: enter',
      ...prev.slice(0, 5),
    ]);
    triggerClick(600, 360);
  };

  const simulateScreenshot = () => {
    const filename = `screen_${new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15)}.png`;
    setScreenshots((prev) => [filename, ...prev]);
    setKeyboardStream((prev) => [`screenshot -> ${filename}`, ...prev.slice(0, 5)]);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Visualizer Header */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
          <div>
            <div className="flex items-center gap-2">
              <MonitorPlay className="w-6 h-6 text-blue-400" />
              <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
                Simulator Otomasi Desktop Windows
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1">
              Visualisasi waktu-nyata pergerakan kursor mouse, ketikan keyboard via clipboard, pengelolaan jendela PyGetWindow, dan loop verifikasi tangkapan layar.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <div className="bg-blue-500/10 border border-blue-500/20 text-blue-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5">
              <MousePointer className="w-3.5 h-3.5 text-blue-400" />
              <span>X: {mousePos.x}, Y: {mousePos.y}</span>
            </div>
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-3 py-1.5 rounded-lg">
              <span>FAILSAFE: Pojok Kiri-Atas</span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2 pb-2">
          <button
            onClick={() => simulateOpenApp('vscode')}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1.5 border border-zinc-700 transition-colors shadow-sm"
          >
            <AppWindow className="w-3.5 h-3.5 text-blue-400" />
            <span>Buka VS Code</span>
          </button>
          <button
            onClick={() => simulateOpenApp('notepad')}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1.5 border border-zinc-700 transition-colors shadow-sm"
          >
            <AppWindow className="w-3.5 h-3.5 text-amber-400" />
            <span>Buka Notepad</span>
          </button>
          <button
            onClick={simulateTypePaste}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1.5 border border-zinc-700 transition-colors shadow-sm"
          >
            <Keyboard className="w-3.5 h-3.5 text-emerald-400" />
            <span>Ketik Kode (Paste)</span>
          </button>
          <button
            onClick={simulateScreenshot}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1.5 border border-zinc-700 transition-colors shadow-sm"
          >
            <Camera className="w-3.5 h-3.5 text-purple-400" />
            <span>Ambil Screenshot</span>
          </button>
        </div>

        {/* Virtual Desktop Canvas */}
        <div className="relative w-full h-[420px] bg-slate-950 rounded-xl border border-zinc-800 overflow-hidden shadow-2xl flex flex-col select-none">
          {/* Simulated Windows Desktop Wallpaper / Taskbar */}
          <div className="flex-1 relative p-4 overflow-hidden bg-gradient-to-br from-slate-950 via-zinc-950 to-blue-950/30">
            {/* Active Window: VS Code or Notepad */}
            <div
              className={`absolute top-6 left-10 w-[85%] max-w-2xl h-[300px] bg-zinc-900 border border-zinc-700/80 rounded-xl shadow-2xl flex flex-col transition-all duration-300 ${
                activeWindow === 'vscode' ? 'z-20 scale-100 ring-1 ring-blue-500/40' : 'z-10 opacity-70 scale-95'
              }`}
              onClick={() => setActiveWindow('vscode')}
            >
              <div className="h-8 bg-zinc-950/80 px-3 border-b border-zinc-800 flex items-center justify-between text-xs font-mono text-zinc-300">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                  <span className="font-semibold text-zinc-200">Visual Studio Code — sample_automation.py</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-zinc-700 inline-block" />
                  <span className="w-3 h-3 rounded-sm bg-zinc-700 inline-block" />
                  <span className="w-3 h-3 rounded-sm bg-red-500/80 inline-block" />
                </div>
              </div>
              <div className="flex-1 p-3 font-mono text-xs text-blue-200/90 bg-zinc-950 overflow-y-auto whitespace-pre leading-relaxed">
                {editorText}
              </div>
            </div>

            {/* Background Secondary Window: Notepad */}
            <div
              className={`absolute top-16 right-10 w-[70%] max-w-md h-[220px] bg-zinc-900 border border-zinc-700/80 rounded-xl shadow-xl flex flex-col transition-all duration-300 ${
                activeWindow === 'notepad' ? 'z-20 scale-100 ring-1 ring-amber-500/40' : 'z-10 opacity-60 scale-95'
              }`}
              onClick={() => setActiveWindow('notepad')}
            >
              <div className="h-8 bg-zinc-950/80 px-3 border-b border-zinc-800 flex items-center justify-between text-xs font-mono text-zinc-300">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <span className="font-semibold text-zinc-200">Notepad — Untitled.txt</span>
                </div>
              </div>
              <div className="flex-1 p-3 font-mono text-xs text-zinc-300 bg-zinc-950">
                Halo dunia! Catatan dibuat oleh otomasi agent PyAutoGUI.
              </div>
            </div>

            {/* Virtual Mouse Pointer */}
            <div
              className="absolute z-50 pointer-events-none transition-all duration-300 ease-out flex items-center gap-1"
              style={{ left: `${mousePos.x}px`, top: `${mousePos.y}px` }}
            >
              <MousePointer className="w-5 h-5 text-emerald-400 fill-emerald-400 drop-shadow-md" />
              <span className="text-[9px] bg-black/80 px-1.5 py-0.5 rounded text-emerald-300 font-mono">
                ({mousePos.x}, {mousePos.y})
              </span>
            </div>

            {/* Click Ripple Effects */}
            {clickRipples.map((ripple) => (
              <div
                key={ripple.id}
                className="absolute w-8 h-8 rounded-full border-2 border-emerald-400 -translate-x-1/2 -translate-y-1/2 pointer-events-none animate-ping"
                style={{ left: `${ripple.x}px`, top: `${ripple.y}px` }}
              />
            ))}
          </div>

          {/* Windows Taskbar */}
          <div className="h-10 bg-zinc-950/90 border-t border-zinc-800 px-4 flex items-center justify-between z-30">
            <div className="flex items-center gap-2">
              <button className="p-1 rounded hover:bg-zinc-800 text-blue-400">
                <Layers className="w-4 h-4" />
              </button>
              <button
                onClick={() => simulateOpenApp('vscode')}
                className={`px-2.5 py-1 rounded text-xs font-mono flex items-center gap-1.5 ${
                  activeWindow === 'vscode' ? 'bg-zinc-800 text-blue-300 border border-zinc-700' : 'text-zinc-400'
                }`}
              >
                <AppWindow className="w-3.5 h-3.5 text-blue-400" />
                <span>Code</span>
              </button>
              <button
                onClick={() => simulateOpenApp('notepad')}
                className={`px-2.5 py-1 rounded text-xs font-mono flex items-center gap-1.5 ${
                  activeWindow === 'notepad' ? 'bg-zinc-800 text-amber-300 border border-zinc-700' : 'text-zinc-400'
                }`}
              >
                <AppWindow className="w-3.5 h-3.5 text-amber-400" />
                <span>Notepad</span>
              </button>
            </div>
            <div className="text-[11px] font-mono text-zinc-400">
              {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Automation Logs & Screenshots Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Action Stream Log */}
          <div className="bg-zinc-950 rounded-xl border border-zinc-800 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-300 font-mono">
              <span className="flex items-center gap-1.5">
                <Keyboard className="w-4 h-4 text-emerald-400" />
                Aliran Aksi Keyboard / Mouse
              </span>
              <span className="text-[10px] text-zinc-500">Live Queue</span>
            </div>
            <div className="space-y-1 font-mono text-xs text-zinc-400 max-h-36 overflow-y-auto">
              {keyboardStream.map((k, idx) => (
                <div key={idx} className="bg-zinc-900/60 px-2.5 py-1.5 rounded flex items-center justify-between">
                  <span>{k}</span>
                  <span className="text-[10px] text-emerald-400">OK</span>
                </div>
              ))}
            </div>
          </div>

          {/* Screenshot History */}
          <div className="bg-zinc-950 rounded-xl border border-zinc-800 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-zinc-300 font-mono">
              <span className="flex items-center gap-1.5">
                <Camera className="w-4 h-4 text-purple-400" />
                Daftar Tangkapan Layar (Vision Loop)
              </span>
              <span className="text-[10px] text-zinc-500">{screenshots.length} Foto</span>
            </div>
            <div className="space-y-1 font-mono text-xs text-zinc-400 max-h-36 overflow-y-auto">
              {screenshots.map((s, idx) => (
                <div key={idx} className="bg-zinc-900/60 px-2.5 py-1.5 rounded flex items-center justify-between">
                  <span className="text-zinc-300">{s}</span>
                  <span className="text-[10px] text-purple-400 font-medium">1920x1080</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
