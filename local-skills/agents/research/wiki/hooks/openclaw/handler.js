/**
 * Wiki Session Hook for OpenClaw
 *
 * At session end, writes a redacted digest to ~/.llm-wiki/hub/.sessions/digests/
 * and appends high-signal feedback candidates to
 * ~/.llm-wiki/hub/.sessions/feedback/. The hook is conservative: full
 * transcripts are never written by default.
 *
 * Events:
 *   command:new / command:reset   session ended
 */

const fs = require('node:fs/promises');
const path = require('node:path');

const DEBUG = process.env.WIKI_SESSION_HOOK_DEBUG === '1';

const HUB_PATH = (() => {
  const home = process.env.HOME || '/tmp';
  try {
    const configPath = path.join(home, '.config', 'llm-wiki', 'config.json');
    const raw = require('fs').readFileSync(configPath, 'utf-8');
    const config = JSON.parse(raw);
    if (config.hub_path) {
      return config.hub_path.startsWith('~')
        ? path.join(home, config.hub_path.slice(2))
        : config.hub_path;
    }
  } catch {
    // ignore
  }
  return path.join(home, '.llm-wiki', 'hub');
})();

const MAX_EXCERPTS = 5;
const MAX_EXCERPT_LENGTH = 240;
const REDACTION_RULES = [
  [/\b(api[_-]?key|token|secret|password|passwd|authorization|credential)s?\b(\s*[=:]\s*)\S+/gi, '$1$2[REDACTED]'],
  [/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [REDACTED]'],
  [/\bgh[pousr]_[A-Za-z0-9]{16,}\b/g, '[REDACTED]'],
  [/\bxox[baprs]-[A-Za-z0-9-]{10,}\b/g, '[REDACTED]'],
  [/\bAKIA[0-9A-Z]{16}\b/g, '[REDACTED]'],
  [/\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b/g, '[REDACTED-JWT]'],
  [/\b[A-Za-z0-9_-]{40,}\b/g, '[REDACTED-BLOB]'],
];

function isObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function redact(text) {
  let result = String(text);
  for (const [pattern, replacement] of REDACTION_RULES) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

function collectTextFragments(value, out, depth = 0) {
  if (depth > 4 || out.length > 200) return;
  if (typeof value === 'string') {
    out.push(value);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectTextFragments(item, out, depth + 1);
    return;
  }
  if (isObject(value)) {
    if (typeof value.text === 'string') out.push(value.text);
    if ('content' in value) collectTextFragments(value.content, out, depth + 1);
  }
}

function looksLikeFeedback(text) {
  const lower = text.toLowerCase();
  const markers = [
    'remember', 'don\'t forget', 'always', 'never', 'prefer', 'preference',
    'correction', 'correct', 'actually', 'important', 'approval', 'approved',
    'decided', 'decision', 'rule:', 'constraint:', 'must', 'should not'
  ];
  return markers.some((m) => lower.includes(m));
}

function sanitizeExcerpt(line) {
  let excerpt = redact(line.trim()).replace(/```/g, "'''");
  if (excerpt.length > MAX_EXCERPT_LENGTH) {
    excerpt = `${excerpt.slice(0, MAX_EXCERPT_LENGTH)}…`;
  }
  return excerpt;
}

function resolveSessionFilePath(context, workspaceDir) {
  const sessionEntry = isObject(context.previousSessionEntry)
    ? context.previousSessionEntry
    : isObject(context.sessionEntry)
      ? context.sessionEntry
      : {};

  if (typeof sessionEntry.sessionFile === 'string' && sessionEntry.sessionFile.trim()) {
    return sessionEntry.sessionFile;
  }

  const sessionId = typeof sessionEntry.sessionId === 'string' ? sessionEntry.sessionId.trim() : '';
  if (sessionId && workspaceDir) {
    return path.join(workspaceDir, 'sessions', `${sessionId}.jsonl`);
  }

  return undefined;
}

async function scanTranscript(sessionFilePath) {
  let raw;
  try {
    raw = await fs.readFile(sessionFilePath, 'utf-8');
  } catch {
    return { excerpts: [], feedback: [] };
  }

  const excerpts = [];
  const feedback = [];
  const seenExcerpts = new Set();
  const seenFeedback = new Set();

  for (const jsonLine of raw.split('\n')) {
    const trimmed = jsonLine.trim();
    if (!trimmed) continue;

    let entry;
    try {
      entry = JSON.parse(trimmed);
    } catch {
      continue;
    }

    const fragments = [];
    if (isObject(entry.message)) {
      collectTextFragments(entry.message.content, fragments);
    }

    for (const fragment of fragments) {
      for (const line of fragment.split('\n')) {
        if (excerpts.length < MAX_EXCERPTS && line.length > 20 && line.length < 600) {
          const excerpt = sanitizeExcerpt(line);
          if (excerpt && !seenExcerpts.has(excerpt)) {
            seenExcerpts.add(excerpt);
            excerpts.push(excerpt);
          }
        }
        if (looksLikeFeedback(line)) {
          const fb = sanitizeExcerpt(line);
          if (fb && !seenFeedback.has(fb)) {
            seenFeedback.add(fb);
            feedback.push(fb);
          }
        }
      }
    }
  }

  return { excerpts: excerpts.slice(0, MAX_EXCERPTS), feedback: feedback.slice(0, MAX_EXCERPTS) };
}

async function ensureLayout(sessionsDir) {
  for (const rel of ['digests', 'feedback', 'state']) {
    await fs.mkdir(path.join(sessionsDir, rel), { recursive: true });
  }
}

async function writeDigest(sessionsDir, context, sessionFilePath, scan) {
  const now = new Date();
  const sessionId =
    (isObject(context.previousSessionEntry) && context.previousSessionEntry.sessionId) ||
    (isObject(context.sessionEntry) && context.sessionEntry.sessionId) ||
    'unknown';
  const workspace = context.workspace || 'unknown';
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, '');
  const digestPath = path.join(sessionsDir, 'digests', `${ymd}-${workspace}-${sessionId}.md`);

  const lines = [
    '# OpenClaw Session Digest',
    '',
    `- **Session**: ${sessionId}`,
    `- **Workspace**: ${workspace}`,
    `- **Timestamp**: ${now.toISOString()}`,
    `- **Source**: ${sessionFilePath || 'unknown'}`,
    '',
    '## Highlights',
  ];

  if (scan.excerpts.length === 0) {
    lines.push('_No highlights captured._');
  } else {
    lines.push('');
    for (const excerpt of scan.excerpts) {
      lines.push(`- ${excerpt}`);
    }
  }

  lines.push('', '## Feedback candidates');
  if (scan.feedback.length === 0) {
    lines.push('_None detected._');
  } else {
    lines.push('');
    for (const fb of scan.feedback) {
      lines.push(`- ${fb}`);
    }
  }

  await fs.writeFile(digestPath, lines.join('\n') + '\n', 'utf-8');
  return digestPath;
}

async function appendFeedbackQueue(sessionsDir, context, scan) {
  if (scan.feedback.length === 0) return null;
  const queuePath = path.join(sessionsDir, 'feedback', 'pending.jsonl');
  const sessionId =
    (isObject(context.previousSessionEntry) && context.previousSessionEntry.sessionId) ||
    (isObject(context.sessionEntry) && context.sessionEntry.sessionId) ||
    'unknown';

  const entry = {
    timestamp: new Date().toISOString(),
    sessionId,
    workspace: context.workspace || 'unknown',
    excerpts: scan.feedback,
    topicHint: 'dotfiles',
    status: 'pending',
  };

  await fs.appendFile(queuePath, JSON.stringify(entry) + '\n', 'utf-8');
  return queuePath;
}

async function handler(context) {
  const sessionsDir = path.join(HUB_PATH, '.sessions');
  try {
    await ensureLayout(sessionsDir);

    const workspaceDir = context.workspace || process.env.OPENCLAW_WORKSPACE;
    const sessionFilePath = resolveSessionFilePath(context, workspaceDir);

    const scan = await scanTranscript(sessionFilePath);
    const digestPath = await writeDigest(sessionsDir, context, sessionFilePath, scan);
    const queuePath = await appendFeedbackQueue(sessionsDir, context, scan);

    if (DEBUG) {
      console.error(`[wiki-session] digest=${digestPath} queue=${queuePath}`);
    }

    return { ok: true };
  } catch (err) {
    if (DEBUG) {
      console.error('[wiki-session] error:', err);
    }
    return { ok: false, error: String(err) };
  }
}

module.exports = { handler };
