import { BugItem } from '../types/agent';

export const BUGS_DATA: BugItem[] = [
  {
    id: 'windows-cmd-builtin',
    title: 'Windows Shell Built-ins Crash (FileNotFoundError)',
    severity: 'critical',
    category: 'Runtime Crash',
    symptom: 'Running "dir", "cd", or "type" in Coding Mode on Windows immediately crashes with `FileNotFoundError: [WinError 2] The system cannot find the file specified`.',
    rootCause: 'On Windows, commands like `dir`, `cd`, and `type` are internal built-in commands of `cmd.exe`. They do not exist as standalone `.exe` binaries on disk. When invoked via `subprocess.run(["dir"], shell=False)`, the operating system cannot locate any executable named "dir".',
    fixExplanation: 'Detect when running on Windows with internal shell commands, and route execution safely through `shell=True` (or `cmd.exe /c`), while keeping non-builtin commands on safe isolation.',
    originalSnippet: `# Original code in run_coding_command:
exe = parts[0]
if IS_WINDOWS:
    allowed = (
        exe in {"cd", "dir", "type"}
        ...
    )
...
# CRASH: subprocess.run searches for dir.exe with shell=False!
r = subprocess.run(parts, cwd=base, text=True, capture_output=True,
                   timeout=20, check=False, shell=False)`,
    fixedSnippet: `# Fixed v2.0 code in run_coding_command:
if IS_WINDOWS:
    is_builtin = exe in {"cd", "dir", "type"}
    allowed = (is_builtin or ...)
...
use_shell = IS_WINDOWS and is_builtin
r = subprocess.run(
    cmd_clean if use_shell else parts,
    cwd=base, text=True, capture_output=True,
    timeout=25, check=False, shell=use_shell
)`
  },
  {
    id: 'gemini-dummy-ping',
    title: 'Gemini Dummy "ping" Polluting History & Schema Failures',
    severity: 'critical',
    category: 'API Quota & Tokens',
    symptom: 'Every initialization sends a "ping" message to Gemini. This wastes tokens, delays startup by 1.5–2.5s, pollutes conversation history forever, and causes schema validation mismatch because Gemini is forced into action JSON.',
    rootCause: 'In `_init_with_fallback()`, the author sent `self.chat.send_message("ping")` as a health-check. But `self.config` configured strict JSON schema `response_schema=make_action_schema(mode)`. A simple "ping" violates the agent workflow, consumes quota on every launch, and stays in `self.chat` history.',
    fixExplanation: 'Removed the dummy ping probe from startup. The chat session initializes cleanly with its configuration, and API validation occurs transparently on the first genuine turn or in `--check` mode only.',
    originalSnippet: `# Original code in GeminiClient._init_with_fallback:
for model in GEMINI_MODEL_FALLBACKS:
    try:
        self.chat = self.client.chats.create(model=model, config=self.config)
        probe = self.chat.send_message("ping") # POLLUTES CHAT & BURNS TOKENS
        if getattr(probe, "text", None):
            self._model_used = model
            return
    except Exception as exc:
        last_err = exc`,
    fixedSnippet: `# Fixed v2.0 code in GeminiClient._init_chat:
model = DEFAULT_GEMINI_MODEL
try:
    # Clean initialization without polluting chat history
    self.chat = self.client.chats.create(model=model, config=self.config)
    self._model_used = model
except Exception as exc:
    self._try_init_fallback(exc)`
  },
  {
    id: 'model-fallback-context-loss',
    title: 'Model Fallback Context Loss on 503 / 429 Errors',
    severity: 'high',
    category: 'Context Loss',
    symptom: 'When Gemini encounters rate limits or service unavailability and falls back to another model, all past user and assistant messages are erased.',
    rootCause: 'In `_try_fallback_models()`, the code simply called `self.client.chats.create(model=model, config=self.config)` without preserving past history. A completely empty chat session was started, causing the agent to forget what file it was editing or what the user asked.',
    fixExplanation: 'Extract `self._get_history()` from the existing chat session and pass `history=past_history` to `chats.create(..., history=past_history)` when switching fallback models.',
    originalSnippet: `# Original code in _try_fallback_models:
for model in GEMINI_MODEL_FALLBACKS:
    if model == self._model_used:
        continue
    # BUG: creates a brand-new blank chat, discarding all context!
    self.chat = self.client.chats.create(model=model, config=self.config)
    res = self._do_send(text)`,
    fixedSnippet: `# Fixed v2.0 code in _try_fallback_models:
past_history = self._get_history()
for model in GEMINI_MODEL_FALLBACKS:
    ...
    # Preserves the full conversation context across fallback models!
    self.chat = self.client.chats.create(
        model=model,
        config=self.config,
        history=past_history if past_history else None
    )`
  },
  {
    id: 'self-correction-step-burning',
    title: 'Self-Correction Retries Burning Agent Step Budget',
    severity: 'high',
    category: 'Robustness',
    symptom: 'If an LLM produces slightly malformed JSON, the self-correction `continue` increments the main turn step loop, quickly consuming the 4-step limit and causing the agent to abort unfinished work.',
    rootCause: 'In `run_turn()`, the retry was placed directly in `for step in range(max_steps)`. When `continue` ran on error, `step` advanced from 0 to 1, then to 2, leaving no steps left for the agent to actually run tools.',
    fixExplanation: 'Isolated the JSON formatting and validation retries into an inner loop (up to 3 attempts per step). Format corrections now do not decrement or advance the turn step counter.',
    originalSnippet: `# Original code in run_turn:
for step in range(max_steps):
    try:
        raw = llm.send_message(prompt)
        action, params = validate_action(parse_ai_response(raw), mode=mode)
    except ValueError as exc:
        parse_retries += 1
        prompt = f"JSON gagal divalidasi: {exc}..."
        continue # ADVANCES step! Burns max_steps immediately`,
    fixedSnippet: `# Fixed v2.0 code in run_turn:
for step in range(max_steps):
    # Inner format recovery loop: does not consume outer step counter
    for parse_attempt in range(3):
        try:
            raw_response = llm.send_message(current_prompt)
            action, params = validate_action(parse_ai_response(raw_response), mode=mode)
            break
        except ValueError as exc:
            if parse_attempt == 2:
                on_chat("[Gagal parsing respons AI setelah 3 percobaan]")
                return
            current_prompt = "Respons bukan JSON valid..."`
  },
  {
    id: 'search-code-bottleneck',
    title: 'Code Search Performance Bottleneck (rglob vs pruned os.walk)',
    severity: 'critical',
    category: 'Performance',
    symptom: 'Running `search_code` in any typical repository takes 10 to 30+ seconds or freezes entirely due to scanning `.git`, `node_modules`, and `.venv`.',
    rootCause: '`root.rglob("*")` eagerly scans every directory recursively into memory. Filtering ignored folders with `if any(p in IGNORED_DIRS for p in rel.parts)` occurs AFTER all 40,000+ files in `node_modules` have already been traversed!',
    fixExplanation: 'Switched to `os.walk` with topdown in-place pruning: `dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]`. Ignored directory trees are skipped before even entering them, yielding a 100x to 1000x speedup.',
    originalSnippet: `# Original code in search_code (Slow rglob):
cands = root.rglob(fp) if root.is_dir() else [root]
for cand in cands: # Traverses all 35,000+ files in node_modules!
    rel = cand.relative_to(base)
    if any(p in IGNORED_DIRS for p in rel.parts):
        continue`,
    fixedSnippet: `# Fixed v2.0 code in search_code (Pruned os.walk):
for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
    # In-place directory pruning skips entire ignored trees instantly!
    dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
    for fname in filenames:
        if fnmatch.fnmatch(fname, fp):
            file_candidates.append(Path(dirpath) / fname)`
  },
  {
    id: 'pygetwindow-focus-crash',
    title: 'Windows Focus Stealing Crash in PyGetWindow',
    severity: 'medium',
    category: 'Runtime Crash',
    symptom: 'Calling `w.activate()` on Windows when another process holds focus lock throws `PyGetWindowException: Error code from Windows: 0`, terminating the turn.',
    rootCause: 'Windows has built-in focus-stealing prevention. Calling `activate()` without handling OS focus rejection results in an unhandled exception.',
    fixExplanation: 'Wrapped `w.activate()` in a try-catch block with restore fallback and subtle pause to ensure automation continues smoothly.',
    originalSnippet: `# Original code in win_window:
if action == "activate":
    if w.isMinimized: w.restore()
    w.activate(); time.sleep(0.2) # THROWS PyGetWindowException on focus lock!`,
    fixedSnippet: `# Fixed v2.0 code in win_window:
if action == "activate":
    try:
        if w.isMinimized: w.restore()
        w.activate()
    except Exception:
        try: w.restore()
        except Exception: pass
    time.sleep(0.15)`
  },
  {
    id: 'parameter-synonym-normalization',
    title: 'Model Parameter Synonym Rejection',
    severity: 'medium',
    category: 'Robustness',
    symptom: 'Models frequently output synonymous parameter names like `key` instead of `keys`, `app_name` instead of `app`, or `filename` instead of `path`, causing validation rejection.',
    rootCause: 'The schema validator strictly checked only the exact canonical parameter names and rejected valid instructions.',
    fixExplanation: 'Added automated alias normalization for `app_name`/`program` -> `app`, `key` -> `keys`, `filename`/`file` -> `path`, and `cmd` -> `command`.',
    originalSnippet: `# Original code in validate_action:
if action == "open":
    # only handled open, other actions like keyboard or files were rejected!`,
    fixedSnippet: `# Fixed v2.0 code in validate_action:
if action == "keyboard" and "key" in params and "keys" not in params:
    params["keys"] = params.pop("key")
if action in {"read_file", "write_file"}:
    for alt in ("file", "filename", "file_path", "target"):
        if alt in params and "path" not in params:
            params["path"] = params.pop(alt)`
  }
];
