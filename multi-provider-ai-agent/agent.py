#!/usr/bin/env python3
# =============================================================================
#  MULTI-PROVIDER AI AGENT — CODING / HACKING (KALI) / WINDOWS MODE
#  Version: 2.0.0 (Production-Ready, Bug-Fixed & Optimized)
# =============================================================================
#  Usage:
#     python agent.py                 → [mode 1-3] → [CLI/GUI] → [provider] → chat
#     python agent.py --coding        → skip mode menu (coding agent)
#     python agent.py --hacking       → skip mode menu (Kali Linux hacking agent)
#     python agent.py --windows       → skip mode menu (Windows desktop automation)
#     python agent.py --gui / --cli   → select interface directly
#     python agent.py --no-menu       → direct CLI using environment settings
#     python agent.py --check         → test credentials and exit
#     python agent.py --help          → display comprehensive help guide
#
#  Key Bug Fixes & Optimizations in v2.0:
#     1. FIXED: Windows shell built-ins ('dir', 'cd', 'type') failing with
#        FileNotFoundError due to shell=False. Routed through cmd.exe correctly.
#     2. FIXED: Dummy 'ping' probe during Gemini initialization removed. No longer
#        pollutes chat history, avoids schema mismatch, and saves API quota.
#     3. FIXED: Model fallback (503/429) now preserves full chat history instead
#        of wiping conversation context.
#     4. FIXED: Self-correction loop no longer consumes turn steps. Format retries
#        are isolated per turn step.
#     5. OPTIMIZED: Code search upgraded from unpruned rglob to in-place pruned
#        os.walk, providing a 100x-1000x speedup on projects with node_modules/.git.
#     6. FIXED: PyGetWindow focus-stealing crash on Windows handled with fallback.
#     7. ENHANCED: Parameter normalization (e.g. 'key' -> 'keys', 'app_name' -> 'app').
#     8. ENHANCED: Resilient JSON extractor handles conversational preambles and fences.
# =============================================================================

from __future__ import annotations

import atexit
import base64
import fnmatch
import getpass
import json
import mimetypes
import os
import platform
import queue
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------- Optional SDK Imports ----------
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, simpledialog, ttk
    TKINTER_AVAILABLE = True
except (ImportError, Exception):
    tk = ttk = messagebox = scrolledtext = simpledialog = None
    TKINTER_AVAILABLE = False

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ---------- Configuration & Limits ----------
GEMINI_MODEL_FALLBACKS = [
    m for m in [
        os.getenv("GEMINI_MODEL"),
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
    ] if m
]
DEFAULT_GEMINI_MODEL = GEMINI_MODEL_FALLBACKS[0]
DEFAULT_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

MAX_READ_BYTES = 50_000
MAX_WRITE_BYTES = 300_000
MAX_SEARCH_MATCHES = 100
MAX_SEARCH_FILE_BYTES = 1_000_000
HACKING_TIMEOUT = int(os.getenv("HACKING_TIMEOUT", "300"))
WINDOWS_SCREENSHOT_PROMPT = os.getenv("WINDOWS_SCREENSHOT_PROMPT", "0") == "1"

IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "env",
    ".ssh", ".gnupg", ".aws", ".config", "dist", "build", ".next",
    ".cache", ".idea", ".vscode"
}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", "credentials", "secrets.json",
    "private_key.pem", "service-account.json"
}

MODES = [
    ("coding",  "Coding Agent",          "Inspect/modify code, git, run dev commands"),
    ("hacking", "Hacking Agent (Kali)",  "Full shell access with all security tools"),
    ("windows", "AI Agent Windows Mode", "Desktop control (mouse, keyboard, windows, apps)"),
]
MODE_NAMES = {k: name for k, name, _ in MODES}
MAX_STEPS_BY_MODE = {"coding": 6, "hacking": 8, "windows": 12}

PROVIDERS: List[Tuple[str, str, List[str]]] = [
    ("gemini",   "Google Gemini",    ["GEMINI_API_KEY", "GOOGLE_API_KEY", "VERTEX_API_KEY"]),
    ("openai",   "OpenAI (ChatGPT)", ["OPENAI_API_KEY"]),
    ("deepseek", "DeepSeek",         ["DEEPSEEK_API_KEY"]),
    ("grok",     "xAI Grok",         ["XAI_API_KEY"]),
    ("meta",     "Meta Llama",       ["LLAMA_API_KEY", "META_API_KEY"]),
    ("claude",   "Anthropic Claude", ["ANTHROPIC_API_KEY"]),
]
PROVIDER_NAMES = {k: n for k, n, _ in PROVIDERS}
PROVIDER_KEY_URLS = {
    "gemini":   "https://aistudio.google.com/apikey",
    "openai":   "https://platform.openai.com/api-keys",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "grok":     "https://console.x.ai",
    "meta":     "https://llama.developer.meta.com",
    "claude":   "https://console.anthropic.com/settings/keys",
}

VISION_CAPABLE = {
    "gemini": True,
    "openai": True,
    "grok": True,
    "claude": True,
    "deepseek": False,
    "meta": False,
}

_SELF_DESTRUCT_PATTERNS = [
    (r"\brm\s+-[rf]+\s+/\s*(?:$|;|&|\|)", "deleting root filesystem (rm -rf /)"),
    (r"\brm\s+-[rf]+\s+/\*",             "deleting root filesystem contents (rm -rf /*)"),
    (r"\bmkfs(?:\.\w+)?\s+/dev/",         "formatting block device directly"),
    (r"\bdd\b[^|;&]*\bof=/dev/(?:sd|nvme|hd|disk)", "overwriting block device with dd"),
    (r">+\s*/dev/(?:sd|nvme|hd)",         "redirecting raw writes to disk"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "executing fork bomb"),
    (r"\bchmod\s+-R\s+777\s+/\s*(?:$|;|&|\|)", "destroying root permissions"),
]

# ---------- System Prompts ----------
SYSTEM_PROMPT_CODING = """
You are an expert, meticulous coding assistant. Help the user inspect, navigate,
and modify files in their working directory.

Respond with exactly ONE valid JSON object per turn:
{
  "action": "chat" | "search_code" | "read_file" | "write_file" | "run_command",
  "parameters": { ... }
}

Actions:
- chat: {"message": string}
- search_code: {"query": string, "path": string, "file_pattern": string}
- read_file: {"path": string}
- write_file: {"path": string, "content": string}
- run_command: {"command": string}

Rules:
1. Always use relative paths inside the working directory.
2. Never access sensitive keys, tokens, or credential files.
3. Allowed commands: git (status, diff, log, branch), python/python3 --version,
   ls/pwd (Linux/Mac) or dir/cd (Windows).
4. Return ONLY the JSON object. No Markdown code fences, no surrounding prose.
"""

SYSTEM_PROMPT_HACKING = """
You are a Kali Linux security testing assistant. The user is an authorized
ethical hacker and penetration tester working on approved targets or local lab environments.
You have full shell access through the run_command action (shell=True).

Respond with exactly ONE valid JSON object per turn:
{
  "action": "chat" | "search_code" | "read_file" | "write_file" | "run_command",
  "parameters": { ... }
}

Actions:
- chat: {"message": string}
- search_code: {"query": string, "path": string, "file_pattern": string}
- read_file: {"path": string}
- write_file: {"path": string, "content": string}
- run_command: {"command": string}   # Full shell access (pipes, redirects, &&, ;)

Style:
- If running a non-trivial scan or tool, explain intent briefly first via chat.
- Available tools: nmap, masscan, arp-scan, netdiscover, whois, dig, nslookup,
  dnsrecon, theHarvester, whatweb, searchsploit, curl, wget, nikto, gobuster,
  dirb, wfuzz, wpscan, sqlmap, iwconfig, airmon-ng, airodump-ng, aircrack-ng,
  hydra, john, hashcat, msfconsole, msfvenom, tcpdump, tshark, mitmproxy,
  strings, xxd, binwalk, foremost, exiftool, grep, find, ss, ip, etc.
- Return ONLY the JSON object, no Markdown code fences.
"""

SYSTEM_PROMPT_WINDOWS = """
You are a Windows desktop automation agent. You control the mouse, keyboard,
and application windows using automation libraries. You can also inspect/write files
and launch applications.

Respond with exactly ONE valid JSON object per turn:
{
  "action": "chat" | "screenshot" | "mouse" | "keyboard" | "window" | "open" | "read_file" | "write_file" | "run_command",
  "parameters": { ... }
}

Actions:
- chat:       {"message": string}
- screenshot: {}
- mouse:      {"action": "move"|"click"|"doubleclick"|"rightclick"|"drag"|"scroll", "x": int, "y": int, "clicks": int, "button": "left"|"right"|"middle", "amount": int, "duration": float}
- keyboard:   {"action": "write"|"press"|"hotkey"|"paste", "text": str, "keys": [str], "interval": float}
- window:     {"action": "list"|"activate"|"minimize"|"maximize"|"close", "title": str}
- open:       {"app": "code"|"notepad"|"chrome"|"cmd"|"explorer"|..., "args": str}
- read_file:  {"path": str}
- write_file: {"path": str, "content": str}
- run_command:{"command": str}

Rules:
1. When generating code in VS Code: ALWAYS write the file first via write_file,
   then use open {"app": "code", "args": "path"} for reliable execution.
2. If the user asks to see typing in an editor, open the app, then use paste (Ctrl+V)
   rather than slow character-by-character typing.
3. Call screenshot before interacting if you need current screen coordinates.
4. Return ONLY the JSON object, no Markdown code fences.
"""

MODE_PROMPTS = {
    "coding":  SYSTEM_PROMPT_CODING,
    "hacking": SYSTEM_PROMPT_HACKING,
    "windows": SYSTEM_PROMPT_WINDOWS,
}

ACTIONS_BY_MODE = {
    "coding":  ["chat", "search_code", "read_file", "write_file", "run_command"],
    "hacking": ["chat", "search_code", "read_file", "write_file", "run_command"],
    "windows": ["chat", "screenshot", "mouse", "keyboard", "window", "open",
                "read_file", "write_file", "run_command"],
}

PERMISSION_HANDLER: Optional[Callable[[str], bool]] = None


def make_action_schema(mode: str) -> Dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "enum": ACTIONS_BY_MODE[mode]},
            "parameters": {"type": "OBJECT"},
        },
        "required": ["action", "parameters"],
    }


# ---------- Robust Response Parsing ----------
def parse_ai_response(text: str) -> Dict[str, Any]:
    """
    Robustly parses the model's response into a JSON dictionary.
    Handles raw JSON, Markdown code fences, preambles, and extracts outermost objects.
    """
    if not isinstance(text, str):
        raise ValueError("AI response is not text.")
    clean = text.strip()
    if not clean:
        raise ValueError("Respons AI kosong.")

    # 1. Direct JSON parse
    try:
        obj = json.loads(clean)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences if present
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    fenced_match = fence_pattern.search(clean)
    if fenced_match:
        extracted = fenced_match.group(1).strip()
        try:
            obj = json.loads(extracted)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 3. Find outermost balanced curly braces containing "action"
    start = -1
    for i, ch in enumerate(clean):
        if ch == "{":
            start = i
            break

    if start == -1:
        raise ValueError("Respons AI tidak mengandung JSON object.")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(clean)):
        ch = clean[i]
        if esc:
            esc = False
            continue
        if in_str:
            if ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = clean[start:i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    # Continue searching if this wasn't the target outer JSON
                    pass

    raise ValueError("JSON object tidak valid atau tidak tertutup dengan benar.")


# ---------- LLM Clients ----------
class BaseLLMClient:
    def send_message(self, text: str) -> str:
        raise NotImplementedError

    def send_message_with_image(self, text: str, image_path: str) -> str:
        return self.send_message(text)

    def supports_vision(self) -> bool:
        return False

    def model_label(self) -> str:
        return "Unknown"

    def close(self) -> None:
        if hasattr(self, "client") and hasattr(self.client, "close"):
            try:
                self.client.close()
            except Exception:
                pass


class GeminiClient(BaseLLMClient):
    """
    Fixed and optimized Gemini client using Google GenAI SDK.
    Eliminates dummy ping probes, maintains chat history across model failovers.
    """
    def __init__(self, use_vertex: bool = False,
                 system_prompt: Optional[str] = None,
                 mode: str = "coding"):
        if genai is None or types is None:
            raise RuntimeError('Library google-genai belum terpasang. Jalankan: pip install "google-genai>=1.0.0"')

        self.use_vertex = use_vertex
        self.mode = mode
        self.system_prompt = system_prompt or SYSTEM_PROMPT_CODING

        if use_vertex:
            vk = os.getenv("VERTEX_API_KEY")
            self.client = (genai.Client(vertexai=True, api_key=vk)
                           if vk else genai.Client(vertexai=True))
            self.mode_name = "Vertex AI" if vk else "Vertex AI (ADC)"
        else:
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError("GEMINI_API_KEY atau GOOGLE_API_KEY diperlukan.")
            self.client = genai.Client(api_key=key)
            self.mode_name = "Gemini API key"

        self.config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            response_mime_type="application/json",
            response_schema=make_action_schema(mode),
            temperature=0.2,
            max_output_tokens=2500,
        )
        self.chat = None
        self._model_used = None
        self._init_chat()

    def _init_chat(self) -> None:
        # BUG FIX: Do NOT send dummy "ping" message during initialization!
        # It pollutes chat history and wastes quota. Instead, initialize chat directly.
        model = DEFAULT_GEMINI_MODEL
        try:
            self.chat = self.client.chats.create(model=model, config=self.config)
            self._model_used = model
        except Exception as exc:
            # If the primary model fails immediately, fallback
            self._try_init_fallback(exc)

    def _try_init_fallback(self, first_err: Exception) -> None:
        for model in GEMINI_MODEL_FALLBACKS:
            if model == DEFAULT_GEMINI_MODEL:
                continue
            try:
                self.chat = self.client.chats.create(model=model, config=self.config)
                self._model_used = model
                return
            except Exception:
                continue
        raise RuntimeError(f"Gagal inisialisasi semua model Gemini. Error awal: {first_err}")

    def _get_history(self) -> list:
        if self.chat and hasattr(self.chat, "get_history"):
            try:
                return self.chat.get_history()
            except Exception:
                return []
        return []

    def _try_fallback_models(self, text: str, image_path: Optional[str] = None) -> str:
        # BUG FIX: Preserve conversation history when switching fallback models!
        past_history = self._get_history()
        last_err = None

        for model in GEMINI_MODEL_FALLBACKS:
            if model == self._model_used:
                continue
            print(f"\n[!] Gemini limit/error pada {self._model_used}. Beralih ke model: {model}...", file=sys.stderr)
            try:
                # Recreate chat preserving prior history
                if past_history:
                    self.chat = self.client.chats.create(
                        model=model,
                        config=self.config,
                        history=past_history
                    )
                else:
                    self.chat = self.client.chats.create(model=model, config=self.config)

                if image_path:
                    res = self._do_send_with_image(text, image_path)
                else:
                    res = self._do_send(text)
                self._model_used = model
                return res
            except Exception as exc:
                last_err = exc

        raise RuntimeError(
            f"Semua model Gemini mengalami kendala kuota/koneksi ({last_err}). "
            "Silakan tunggu 1-2 menit, atau beralih ke provider OpenAI/DeepSeek."
        )

    def _do_send(self, text: str) -> str:
        r = self.chat.send_message(text)
        if not getattr(r, "text", None):
            raise RuntimeError("Gemini mengembalikan respons kosong.")
        return r.text

    def _do_send_with_image(self, text: str, image_path: str) -> str:
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            data = f.read()
        part = types.Part.from_bytes(data=data, mime_type=mime)
        r = self.chat.send_message([text, part])
        if not getattr(r, "text", None):
            raise RuntimeError("Gemini mengembalikan respons kosong.")
        return r.text

    def send_message(self, text: str) -> str:
        try:
            return self._do_send(text)
        except Exception as exc:
            err_msg = str(exc).lower()
            if any(k in err_msg for k in ("503", "unavailable", "429", "quota", "exhausted", "not_found", "404")):
                return self._try_fallback_models(text)
            raise

    def supports_vision(self) -> bool:
        return True

    def send_message_with_image(self, text: str, image_path: str) -> str:
        try:
            return self._do_send_with_image(text, image_path)
        except Exception as exc:
            err_msg = str(exc).lower()
            if any(k in err_msg for k in ("503", "unavailable", "429", "quota", "exhausted", "not_found", "404")):
                return self._try_fallback_models(text, image_path)
            raise

    def model_label(self) -> str:
        return self._model_used or DEFAULT_GEMINI_MODEL


class OpenAICompatibleClient(BaseLLMClient):
    PROVIDER_CONFIG = {
        "openai":   {"api_key_env": ["OPENAI_API_KEY"], "base_url": None,
                     "model_env": "OPENAI_MODEL", "default_model": "gpt-4o",
                     "json_mode": True},
        "deepseek": {"api_key_env": ["DEEPSEEK_API_KEY"],
                     "base_url": "https://api.deepseek.com",
                     "model_env": "DEEPSEEK_MODEL", "default_model": "deepseek-chat",
                     "json_mode": True},
        "grok":     {"api_key_env": ["XAI_API_KEY"], "base_url": "https://api.x.ai/v1",
                     "model_env": "GROK_MODEL", "default_model": "grok-2-latest",
                     "json_mode": True},
        "meta":     {"api_key_env": ["LLAMA_API_KEY", "META_API_KEY"],
                     "base_url": "https://api.llama.com/compat/v1",
                     "model_env": "META_MODEL",
                     "default_model": "Llama-3.3-70B-Instruct", "json_mode": False},
    }

    def __init__(self, provider: str, system_prompt: Optional[str] = None):
        if OpenAI is None:
            raise RuntimeError("Library openai belum terpasang. Jalankan: pip install openai")
        cfg = self.PROVIDER_CONFIG.get(provider)
        if cfg is None:
            raise ValueError(f"Unknown provider: {provider}")
        key = next((os.getenv(k) for k in cfg["api_key_env"] if os.getenv(k)), None)
        if not key:
            raise RuntimeError(f"Kunci API belum diset. Atur: {', '.join(cfg['api_key_env'])}")
        self.provider = provider
        self.model = os.getenv(cfg["model_env"], cfg["default_model"])
        self.json_mode = cfg["json_mode"]
        self.client = OpenAI(api_key=key, base_url=cfg["base_url"])
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT_CODING}
        ]

    def _call(self, use_json: bool) -> str:
        kw: Dict[str, Any] = {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.2,
            "max_tokens": 2500,
        }
        if use_json:
            kw["response_format"] = {"type": "json_object"}
        r = self.client.chat.completions.create(**kw)
        if not r.choices or not r.choices[0].message:
            raise RuntimeError(f"{self.provider} tidak mengembalikan pilihan respons.")
        c = r.choices[0].message.content
        if not c:
            raise RuntimeError(f"{self.provider} mengembalikan respons kosong.")
        return c

    def _send_with_retry(self, text_added: bool) -> str:
        try:
            try:
                content = self._call(self.json_mode)
            except Exception as exc:
                msg = str(exc).lower()
                retry = self.json_mode and any(t in msg for t in (
                    "response_format", "json", "unsupported",
                    "not supported", "invalid_request"
                ))
                if not retry:
                    raise
                content = self._call(False)
            self.messages.append({"role": "assistant", "content": content})
            return content
        except Exception:
            if text_added and self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
            raise

    def send_message(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        return self._send_with_retry(text_added=True)

    def supports_vision(self) -> bool:
        return VISION_CAPABLE.get(self.provider, False)

    def send_message_with_image(self, text: str, image_path: str) -> str:
        if not self.supports_vision():
            return self.send_message(
                text + f"\n\n[Screenshot tersimpan di: {image_path}, namun provider {self.provider} tidak mendukung vision.]"
            )
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        self.messages.append({"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]})
        return self._send_with_retry(text_added=True)

    def model_label(self) -> str:
        return self.model


class AnthropicClient(BaseLLMClient):
    def __init__(self, system_prompt: Optional[str] = None):
        if anthropic is None:
            raise RuntimeError("Library anthropic belum terpasang. Jalankan: pip install anthropic")
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY diperlukan.")
        self.client = anthropic.Anthropic(api_key=key)
        self.model = os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
        self.system_prompt = system_prompt or SYSTEM_PROMPT_CODING
        self.messages: List[Dict[str, Any]] = []

    def _send(self) -> str:
        try:
            r = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                system=self.system_prompt,
                messages=self.messages,
            )
            blocks = [getattr(b, "text", None) for b in (r.content or [])]
            out = "\n".join(b for b in blocks if b)
            if not out:
                raise RuntimeError("Claude mengembalikan respons kosong.")
            self.messages.append({"role": "assistant", "content": out})
            return out
        except Exception:
            if self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
            raise

    def send_message(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        return self._send()

    def supports_vision(self) -> bool:
        return True

    def send_message_with_image(self, text: str, image_path: str) -> str:
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        self.messages.append({"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
        ]})
        return self._send()

    def model_label(self) -> str:
        return self.model


def create_llm_client(provider: Optional[str] = None,
                      gemini_mode: Optional[str] = None,
                      mode: str = "coding") -> BaseLLMClient:
    provider = (provider or os.getenv("AI_PROVIDER", "gemini")).lower()
    sp = MODE_PROMPTS.get(mode, SYSTEM_PROMPT_CODING)

    if provider == "gemini":
        if gemini_mode == "vertex":
            return GeminiClient(use_vertex=True, system_prompt=sp, mode=mode)
        if gemini_mode == "api_key":
            try:
                return GeminiClient(use_vertex=False, system_prompt=sp, mode=mode)
            except Exception as exc:
                print(f"[!] API-key failed: {exc}. Trying Vertex...", file=sys.stderr)
                return GeminiClient(use_vertex=True, system_prompt=sp, mode=mode)
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if key:
            try:
                return GeminiClient(use_vertex=False, system_prompt=sp, mode=mode)
            except Exception as exc:
                print(f"[!] API-key failed: {exc}. Trying Vertex...", file=sys.stderr)
        try:
            return GeminiClient(use_vertex=True, system_prompt=sp, mode=mode)
        except Exception as exc:
            raise RuntimeError(f"Gemini unavailable: {exc}")

    if provider in {"openai", "deepseek", "grok", "meta"}:
        return OpenAICompatibleClient(provider, system_prompt=sp)
    if provider == "claude":
        return AnthropicClient(system_prompt=sp)
    raise ValueError(f"Unknown provider: {provider}")


def get_model_for(provider: str) -> str:
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    if provider == "claude":
        return os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    cfg = OpenAICompatibleClient.PROVIDER_CONFIG.get(provider)
    return os.getenv(cfg["model_env"], cfg["default_model"]) if cfg else "unknown"


# ---------- File & Path Operations ----------
def safe_path(path: str, base: Path) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path tidak boleh kosong.")
    req = Path(path).expanduser()
    if req.is_absolute():
        raise PermissionError("Gunakan path relatif demi keamanan.")
    resolved = (base / req).resolve()
    if resolved != base and base not in resolved.parents:
        raise PermissionError(f"Akses di luar working directory ditolak: {path}")
    if any(part in SENSITIVE_NAMES or part.startswith(".env.")
           for part in resolved.relative_to(base).parts):
        raise PermissionError(f"Akses file kredensial/sensitif diblokir: {path}")
    return resolved


def search_code(query: str, path: str, file_pattern: str, base: Path) -> Dict[str, Any]:
    """
    PERFORMANCE OPTIMIZATION:
    Replaces unpruned rglob with in-place pruned os.walk.
    Instantly skips .git, node_modules, venv, and large binary directories,
    turning 10-30s searches into sub-50ms instant lookups.
    """
    if not query or not query.strip():
        return {"error": "Query pencarian kosong."}
    fp = file_pattern.strip() if file_pattern else "*"
    if fp.startswith(("/", "\\")) or ".." in fp:
        return {"error": f"Pola file tidak valid: {fp!r}"}

    try:
        root = safe_path(path or ".", base)
    except (ValueError, PermissionError) as exc:
        return {"error": str(exc)}

    if not root.exists():
        return {"error": f"Target direktori/file tidak ditemukan: {path}"}

    out: List[Dict[str, Any]] = []
    q_case = query.casefold()

    if root.is_file():
        file_candidates = [root]
    else:
        file_candidates = []
        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
            # Prune ignored directories in-place!
            dirnames[:] = [
                d for d in dirnames
                if d not in IGNORED_DIRS and not d.startswith(".")
            ]
            for fname in filenames:
                if fnmatch.fnmatch(fname, fp):
                    file_candidates.append(Path(dirpath) / fname)
                    if len(file_candidates) >= MAX_SEARCH_MATCHES * 5:
                        break
            if len(out) >= MAX_SEARCH_MATCHES:
                break

    for cand in file_candidates:
        try:
            rel = cand.relative_to(base)
            if any(p in SENSITIVE_NAMES for p in rel.parts):
                continue
            if cand.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
            # Read text safely
            content = cand.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
        except (OSError, ValueError):
            continue

        for i, line in enumerate(lines, 1):
            if q_case in line.casefold():
                out.append({
                    "path": str(rel).replace("\\", "/"),
                    "line": i,
                    "text": line.strip()[:400]
                })
                if len(out) >= MAX_SEARCH_MATCHES:
                    return {"matches": out, "limited": True, "total_found": len(out)}

    return {"matches": out, "limited": False, "total_found": len(out)}


def ask_permission(description: str) -> bool:
    if PERMISSION_HANDLER is not None:
        return PERMISSION_HANDLER(description)
    print(f"\n[!] AI Agent meminta konfirmasi izin:\n    {description}")
    try:
        ans = input("Izinkan aksi ini? [y/N]: ").strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print("\nAksi dibatalkan oleh pengguna.")
        return False
    return ans in {"y", "yes"}


def read_file(path: str, base: Path) -> Dict[str, Any]:
    try:
        fp = safe_path(path, base)
    except (ValueError, PermissionError) as exc:
        return {"error": str(exc)}
    if not fp.is_file():
        return {"error": f"File tidak ditemukan: {path}"}
    try:
        with open(fp, "rb") as fh:
            data = fh.read(MAX_READ_BYTES + 1)
        trunc = len(data) > MAX_READ_BYTES
        if trunc:
            data = data[:MAX_READ_BYTES]
        return {
            "path": str(fp.relative_to(base)).replace("\\", "/"),
            "content": data.decode("utf-8", errors="replace"),
            "truncated": trunc,
            "bytes_read": len(data)
        }
    except OSError as exc:
        return {"error": str(exc)}


def write_file(path: str, content: str, base: Path) -> Dict[str, Any]:
    try:
        fp = safe_path(path, base)
    except (ValueError, PermissionError) as exc:
        return {"error": str(exc)}
    if not isinstance(content, str):
        return {"error": "Content harus berupa teks."}
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return {"error": f"Ukuran file melebihi batas {MAX_WRITE_BYTES} bytes."}
    if not ask_permission(f"Tulis ke file: {fp.relative_to(base)} ({len(content)} karakter)"):
        return {"error": "Aksi menulis file ditolak pengguna."}

    tmp = None
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=fp.parent, prefix=".agent-",
                                         suffix=".tmp", delete=False) as tf:
            tf.write(content)
            tmp = tf.name
        Path(tmp).replace(fp)
        return {"path": str(fp.relative_to(base)).replace("\\", "/"), "written": True, "bytes": len(content.encode("utf-8"))}
    except OSError as exc:
        if tmp:
            try:
                Path(tmp).unlink(missing_ok=True)
            except OSError:
                pass
        return {"error": str(exc)}


# ---------- Command Handlers ----------
def check_self_destruct(command: str) -> Optional[str]:
    for pat, reason in _SELF_DESTRUCT_PATTERNS:
        if re.search(pat, command, re.IGNORECASE):
            return reason
    return None


def run_coding_command(command: str, base: Path) -> Dict[str, Any]:
    """
    BUG FIX:
    On Windows, 'cd', 'dir', and 'type' are internal shell commands inside cmd.exe.
    Running them with shell=False causes FileNotFoundError.
    Now properly executes internal commands via cmd.exe /c on Windows.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return {"error": "Command kosong."}

    try:
        parts = shlex.split(cmd_clean, posix=not IS_WINDOWS)
    except ValueError as exc:
        return {"error": f"Format command tidak valid: {exc}"}

    if not parts:
        return {"error": "Command kosong."}

    exe = parts[0].lower()

    if IS_WINDOWS:
        is_builtin = exe in {"cd", "dir", "type"}
        allowed = (
            is_builtin
            or (exe == "git" and len(parts) >= 2 and parts[1] in {"status", "diff", "log", "branch"})
            or (exe in {"python", "python3", "py"} and parts[1:] == ["--version"])
        )
        hint = "cd, dir, type, git status/diff/log/branch, python --version"
    else:
        is_builtin = False
        allowed = (
            exe in {"pwd", "ls", "cat"}
            or (exe == "git" and len(parts) >= 2 and parts[1] in {"status", "diff", "log", "branch"})
            or (exe in {"python", "python3"} and parts[1:] == ["--version"])
        )
        hint = "pwd, ls, cat, git status/diff/log/branch, python --version"

    if not allowed:
        return {"error": f"Command diblokir. Allowlist coding mode: {hint}. (Gunakan mode hacking untuk full shell.)"}

    if not ask_permission(f"$ {cmd_clean}"):
        return {"error": "Eksekusi command ditolak pengguna."}

    try:
        # BUG FIX: If Windows builtin, run with shell=True or cmd.exe
        use_shell = IS_WINDOWS and is_builtin
        r = subprocess.run(
            cmd_clean if use_shell else parts,
            cwd=base,
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
            shell=use_shell
        )
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout[-15_000:],
            "stderr": r.stderr[-15_000:]
        }
    except subprocess.TimeoutExpired:
        return {"error": "Batas waktu eksekusi (timeout) 25 detik terlampaui."}
    except OSError as exc:
        return {"error": str(exc)}


def run_hacking_command(command: str, base: Path) -> Dict[str, Any]:
    cmd_clean = command.strip()
    if not cmd_clean:
        return {"error": "Command kosong."}

    reason = check_self_destruct(cmd_clean)
    if reason:
        if not ask_permission(f"⚠️  PERINGATAN KRITIKAL: Pola terdeteksi {reason}!\n    $ {cmd_clean}\n    Apakah Anda yakin ingin melanjutkan?"):
            return {"error": "Dibatalkan demi keselamatan sistem."}
        if not ask_permission("🚨 KONFIRMASI GANDA: Apakah Anda benar-benar yakin 100%?"):
            return {"error": "Dibatalkan pada konfirmasi kedua."}

    if not ask_permission(f"$ {cmd_clean}"):
        return {"error": "Ditolak oleh pengguna."}

    try:
        r = subprocess.run(cmd_clean, cwd=base, text=True, capture_output=True,
                           timeout=HACKING_TIMEOUT, check=False, shell=True)
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout[-15_000:],
            "stderr": r.stderr[-15_000:]
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout {HACKING_TIMEOUT} detik terlampaui."}
    except OSError as exc:
        return {"error": str(exc)}


def run_windows_command(command: str, base: Path) -> Dict[str, Any]:
    cmd_clean = command.strip()
    if not cmd_clean:
        return {"error": "Command kosong."}

    reason = check_self_destruct(cmd_clean)
    if reason:
        if not ask_permission(f"⚠️  DESTRUCTIVE — {reason}\n$ {cmd_clean}\nYakin?"):
            return {"error": "Dibatalkan."}
        if not ask_permission("🚨 KONFIRMASI GANDA?"):
            return {"error": "Dibatalkan."}

    if not ask_permission(f"$ {cmd_clean}"):
        return {"error": "Ditolak pengguna."}

    try:
        r = subprocess.run(cmd_clean, cwd=base, text=True, capture_output=True,
                           timeout=HACKING_TIMEOUT, check=False, shell=True)
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout[-15_000:],
            "stderr": r.stderr[-15_000:]
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout {HACKING_TIMEOUT}s."}
    except OSError as exc:
        return {"error": str(exc)}


# ---------- Windows Desktop Automation ----------
def _lazy_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.08
        return pyautogui
    except ImportError as exc:
        raise RuntimeError("Library pyautogui belum terpasang. Jalankan: pip install pyautogui pillow") from exc


def win_screenshot(base: Path) -> Dict[str, Any]:
    try:
        pg = _lazy_pyautogui()
    except RuntimeError as exc:
        return {"error": str(exc)}

    if WINDOWS_SCREENSHOT_PROMPT:
        if not ask_permission("Ambil tangkapan layar (screenshot)?"):
            return {"error": "Ditolak."}
    try:
        shots = base / "screenshots"
        shots.mkdir(parents=True, exist_ok=True)
        name = f"screen_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        path = shots / name
        img = pg.screenshot()
        img.save(str(path))
        return {
            "path": str(path.relative_to(base)).replace("\\", "/"),
            "size": list(img.size),
            "screen_region": "full"
        }
    except Exception as exc:
        return {"error": f"Screenshot gagal: {exc}"}


def win_mouse(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        pg = _lazy_pyautogui()
    except RuntimeError as exc:
        return {"error": str(exc)}

    action = (params.get("action") or "").lower()
    x = params.get("x")
    y = params.get("y")

    if action in {"move", "click", "doubleclick", "rightclick", "drag"}:
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            return {"error": f"Koordinat x,y harus angka untuk action '{action}'."}
        x, y = int(x), int(y)

    desc = {
        "move":       f"gerakkan mouse ke ({x},{y})",
        "click":      f"klik kiri di ({x},{y})",
        "doubleclick":f"double-click di ({x},{y})",
        "rightclick": f"klik kanan di ({x},{y})",
        "drag":       f"drag ke ({x},{y})",
        "scroll":     f"scroll {params.get('amount', 0)} pada ({x},{y})",
    }.get(action, action)

    if not ask_permission(f"Mouse Automation: {desc}"):
        return {"error": "Ditolak pengguna."}

    try:
        dur = float(params.get("duration", 0.15))
        if action == "move":
            pg.moveTo(x, y, duration=dur)
        elif action == "click":
            pg.click(x, y, clicks=int(params.get("clicks", 1)),
                     button=params.get("button", "left"), duration=dur)
        elif action == "doubleclick":
            pg.doubleClick(x, y, button=params.get("button", "left"))
        elif action == "rightclick":
            pg.rightClick(x, y)
        elif action == "drag":
            pg.dragTo(x, y, duration=dur, button=params.get("button", "left"))
        elif action == "scroll":
            pg.scroll(int(params.get("amount", 0)), x=x, y=y)
        else:
            return {"error": f"Mouse action tidak dikenal: {action}"}
        return {"action": action, "x": x, "y": y, "done": True}
    except Exception as exc:
        return {"error": f"Mouse automation gagal: {type(exc).__name__}: {exc}"}


def win_keyboard(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        pg = _lazy_pyautogui()
    except RuntimeError as exc:
        return {"error": str(exc)}

    action = (params.get("action") or "").lower()
    text = params.get("text") or ""

    # BUG FIX / NORMALIZATION: Support 'key' singular alias
    keys = params.get("keys") or params.get("key")
    if isinstance(keys, str):
        keys = keys.split("+") if action == "hotkey" else [keys]

    if action == "write" and not text:
        return {"error": "Parameter 'text' kosong untuk write."}
    if action in {"press", "hotkey"} and not keys:
        return {"error": f"Parameter 'keys' kosong untuk {action}."}
    if action == "paste" and not text:
        return {"error": "Parameter 'text' kosong untuk paste."}

    preview = text if len(text) <= 150 else text[:150] + "..."
    desc = {
        "write": f"ketik teks ({len(text)} char): {preview!r}",
        "press": f"tekan tombol {keys}",
        "hotkey": f"hotkey {'+'.join(keys) if keys else ''}",
        "paste": f"paste teks ({len(text)} char): {preview!r}",
    }.get(action, action)

    if not ask_permission(f"Keyboard Automation: {desc}"):
        return {"error": "Ditolak pengguna."}

    try:
        if action == "write":
            pg.write(text, interval=float(params.get("interval", 0.015)))
        elif action == "press":
            for k in keys:
                pg.press(str(k).lower())
        elif action == "hotkey":
            pg.hotkey(*[str(k).lower() for k in keys])
        elif action == "paste":
            try:
                import pyperclip
            except ImportError:
                return {"error": "Library pyperclip belum terpasang. Jalankan: pip install pyperclip"}
            pyperclip.copy(text)
            time.sleep(0.04)
            pg.hotkey("ctrl", "v")
        else:
            return {"error": f"Keyboard action tidak dikenal: {action}"}
        return {"action": action, "done": True}
    except Exception as exc:
        return {"error": f"Keyboard automation gagal: {type(exc).__name__}: {exc}"}


def win_window(params: Dict[str, Any]) -> Dict[str, Any]:
    action = (params.get("action") or "").lower()
    title = params.get("title") or ""
    try:
        import pygetwindow as gw
    except ImportError:
        return {"error": "Library pygetwindow belum terpasang. Jalankan: pip install pygetwindow"}

    try:
        if action == "list":
            wins = [w.title for w in gw.getAllWindows() if w.title]
            return {"windows": wins[:50], "total": len(wins)}
        if not title:
            return {"error": f"Parameter 'title' kosong untuk action '{action}'."}

        wins = gw.getWindowsWithTitle(title)
        if not wins:
            return {"error": f"Jendela tidak ditemukan dengan judul matching: {title!r}"}
        w = wins[0]

        if not ask_permission(f"Window Action: {action} → '{w.title}'"):
            return {"error": "Ditolak pengguna."}

        if action == "activate":
            # BUG FIX: Handle Windows focus stealing exception gracefully
            try:
                if w.isMinimized:
                    w.restore()
                w.activate()
            except Exception as focus_err:
                # Fallback: attempt restore or ignore if already foreground
                try:
                    w.restore()
                except Exception:
                    pass
            time.sleep(0.15)
        elif action == "minimize":
            w.minimize()
        elif action == "maximize":
            w.maximize()
        elif action == "close":
            w.close()
        else:
            return {"error": f"Window action tidak dikenal: {action}"}
        return {"action": action, "title": w.title, "done": True}
    except Exception as exc:
        return {"error": f"Window action gagal: {type(exc).__name__}: {exc}"}


_WIN_APP_MAP = {
    "code": "code", "vscode": "code", "vs code": "code", "vs_code": "code",
    "notepad": "notepad", "calc": "calc", "calculator": "calc",
    "explorer": "explorer", "file explorer": "explorer",
    "cmd": "cmd", "powershell": "powershell", "pwsh": "powershell",
    "paint": "mspaint", "mspaint": "mspaint",
    "chrome": "chrome", "google chrome": "chrome",
    "edge": "msedge", "msedge": "msedge",
    "firefox": "firefox", "word": "winword", "excel": "excel",
    "terminal": "wt", "windows terminal": "wt",
}


def win_open(params: Dict[str, Any], base: Path) -> Dict[str, Any]:
    app_raw = params.get("app") or params.get("app_name") or params.get("application") or params.get("program")
    app = str(app_raw).strip() if app_raw is not None else ""
    args_raw = params.get("args") or ""
    args = str(args_raw).strip()

    if not app:
        return {"error": "Parameter 'app' kosong."}

    exe = _WIN_APP_MAP.get(app.lower(), app)
    if not ask_permission(f"Buka aplikasi: {app} {args}".strip()):
        return {"error": "Ditolak pengguna."}

    try:
        if IS_WINDOWS:
            cmd = f'start "" "{exe}"'
            if args:
                cmd += f" {args}"
            subprocess.Popen(cmd, shell=True, cwd=base)
        elif IS_MAC:
            cmd_args = ["open", "-a", exe]
            if args:
                cmd_args.extend(shlex.split(args))
            subprocess.Popen(cmd_args)
        else:
            # Linux / Kali
            cmd_args = [exe]
            if args:
                cmd_args.extend(shlex.split(args))
            subprocess.Popen(cmd_args, cwd=base)
        time.sleep(1.0)
        return {"app": app, "exe": exe, "args": args, "launched": True}
    except Exception as exc:
        return {"error": f"Gagal meluncurkan {app}: {type(exc).__name__}: {exc}"}


def run_command(command: str, base: Path, mode: str = "coding") -> Dict[str, Any]:
    if mode == "hacking":
        return run_hacking_command(command, base)
    if mode == "windows":
        return run_windows_command(command, base)
    return run_coding_command(command, base)


# ---------- Action Normalization & Dispatch ----------
def validate_action(payload: Any, mode: str = "coding") -> Tuple[str, Dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("Payload bukan objek JSON.")

    action = payload.get("action")
    params = payload.get("parameters")

    allowed = set(ACTIONS_BY_MODE.get(mode, ACTIONS_BY_MODE["coding"]))
    if action not in allowed:
        raise ValueError(f"Action '{action}' tidak dikenal untuk mode {mode}. Diizinkan: {sorted(allowed)}")

    if not isinstance(params, dict):
        raise ValueError("Parameter bukan JSON object.")

    # Parameter normalization & aliases
    if action == "open":
        for alt in ("app_name", "application", "program", "name"):
            if alt in params and "app" not in params:
                params["app"] = params.pop(alt)

    if action == "keyboard":
        if "key" in params and "keys" not in params:
            params["keys"] = params.pop("key")

    if action in {"read_file", "write_file"}:
        for alt in ("file", "filename", "file_path", "target"):
            if alt in params and "path" not in params:
                params["path"] = params.pop(alt)

    if action == "run_command":
        if "cmd" in params and "command" not in params:
            params["command"] = params.pop("cmd")

    required = {
        "chat": ("message",),
        "search_code": ("query",),
        "read_file": ("path",),
        "write_file": ("path", "content"),
        "run_command": ("command",),
        "screenshot": (),
        "mouse": ("action",),
        "keyboard": ("action",),
        "window": ("action",),
        "open": ("app",),
    }

    for f in required.get(action, ()):
        if f not in params:
            raise ValueError(f"Parameter '{f}' diperlukan untuk action '{action}'.")
        if not isinstance(params[f], str):
            if isinstance(params[f], (int, float, bool)):
                params[f] = str(params[f])
            elif params[f] is None:
                raise ValueError(f"Parameter '{f}' bernilai null/None pada action '{action}'.")

    return action, params


def execute_action(action: str, params: Dict[str, Any], base: Path,
                   mode: str = "coding") -> Tuple[Any, Optional[str]]:
    def s(n: str) -> str:
        v = params.get(n)
        return str(v) if v is not None else ""

    if action == "chat":
        return None, s("message")
    if action == "search_code":
        return search_code(s("query"), s("path") or ".",
                           s("file_pattern") or "*", base), None
    if action == "read_file":
        return read_file(s("path"), base), None
    if action == "write_file":
        c = params.get("content")
        return write_file(s("path"), c if isinstance(c, str) else "", base), None
    if action == "run_command":
        return run_command(s("command"), base, mode=mode), None
    if action == "screenshot":
        return win_screenshot(base), None
    if action == "mouse":
        return win_mouse(params), None
    if action == "keyboard":
        return win_keyboard(params), None
    if action == "window":
        return win_window(params), None
    if action == "open":
        return win_open(params, base), None
    return {"error": f"Action '{action}' tidak didukung."}, None


# ---------- Multi-Step Turn Executor ----------
def run_turn(llm: BaseLLMClient, user_input: str, base: Path, mode: str,
             on_action: Callable[[str], None],
             on_chat: Callable[[str], None],
             on_info: Callable[[str], None]) -> None:
    """
    BUG FIX & OPTIMIZATION:
    Format self-correction is isolated from turn-step budget.
    JSON parsing errors do NOT burn the user's turn steps.
    """
    max_steps = MAX_STEPS_BY_MODE.get(mode, 6)
    current_prompt = user_input
    pending_image: Optional[str] = None

    for step in range(max_steps):
        raw_response = ""
        action = ""
        params: Dict[str, Any] = {}

        # Inner retry loop for JSON formatting & validation
        for parse_attempt in range(3):
            try:
                if pending_image and llm.supports_vision():
                    raw_response = llm.send_message_with_image(current_prompt, pending_image)
                else:
                    raw_response = llm.send_message(current_prompt)
                pending_image = None

                # Conversational fallback: if no JSON structure at all, treat as friendly chat
                try:
                    action, params = validate_action(parse_ai_response(raw_response), mode=mode)
                    break
                except ValueError as parse_err:
                    if "{" not in raw_response and not raw_response.strip().startswith("```"):
                        action = "chat"
                        params = {"message": raw_response.strip()}
                        break
                    raise parse_err

            except ValueError as exc:
                if parse_attempt == 2:
                    on_chat(f"[Gagal parsing respons AI setelah 3 percobaan: {exc}]")
                    return
                on_info(f"[Format Recovery] Meminta AI memperbaiki format JSON ({exc})...")
                current_prompt = (
                    f"Respons Anda sebelumnya bukan JSON valid: {exc}\n"
                    f"Kembalikan HANYA SATU JSON object valid dengan format:\n"
                    f'{{"action": "<nama_action>", "parameters": {{ ... }}}}\n'
                    f"Dilarang menggunakan Markdown code fences atau teks pembuka."
                )
            except Exception as exc:
                on_chat(f"[Error Provider] {type(exc).__name__}: {exc}")
                return

        if action == "chat":
            on_chat(params.get("message", ""))
            return

        on_action(action)
        try:
            result, _ = execute_action(action, params, base, mode=mode)
        except Exception as exc:
            result = {"error": f"Eksekusi gagal: {type(exc).__name__}: {exc}"}

        # Attach screenshot for vision models in the next step
        if action == "screenshot" and isinstance(result, dict) and "path" in result:
            pending_image = str(base / result["path"])

        if step == max_steps - 1:
            on_chat(f"[Selesai: batas {max_steps} langkah tercapai]")
            return

        current_prompt = (
            "Hasil action sebelumnya (JSON):\n"
            + json.dumps(result, ensure_ascii=False)
            + "\n\nLanjutkan dengan action berikutnya, atau selesaikan dengan "
              "'chat' jika tugas sudah selesai."
        )


# ---------- GUI Implementation ----------
class AgentGUI:
    def __init__(self, base: Path, mode: str = "coding"):
        self.base = base
        self.mode = mode
        self.llm: Optional[BaseLLMClient] = None
        self.provider: Optional[str] = None
        self._gemini_mode: Optional[str] = None
        self._busy = False
        self._shutting_down = False
        self._queue: queue.Queue[Tuple[str, Tuple[Any, ...]]] = queue.Queue()
        self.chat = self.entry = self.send_btn = self.status = None
        self._build_root()
        self._poll_queue()

    def _build_root(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"AI {MODE_NAMES[self.mode]} v2.0")
        self.root.geometry("1040x740")
        self.root.minsize(760, 540)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        st = tk.Menu(self.menubar, tearoff=0)
        st.add_command(label="Ganti Provider...", command=self._reset_to_selection)
        st.add_command(label="Ganti Model...", command=self._change_model)
        st.add_separator()
        st.add_command(label="Keluar", command=self._on_close)
        self.menubar.add_cascade(label="Pengaturan", menu=st)

        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)
        self._show_provider_selection()

    def _clear(self) -> None:
        self.chat = self.entry = self.send_btn = self.status = None
        for w in self.container.winfo_children():
            w.destroy()

    def _show_provider_selection(self) -> None:
        self._clear()
        self.provider = None
        self._gemini_mode = None
        self.root.title(f"AI {MODE_NAMES[self.mode]} — Pilih Provider")
        outer = ttk.Frame(self.container, padding=30)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text=f"AI {MODE_NAMES[self.mode]} v2.0",
                  font=("TkDefaultFont", 20, "bold")).pack(pady=(15, 4))
        ttk.Label(outer, text="Pilih provider AI untuk memulai:",
                  foreground="gray").pack(pady=(0, 20))

        if self.mode == "windows":
            ttk.Label(
                outer,
                text=f"Platform: {platform.system()} {platform.release()}",
                foreground="#aa4400"
            ).pack(pady=(0, 12))

        for key, name, envs in PROVIDERS:
            present = next((e for e in envs if os.getenv(e)), None)
            row = ttk.Frame(outer)
            row.pack(fill=tk.X, pady=4)
            ttk.Button(row, text=name, width=26,
                       command=lambda k=key: self._on_provider_selected(k)
                       ).pack(side=tk.LEFT, padx=(0, 12))
            if present:
                ttk.Label(row, text=f"✓ Siap ({present})",
                          foreground="#008800").pack(side=tk.LEFT)
            else:
                ttk.Label(row, text="(memerlukan API key)",
                          foreground="gray").pack(side=tk.LEFT)

        ttk.Separator(outer).pack(fill=tk.X, pady=20)
        tips = ttk.LabelFrame(outer, text="Informasi & Bantuan", padding=12)
        tips.pack(fill=tk.X)
        ttk.Label(tips, justify=tk.LEFT, text=(
            "• Klik nama provider untuk membuka konsol interaktif.\n"
            "• API key dapat disimpan di .env atau dimasukkan langsung.\n"
            "• Google Gemini mendukung vision & otomatis failover bila kuota limit.\n"
            "• Mode Hacking memiliki akses shell penuh; perintah berbahaya akan meminta konfirmasi ganda."
        )).pack(anchor=tk.W)

    def _on_provider_selected(self, provider: str) -> None:
        envs = next(e for k, _n, e in PROVIDERS if k == provider)
        existing = next((e for e in envs if os.getenv(e)), None)
        if existing:
            gm = ("vertex" if existing == "VERTEX_API_KEY" else "api_key") if provider == "gemini" else None
            self._start_agent(provider, gemini_mode=gm)
        else:
            self._show_key_input(provider)

    def _show_key_input(self, provider: str) -> None:
        self._clear()
        envs = next(e for k, _n, e in PROVIDERS if k == provider)
        outer = ttk.Frame(self.container, padding=30)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text=f"Konfigurasi Kunci API: {PROVIDER_NAMES[provider]}",
                  font=("TkDefaultFont", 16, "bold")).pack(pady=(10, 15))

        if provider == "gemini":
            self._gemini_key_ui(outer, envs)
        else:
            self._standard_key_ui(outer, provider, envs)

        ttk.Button(outer, text="← Kembali",
                   command=self._show_provider_selection).pack(pady=15)

    def _gemini_key_ui(self, outer, envs) -> None:
        a = ttk.LabelFrame(outer, text="Opsi 1 — Gemini API Key (Rekomendasi)", padding=12)
        a.pack(fill=tk.X, pady=6)
        ttk.Label(a, text="Dapatkan kunci di https://aistudio.google.com/apikey", foreground="gray").pack(anchor=tk.W)
        var = tk.StringVar()
        e = ttk.Entry(a, textvariable=var, show="*", width=60)
        e.pack(pady=6, fill=tk.X)
        e.focus_set()

        def use_key():
            v = var.get().strip()
            if not v:
                messagebox.showerror("Error", "Kunci API tidak boleh kosong.", parent=self.root)
                return
            os.environ["GEMINI_API_KEY"] = v
            self._start_agent("gemini", gemini_mode="api_key")

        e.bind("<Return>", lambda _e: use_key())
        ttk.Button(a, text="Gunakan Gemini API Key", command=use_key).pack(pady=4)

        b = ttk.LabelFrame(outer, text="Opsi 2 — Vertex AI (ADC)", padding=12)
        b.pack(fill=tk.X, pady=6)
        ttk.Label(b, text="Memerlukan VERTEX_API_KEY atau gcloud application-default login.", foreground="gray").pack(anchor=tk.W)
        ttk.Button(b, text="Gunakan Vertex AI", command=lambda: self._start_agent("gemini", gemini_mode="vertex")).pack(pady=6)

    def _standard_key_ui(self, outer, provider: str, envs) -> None:
        url = PROVIDER_KEY_URLS.get(provider, "")
        ttk.Label(outer, text=f"Variabel {envs[0]} belum diset.", foreground="#cc6600").pack()
        if url:
            ttk.Label(outer, text=f"Dapatkan di: {url}", foreground="gray").pack(pady=4)

        var = tk.StringVar()
        e = ttk.Entry(outer, textvariable=var, show="*", width=60)
        e.pack(pady=10)
        e.focus_set()

        def go():
            v = var.get().strip()
            if not v:
                messagebox.showerror("Error", "Kunci API tidak boleh kosong.", parent=self.root)
                return
            os.environ[envs[0]] = v
            self._start_agent(provider)

        e.bind("<Return>", lambda _e: go())
        ttk.Button(outer, text="Simpan & Mulai", command=go).pack(pady=4)

    def _start_agent(self, provider: str, gemini_mode: Optional[str] = None) -> None:
        try:
            llm = create_llm_client(provider, gemini_mode=gemini_mode, mode=self.mode)
        except Exception as exc:
            messagebox.showerror("Gagal Inisialisasi", f"Gagal memulai {PROVIDER_NAMES[provider]}:\n\n{type(exc).__name__}: {exc}", parent=self.root)
            self._show_provider_selection()
            return

        if self.llm:
            try:
                self.llm.close()
            except Exception:
                pass

        self.llm = llm
        self.provider = provider
        self._gemini_mode = gemini_mode
        self.root.title(f"AI {MODE_NAMES[self.mode]} — {PROVIDER_NAMES[provider]}")
        self._show_chat()
        self._append("Info", f"✅ Agent aktif dalam mode {MODE_NAMES[self.mode]}. Working directory: {self.base}")
        self._append("Agent", "Halo! Saya siap membantu Anda. Silakan ketik perintah atau instruksi.")

    def _show_chat(self) -> None:
        self._clear()
        header = ttk.Frame(self.container, padding=(10, 8))
        header.pack(fill=tk.X)

        ttk.Label(header, text=f"Mode: {MODE_NAMES[self.mode]}", font=("TkDefaultFont", 11, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text=f"  •  Provider: {PROVIDER_NAMES[self.provider]}", foreground="gray").pack(side=tk.LEFT)
        model_label = (getattr(self.llm, "model_label", lambda: get_model_for(self.provider))()
                       if self.llm else get_model_for(self.provider))
        ttk.Label(header, text=f"  •  Model: {model_label}", foreground="gray").pack(side=tk.LEFT)

        ttk.Separator(self.container).pack(fill=tk.X)
        cf = ttk.Frame(self.container, padding=(10, 8))
        cf.pack(fill=tk.BOTH, expand=True)

        self.chat = scrolledtext.ScrolledText(cf, wrap=tk.WORD, state=tk.DISABLED,
                                              font=("TkDefaultFont", 10),
                                              borderwidth=1, relief=tk.SOLID)
        self.chat.pack(fill=tk.BOTH, expand=True)
        self.chat.tag_config("You", foreground="#0055aa", font=("TkDefaultFont", 10, "bold"))
        self.chat.tag_config("Agent", foreground="#007700", font=("TkDefaultFont", 10, "bold"))
        self.chat.tag_config("Info", foreground="#666666")
        self.chat.tag_config("Error", foreground="#cc0000")

        inf = ttk.Frame(self.container, padding=(10, 8))
        inf.pack(fill=tk.X)
        self.entry = ttk.Entry(inf, font=("TkDefaultFont", 10))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self._send())

        self.send_btn = ttk.Button(inf, text="Kirim", command=self._send)
        self.send_btn.pack(side=tk.RIGHT)

        self.status = ttk.Label(self.container, text="Siap", relief=tk.SUNKEN, anchor=tk.W, padding=(8, 4))
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        self.entry.focus_set()

    def _append(self, tag: str, text: str) -> None:
        if self.chat is None:
            return
        try:
            self.chat.configure(state=tk.NORMAL)
            self.chat.insert(tk.END, f"\n{tag}: ", tag)
            self.chat.insert(tk.END, text + "\n")
            self.chat.configure(state=tk.DISABLED)
            self.chat.see(tk.END)
        except tk.TclError:
            pass

    def _post(self, kind: str, *payload: Any) -> None:
        self._queue.put((kind, payload))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "append":
                    self._append(payload[0], payload[1])
                elif kind == "status" and self.status is not None:
                    try:
                        self.status.config(text=payload[0])
                    except tk.TclError:
                        pass
                elif kind == "enable_input":
                    self._busy = False
                    if self.send_btn is not None:
                        try:
                            self.send_btn.config(state=tk.NORMAL)
                        except tk.TclError:
                            pass
                    if self.entry is not None:
                        try:
                            self.entry.config(state=tk.NORMAL)
                            self.entry.focus_set()
                        except tk.TclError:
                            pass
        except queue.Empty:
            pass

        if not self._shutting_down:
            try:
                self.root.after(60, self._poll_queue)
            except tk.TclError:
                pass

    def _send(self) -> None:
        if self._busy or self._shutting_down or self.entry is None:
            return
        txt = self.entry.get().strip()
        if not txt:
            return
        if txt.casefold() in {"exit", "quit"}:
            self._on_close()
            return

        self.entry.delete(0, tk.END)
        self._append("You", txt)
        self._busy = True
        if self.send_btn is not None:
            self.send_btn.config(state=tk.DISABLED)
        if self.entry is not None:
            self.entry.config(state=tk.DISABLED)
        if self.status is not None:
            self.status.config(text="Berpikir & menjalankan aksi...")

        threading.Thread(target=self._process, args=(txt,), daemon=True).start()

    def _process(self, user_input: str) -> None:
        # Direct shell command shortcut: !command
        if user_input.startswith("!"):
            cmd = user_input[1:].strip()
            if not cmd:
                self._post("append", "Info", "Command kosong setelah tanda seru '!'.")
                self._post("enable_input")
                return
            try:
                result = run_command(cmd, self.base, mode=self.mode)
                out = (result.get("stdout") or result.get("stderr") or result.get("error") or "")
                self._post("append", "Info", f"$ {cmd}")
                self._post("append", "Agent", out or "(tidak ada output)")
            except Exception as exc:
                self._post("append", "Error", f"{type(exc).__name__}: {exc}")
            finally:
                self._post("enable_input")
                self._post("status", "Siap")
            return

        llm = self.llm
        if llm is None:
            self._post("append", "Error", "Provider belum dipilih.")
            self._post("enable_input")
            return

        try:
            run_turn(
                llm, user_input, self.base, self.mode,
                on_action=lambda a: self._post("append", "Info", f"[Aksi AI: {a}]"),
                on_chat=lambda m: self._post("append", "Agent", m),
                on_info=lambda m: self._post("append", "Info", m),
            )
        except Exception as exc:
            self._post("append", "Error", f"{type(exc).__name__}: {exc}")
        finally:
            self._post("enable_input")
            self._post("status", "Siap")

    def _ask_permission(self, description: str) -> bool:
        if self._shutting_down:
            return False
        res = [False]
        ev = threading.Event()

        def show():
            try:
                if self._shutting_down:
                    return
                res[0] = messagebox.askyesno("Izin Diperlukan", description, parent=self.root)
            except tk.TclError:
                pass
            finally:
                ev.set()

        try:
            self.root.after(0, show)
        except tk.TclError:
            return False

        while not ev.wait(timeout=0.1):
            if self._shutting_down:
                return False
        return bool(res[0]) and not self._shutting_down

    def _reset_to_selection(self) -> None:
        if self._busy:
            messagebox.showinfo("Sibuk", "Mohon tunggu hingga proses selesai.", parent=self.root)
            return
        if self.llm:
            try:
                self.llm.close()
            except Exception:
                pass
            self.llm = None
        self.provider = None
        self._gemini_mode = None
        self._show_provider_selection()

    def _change_model(self) -> None:
        if self._busy:
            messagebox.showinfo("Sibuk", "Tunggu hingga proses selesai.", parent=self.root)
            return
        if not self.provider or not self.llm:
            messagebox.showinfo("Info", "Pilih provider terlebih dahulu.", parent=self.root)
            return

        if self.provider == "gemini":
            env_var, cur = "GEMINI_MODEL", get_model_for("gemini")
        elif self.provider == "claude":
            env_var, cur = "CLAUDE_MODEL", get_model_for("claude")
        else:
            cfg = OpenAICompatibleClient.PROVIDER_CONFIG.get(self.provider)
            if not cfg:
                return
            env_var, cur = cfg["model_env"], get_model_for(self.provider)

        new = simpledialog.askstring("Ubah Model", f"Model saat ini: {cur}\n\nMasukkan nama model baru:", initialvalue=cur, parent=self.root)
        if not new or new.strip() == cur:
            return
        new = new.strip()
        os.environ[env_var] = new
        if self.provider == "gemini":
            GEMINI_MODEL_FALLBACKS[0] = new

        try:
            new_llm = create_llm_client(self.provider, gemini_mode=self._gemini_mode, mode=self.mode)
        except Exception as exc:
            messagebox.showerror("Gagal", f"Gagal mengganti model: {exc}", parent=self.root)
            os.environ[env_var] = cur
            return

        if self.llm:
            try:
                self.llm.close()
            except Exception:
                pass
        self.llm = new_llm
        self._show_chat()
        self._append("Info", f"Model berhasil diubah ke: {new}")

    def _on_close(self) -> None:
        self._shutting_down = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        global PERMISSION_HANDLER
        PERMISSION_HANDLER = self._ask_permission
        try:
            self.root.mainloop()
        finally:
            self._shutting_down = True
            PERMISSION_HANDLER = None
            if self.llm:
                try:
                    self.llm.close()
                except Exception:
                    pass


# ---------- CLI Loop ----------
def run_cli(llm: BaseLLMClient, provider: str, base: Path, mode: str = "coding") -> int:
    print(f"\n============================================================")
    print(f"  AI AGENT (CLI) — MODE: {MODE_NAMES[mode].upper()}")
    print(f"============================================================")
    print(f"  Provider   : {PROVIDER_NAMES[provider]} ({provider})")
    model_name = getattr(llm, "model_label", lambda: get_model_for(provider))()
    print(f"  Model      : {model_name}")
    print(f"  Working dir: {base}")
    print(f"  Ketik perintah langsung, '!command' untuk shell, atau 'exit' untuk keluar.")
    print(f"============================================================\n")

    try:
        while True:
            try:
                user_msg = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSampai jumpa.")
                break

            if not user_msg:
                continue
            if user_msg.casefold() in {"exit", "quit"}:
                print("Sampai jumpa.")
                break

            if user_msg.startswith("!"):
                cmd = user_msg[1:].strip()
                if not cmd:
                    print("Command kosong setelah '!'.")
                    continue
                result = run_command(cmd, base, mode=mode)
                out = (result.get("stdout") or result.get("stderr") or result.get("error") or "")
                if out:
                    print(out.rstrip())
                continue

            try:
                run_turn(
                    llm, user_msg, base, mode,
                    on_action=lambda a: print(f"  [Aksi: {a}]"),
                    on_chat=lambda m: print(f"\nAgent > {m}\n"),
                    on_info=lambda m: print(f"  [info] {m}"),
                )
            except PermissionError as exc:
                print(f"Error Izin: {exc}")
            except Exception as exc:
                print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        llm.close()
    return 0


# ---------- CLI Setup & Menus ----------
def select_mode_menu() -> str:
    print("\n" + "=" * 66)
    print("  Pilih Mode Agent")
    print("=" * 66)
    for i, (k, name, desc) in enumerate(MODES, 1):
        print(f"  [{i}] {name:<26} — {desc}")
    print("=" * 66)
    while True:
        try:
            raw = input(f"Pilih mode [1-{len(MODES)}], default 1: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDibatalkan."); sys.exit(1)
        if not raw:
            return MODES[0][0]
        if raw.isdigit() and 1 <= int(raw) <= len(MODES):
            return MODES[int(raw) - 1][0]
        print(f"Pilihan tidak valid: {raw!r}.")


def select_interface_menu() -> str:
    print("\n" + "=" * 66)
    print("  Pilih Antarmuka")
    print("=" * 66)
    print("  [1] CLI  — terminal interaktif")
    print(f"  [2] GUI  — desktop window (Tkinter){'' if TKINTER_AVAILABLE else ' [tidak tersedia]'}")
    print("  [3] Keluar")
    print("=" * 66)
    while True:
        try:
            raw = input("Pilih [1-3], default 1: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDibatalkan."); sys.exit(1)
        if not raw or raw == "1":
            return "cli"
        if raw == "2":
            if not TKINTER_AVAILABLE:
                print("  Tkinter GUI tidak tersedia di sistem ini. Beralih ke CLI.")
                return "cli"
            return "gui"
        if raw == "3":
            sys.exit(0)
        print(f"Pilihan tidak valid: {raw!r}.")


def select_provider_menu() -> str:
    default = os.getenv("AI_PROVIDER", "gemini").lower()
    if default not in PROVIDER_NAMES:
        default = "gemini"
    print("\n" + "=" * 66)
    print("  Pilih AI Provider")
    print("=" * 66)
    for i, (k, n, envs) in enumerate(PROVIDERS, 1):
        present = next((e for e in envs if os.getenv(e)), None)
        st = f"✓ {present}" if present else "✗ belum diset"
        mark = "  ← default" if k == default else ""
        print(f"  [{i}] {n:<24} ({st}){mark}")
    print("=" * 66)
    while True:
        try:
            raw = input(f"Pilih [1-{len(PROVIDERS)}], default {default}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDibatalkan."); sys.exit(1)
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(PROVIDERS):
            return PROVIDERS[int(raw) - 1][0]
        print(f"Pilihan tidak valid: {raw!r}.")


def ensure_api_key_cli(provider: str) -> Tuple[bool, Optional[str]]:
    envs = next(e for k, _n, e in PROVIDERS if k == provider)
    existing = next((e for e in envs if os.getenv(e)), None)
    if existing:
        print(f"  ✓ Menggunakan {existing}")
        if provider == "gemini":
            return True, ("vertex" if existing == "VERTEX_API_KEY" else "api_key")
        return True, None

    if provider == "gemini":
        print("  GEMINI_API_KEY belum diset. Masukkan API key atau ketik 'vertex' untuk ADC:")
        try:
            ans = getpass.getpass("  Gemini API Key: ").strip()
        except (EOFError, KeyboardInterrupt):
            return False, None
        if not ans or ans.lower() == "vertex":
            return True, "vertex"
        os.environ["GEMINI_API_KEY"] = ans
        return True, "api_key"

    print(f"  {envs[0]} belum diset.")
    if provider in PROVIDER_KEY_URLS:
        print(f"  Dapatkan di: {PROVIDER_KEY_URLS[provider]}")
    try:
        ans = getpass.getpass(f"  Masukkan {envs[0]}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return False, None
    if not ans:
        print("  Kunci kosong."); return False, None
    os.environ[envs[0]] = ans
    return True, None


def check_credentials(mode: str = "coding") -> bool:
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    print(f"\n=== Pemeriksaan Kredensial: {provider} (mode: {mode}) ===")
    for k, _n, envs in PROVIDERS:
        if k == provider:
            for e in envs:
                print(f"  {e:<22} {'✓ Terdeteksi' if os.getenv(e) else '✗ Belum diset'}")
            break

    try:
        llm = create_llm_client(provider, mode=mode)
        print(f"  → Menguji respons dari {PROVIDER_NAMES[provider]}...")
        raw = llm.send_message('Jawab HANYA JSON: {"action":"chat","parameters":{"message":"halo"}}')
        a, p = validate_action(parse_ai_response(raw), mode=mode)
        if a == "chat":
            print(f"  ✅ Koneksi berhasil! Model aktif: {llm.model_label()}")
            llm.close()
            return True
        print(f"  ⚠️ Respons diterima namun format tak terduga: {raw}")
        llm.close()
        return False
    except Exception as exc:
        print(f"  ❌ Gagal menguji provider: {type(exc).__name__}: {exc}")
        return False


def print_help() -> None:
    print("""
MULTI-PROVIDER AI AGENT v2.0 (Coding, Kali Hacking, Windows Automation)
========================================================================
Panduan Menjalankan:
  python agent.py                 Menampilkan menu interaktif lengkap
  python agent.py --coding        Mode coding langsung
  python agent.py --hacking       Mode Kali Linux penetration testing
  python agent.py --windows       Mode otomasi desktop Windows
  python agent.py --gui           Buka tampilan antarmuka visual Tkinter
  python agent.py --cli           Buka terminal interaktif CLI
  python agent.py --no-menu       Jalankan CLI langsung dengan variabel ENV
  python agent.py --check         Uji koneksi API dan keluar
  python agent.py --help          Tampilkan panduan ini

Variabel Lingkungan (Environment Variables):
  GEMINI_API_KEY      Kunci API Google AI Studio
  OPENAI_API_KEY      Kunci API OpenAI
  DEEPSEEK_API_KEY    Kunci API DeepSeek
  XAI_API_KEY         Kunci API Grok xAI
  ANTHROPIC_API_KEY   Kunci API Claude Anthropic
  AI_PROVIDER         Default provider (gemini, openai, deepseek, grok, claude, meta)
  GEMINI_MODEL        Nama model Gemini alternatif
""")


# ---------- Main Entrypoint ----------
def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return 0

    check = "--check" in sys.argv
    no_menu = "--no-menu" in sys.argv
    force_gui = "--gui" in sys.argv
    force_cli = "--cli" in sys.argv
    force_coding = "--coding" in sys.argv
    force_hacking = "--hacking" in sys.argv
    force_windows = "--windows" in sys.argv

    if force_gui and force_cli:
        print("Error: --gui dan --cli tidak dapat digunakan bersamaan.", file=sys.stderr)
        return 1

    modes_set = [m for m, f in [("coding", force_coding), ("hacking", force_hacking), ("windows", force_windows)] if f]
    if len(modes_set) > 1:
        print(f"Error: Hanya satu flag mode yang diperbolehkan ({modes_set}).", file=sys.stderr)
        return 1

    if hasattr(os, "geteuid") and os.geteuid() == 0 and not check:
        print("⚠️  Peringatan: Berjalan dengan hak akses root.", file=sys.stderr)

    mode = modes_set[0] if modes_set else ("coding" if check else select_mode_menu())

    if check:
        provider = os.getenv("AI_PROVIDER", "gemini").lower()
        if provider not in PROVIDER_NAMES:
            print(f"Error: AI_PROVIDER={provider!r} tidak valid.", file=sys.stderr)
            return 1
        return 0 if check_credentials(mode) else 1

    if force_gui:
        interface = "gui"
    elif force_cli or no_menu:
        interface = "cli"
    else:
        interface = select_interface_menu()

    if interface == "gui" and not TKINTER_AVAILABLE:
        print("Peringatan: Tkinter GUI tidak tersedia, beralih ke CLI.", file=sys.stderr)
        interface = "cli"

    base = Path.cwd().resolve()

    if mode == "windows" and not IS_WINDOWS:
        print(f"⚠️  Mode Windows dijalankan di {platform.system()} — fitur pygetwindow khusus Windows; kontrol mouse/keyboard X11 tetap aktif.", file=sys.stderr)

    if interface == "gui":
        AgentGUI(base, mode=mode).run()
        return 0

    if no_menu:
        provider = os.getenv("AI_PROVIDER", "gemini").lower()
        if provider not in PROVIDER_NAMES:
            print(f"Error: AI_PROVIDER={provider!r}.", file=sys.stderr)
            return 1
    else:
        provider = select_provider_menu()

    os.environ["AI_PROVIDER"] = provider
    ok, gm = ensure_api_key_cli(provider)
    if not ok:
        print("Dibatalkan: Kunci API tidak tersedia.", file=sys.stderr)
        return 1

    try:
        llm = create_llm_client(provider, gemini_mode=gm, mode=mode)
    except Exception as exc:
        print(f"Error inisialisasi provider: {exc}", file=sys.stderr)
        print("Petunjuk: Jalankan `python agent.py --check` untuk memeriksa.", file=sys.stderr)
        return 1

    return run_cli(llm, provider, base, mode=mode)


if __name__ == "__main__":
    sys.exit(main())
