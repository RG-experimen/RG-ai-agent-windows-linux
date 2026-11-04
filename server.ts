import express, { Request, Response } from 'express';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import { exec } from 'child_process';
import { GoogleGenAI } from '@google/genai';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;

  app.use(express.json({ limit: '10mb' }));

  // API: Health / System Check
  app.get('/api/health', (req: Request, res: Response) => {
    res.json({
      status: 'ok',
      hasGeminiKey: Boolean(process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY),
      nodeVersion: process.version,
      platform: process.platform,
    });
  });

  // API: Python Environment & Agent Verification
  app.get('/api/python/check', (req: Request, res: Response) => {
    exec('python3 agent.py --check', { cwd: __dirname }, (error, stdout, stderr) => {
      res.json({
        exitCode: error ? error.code : 0,
        stdout: stdout || '',
        stderr: stderr || '',
        success: !error,
      });
    });
  });

  // API: Get agent file contents
  app.get('/api/files/:filename', (req: Request, res: Response) => {
    const filename = req.params.filename;
    const allowed = ['agent.py', 'requirements.txt', 'run.sh', 'run.bat', 'README.md'];
    if (!allowed.includes(filename)) {
      return res.status(403).json({ error: 'File not permitted' });
    }
    const target = path.join(__dirname, filename);
    if (!fs.existsSync(target)) {
      return res.status(404).json({ error: 'File not found' });
    }
    const content = fs.readFileSync(target, 'utf-8');
    res.json({ filename, content });
  });

  // API: Live Gemini Agent Query (Server-side Gemini proxy using @google/genai)
  app.post('/api/agent/chat', async (req: Request, res: Response) => {
    try {
      const { prompt, mode, history, customApiKey } = req.body;
      const apiKey = customApiKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;

      if (!apiKey) {
        return res.status(400).json({
          error: 'No GEMINI_API_KEY found. You can enter an API key in the UI or use the built-in simulator.'
        });
      }

      const ai = new GoogleGenAI({ apiKey });

      let systemInstruction = `You are a helpful AI Agent in mode: ${mode || 'coding'}.
Return strictly a single valid JSON object with the format:
{
  "action": "chat" | "search_code" | "read_file" | "write_file" | "run_command" ${mode === 'windows' ? '| "mouse" | "keyboard" | "screenshot" | "window" | "open"' : ''},
  "parameters": { ... }
}
Do NOT return Markdown code fences or extra prose.`;

      const response = await ai.models.generateContent({
        model: 'gemini-3.8-flash',
        contents: [
          ...(history || []).map((h: any) => ({
            role: h.role === 'agent' ? 'model' : 'user',
            parts: [{ text: h.content }],
          })),
          { role: 'user', parts: [{ text: prompt }] },
        ],
        config: {
          systemInstruction,
          temperature: 0.2,
          responseMimeType: 'application/json',
        },
      });

      const text = response.text || '';
      res.json({ raw: text });
    } catch (err: any) {
      console.error('Agent chat error:', err);
      res.status(500).json({ error: err.message || 'Error processing request' });
    }
  });

  // API: Gemini Chatbot Assistant (Streaming SSE & Full Text)
  app.post('/api/chatbot/stream', async (req: Request, res: Response) => {
    try {
      const { messages, persona, customApiKey } = req.body;
      const apiKey = customApiKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;

      if (!apiKey) {
        return res.status(400).json({
          error: 'GEMINI_API_KEY is not configured. Please supply an API key.'
        });
      }

      const personaInstructions: Record<string, string> = {
        copilot: `You are the Gemini AI Copilot for the Multi-Provider AI Agent (v2.0).
You specialize in explaining agent operations, writing code, drafting action JSON payloads, and helping users run commands.
You have direct knowledge of the 3 modes: Coding Agent, Kali Linux Hacking Agent, and Windows Desktop Automation.
Whenever you suggest a command to run, format it clearly in a fenced bash or shell block like \`\`\`bash\\n<command>\\n\`\`\` so the user can click 'Run in Sandbox'.
Be concise, accurate, helpful, and insightful.`,

        security: `You are the Kali Linux Security & Ethical Hacking Advisor.
You specialize in network reconnaissance (nmap, masscan, whois, dig), vulnerability scanning (nikto, sqlmap, gobuster), traffic analysis (tcpdump, tshark), and offensive/defensive tradecraft.
Always emphasize ethical authorization and safe lab environments.
Whenever you provide penetration testing commands, explain each flag and format executable commands in code blocks with a short note.`,

        windows: `You are the Windows Desktop Automation & System Architect.
You specialize in pyautogui, pygetwindow, pyperclip, PowerShell scripting, and automating mouse/keyboard tasks.
Help users draft robust automation sequences, handle window focus locks, calculate screen regions, and manage clipboard operations cleanly.`,

        optimizer: `You are the Python Performance & Code Optimization Expert.
You specialize in profiling algorithms, replacing slow unpruned rglob file trees with in-place os.walk, managing memory buffers, fixing subprocess built-in bugs on Windows, and crafting resilient LLM tool dispatchers.
Explain algorithmic complexities, show before-and-after benchmarks, and provide clean, modern Python 3.10+ solutions.`,
      };

      const systemInstruction = personaInstructions[persona] || personaInstructions.copilot;
      const ai = new GoogleGenAI({ apiKey });

      // Set headers for Server-Sent Events (SSE)
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      const formattedContents = (messages || []).map((m: any) => ({
        role: m.role === 'assistant' || m.role === 'model' ? 'model' : 'user',
        parts: [{ text: m.content }],
      }));

      const stream = await ai.models.generateContentStream({
        model: 'gemini-3.8-flash',
        contents: formattedContents,
        config: {
          systemInstruction,
          temperature: 0.3,
        },
      });

      for await (const chunk of stream) {
        const chunkText = chunk.text || '';
        if (chunkText) {
          res.write(`data: ${JSON.stringify({ text: chunkText })}\n\n`);
        }
      }

      res.write(`data: [DONE]\n\n`);
      res.end();
    } catch (err: any) {
      console.error('Chatbot stream error:', err);
      if (!res.headersSent) {
        res.status(500).json({ error: err.message || 'Stream generation failed' });
      } else {
        res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
        res.end();
      }
    }
  });

  // Vite middleware in dev or static serving in production
  if (process.env.NODE_ENV === 'production') {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  } else {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
