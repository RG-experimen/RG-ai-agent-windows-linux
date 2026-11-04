# Implementation Plan: Gemini Chatbot & AI Copilot Integration

Integrate an interactive, full-stack Gemini Chatbot powered by `gemini-3.8-flash` via `@google/genai` into the **Multi-Provider AI Agent Studio**. The chatbot serves both as a dedicated conversational assistant and as a context-aware Agent Copilot capable of explaining code, analyzing security scans, optimizing Python automation scripts, and sending 1-click executable commands into the Agent Sandbox.

---

## 1. Objectives & User Journey

### Goals
- **Full-Stack Gemini Chatbot**: Connect real-time Gemini generation using server-side `@google/genai` with streaming text responses, markdown parsing, and code syntax highlighting.
- **Agent Copilot Integration**: Seamlessly bridge the chatbot with the existing three agent modes (**Coding**, **Kali Hacking**, and **Windows Desktop Automation**).
- **1-Click Command Dispatcher**: The chatbot can suggest terminal commands, shell scripts, or agent action JSON with a **"Run in Sandbox"** button that sends commands directly to the live Sandbox terminal.
- **Dual Accessibility**:
  1. Dedicated **"Gemini Chatbot"** tab in the main top navigation.
  2. Floating quick-access trigger with keyboard shortcut (`Alt + C`) accessible from any tab (Sandbox, Inspector, Benchmark).
- **Specialized Persona Presets**:
  - *Agent & Scripting Copilot*: Specializes in `agent.py` configuration, action schemas, and Python automation.
  - *Kali Security Testing Advisor*: Advises on ethical hacking tools, nmap flags, payloads, and defense mitigation.
  - *Windows Automation Architect*: Helps design `pyautogui` and `pygetwindow` automation workflows.
  - *Code Optimization & Refactoring*: Identifies bottlenecks, memory leaks, and regex improvements.

---

## 2. Architecture & Technical Design

### Backend (`server.ts`)
- Add a new streaming endpoint: `POST /api/chat/stream`
  - Uses `@google/genai` SDK with model `gemini-3.8-flash`.
  - Supports Server-Sent Events (SSE) / chunked transfer for smooth real-time token streaming.
  - System instructions tuned with contextual knowledge of the Multi-Provider Agent architecture (`agent.py`, `SYSTEM_PROMPT_CODING`, `SYSTEM_PROMPT_HACKING`, `SYSTEM_PROMPT_WINDOWS`).
  - Fallback error handling for rate limits or missing credentials.

### Frontend Components (`src/components/Chatbot/`)
- `GeminiChatbot.tsx`: Full-page view and drawer container with persona switcher, model indicator, and conversation history controls.
- `ChatbotDrawer.tsx`: Collapsible floating assistant drawer for quick consultation without leaving the Sandbox or Benchmark Lab.
- `MessageBubble.tsx`: Styled message component with markdown rendering, inline code blocks, copy-to-clipboard, and "Send to Sandbox" action buttons.
- `PersonaSelector.tsx`: Compact segmented selector for switching between agent copilot personas.

---

## 3. Step-by-Step Implementation Steps

### Phase A: Backend Endpoint
1. Update `server.ts` to implement `POST /api/chat/stream`:
   - Accept `{ messages, persona, context }`.
   - Configure dynamic system instructions based on persona.
   - Stream text chunks back to client using `res.write()`.

### Phase B: Frontend Chatbot UI
2. Create `src/components/Chatbot/GeminiChatbot.tsx`:
   - Interactive message stream with streaming typing indicator.
   - Model info badge (`gemini-3.8-flash · Active`).
   - Quick prompt starters (e.g., *"How do I run a multi-step nmap scan?"*, *"Write a pyautogui script to capture windows"*, *"Explain how the rglob bottleneck was fixed"*).
3. Update `src/components/Header.tsx`:
   - Add new **"Gemini Chatbot"** tab with Sparkles icon and "AI Live" badge.
4. Update `src/App.tsx`:
   - Wire up new `'chatbot'` tab and floating assistant drawer.
   - Pass callback `onDispatchToSandbox(command)` so chatbot suggestions can automatically switch tabs and execute in the live Agent Sandbox.

### Phase C: Polish & Verification
5. Verify build with `compile_applet`.
6. Test streaming response, persona switching, and 1-click sandbox execution.
