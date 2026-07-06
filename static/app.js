/**
 * app.js – Frontend logic for the Startup Blueprint Generator
 *
 * Responsibilities:
 *  1. Handle form submission and input validation
 *  2. POST to /api/generate and manage loading states
 *  3. Realistic per-agent reveal animation (cards appear one-by-one with timing)
 *  4. Render all 6 blueprint sections as rich cards with markdown formatting
 *  5. Show demo-mode notice when the response has demo_mode: true
 *  6. Copy-to-clipboard and download-as-txt actions
 */

'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// Agent metadata — order matches BlueprintOrchestrator / demo_engine
// ─────────────────────────────────────────────────────────────────────────────
const AGENTS = [
  {
    key:      'startup_plan',
    title:    'Startup Planner',
    subtitle: 'Problem · Value Proposition · Milestones · Next Steps',
    icon:     'SP',
    iconBg:   '#0f62fe',
    label:    'Startup Planner Agent',
  },
  {
    key:      'market_intelligence',
    title:    'Market Intelligence',
    subtitle: 'TAM/SAM/SOM · Competitors · Trends · Customer Segments',
    icon:     'MI',
    iconBg:   '#6929c4',
    label:    'Market Intelligence Agent',
  },
  {
    key:      'business_strategy',
    title:    'Business Strategy',
    subtitle: 'Revenue Model · Competitive Moat · SWOT · 3-Year Roadmap',
    icon:     'BS',
    iconBg:   '#009d9a',
    label:    'Business Strategy Agent',
  },
  {
    key:      'finance_funding',
    title:    'Finance & Funding',
    subtitle: 'Projections · Burn Rate · Funding Rounds · KPIs',
    icon:     'FF',
    iconBg:   '#198038',
    label:    'Finance & Funding Agent',
  },
  {
    key:      'go_to_market',
    title:    'Go-To-Market',
    subtitle: 'Launch Strategy · Channels · User Acquisition · 90-Day Plan',
    icon:     'GM',
    iconBg:   '#9f1853',
    label:    'Go-To-Market Agent',
  },
  {
    key:      'pitch_deck',
    title:    'Pitch Deck',
    subtitle: '10-Slide Narrative · Problem to Vision · Investor Ask',
    icon:     'PD',
    iconBg:   '#b28600',
    label:    'Pitch Deck Agent',
    fullWidth: true,
  },
];

// How long each agent "appears to think" in demo mode (ms).
// Adds up to ~10 s total — realistic for a submission demo.
const AGENT_REVEAL_DELAYS = [1400, 1700, 1600, 1800, 1500, 2000];

// ─────────────────────────────────────────────────────────────────────────────
// DOM references
// ─────────────────────────────────────────────────────────────────────────────
const heroSection     = document.getElementById('hero-section');
const loadingSection  = document.getElementById('loading-section');
const loadingSubtitle = document.getElementById('loading-subtitle');
const resultsSection  = document.getElementById('results-section');
const restartBar      = document.getElementById('restart-bar');
const generateBtn     = document.getElementById('generate-btn');
const ideaInput       = document.getElementById('idea-input');
const industrySelect  = document.getElementById('industry-select');
const stageSelect     = document.getElementById('stage-select');
const errorBanner     = document.getElementById('error-banner');
const blueprintGrid   = document.getElementById('blueprint-grid');
const resultsIdeaText = document.getElementById('results-idea-text');
const demoNotice      = document.getElementById('demo-notice');
const copyBtn         = document.getElementById('copy-btn');
const downloadBtn     = document.getElementById('download-btn');
const newBtn          = document.getElementById('new-btn');
const restartBtn      = document.getElementById('restart-btn');
const footerYear      = document.getElementById('footer-year');

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let _currentBlueprint = null;

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
footerYear.textContent = new Date().getFullYear();
generateBtn.addEventListener('click', handleGenerate);
ideaInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleGenerate();
});
copyBtn.addEventListener('click', handleCopy);
downloadBtn.addEventListener('click', handleDownload);
newBtn.addEventListener('click', showHero);
restartBtn.addEventListener('click', showHero);

// ─────────────────────────────────────────────────────────────────────────────
// Main handler
// ─────────────────────────────────────────────────────────────────────────────
async function handleGenerate() {
  const idea = ideaInput.value.trim();
  if (!idea) {
    showError('Please describe your startup idea before generating a blueprint.');
    ideaInput.focus();
    return;
  }
  if (idea.length < 20) {
    showError('Your idea description seems too short. Add more detail for better results.');
    ideaInput.focus();
    return;
  }

  hideError();
  showLoading();

  const payload = { idea };
  if (industrySelect.value) payload.industry = industrySelect.value;
  if (stageSelect.value)    payload.stage    = stageSelect.value;

  let data;
  try {
    const response = await fetch('/api/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Server error (HTTP ${response.status})`);
    }
  } catch (err) {
    showHero();
    showError(err.message || 'An unexpected error occurred. Please try again.');
    console.error('[Blueprint] Generate error:', err);
    return;
  }

  _currentBlueprint = data;

  // Run the per-agent reveal animation, then show results
  await runRevealAnimation(data);
}

// ─────────────────────────────────────────────────────────────────────────────
// Per-agent reveal animation
// Each agent progress item lights up in sequence, then results appear one-by-one
// ─────────────────────────────────────────────────────────────────────────────
async function runRevealAnimation(data) {
  const isDemo = !!data.demo_mode;
  const totalDelay = isDemo ? AGENT_REVEAL_DELAYS.reduce((a, b) => a + b, 0) : 0;

  // Step 1: animate the progress list items sequentially
  for (let i = 0; i < AGENTS.length; i++) {
    const { key, label } = AGENTS[i];
    const el = document.getElementById(`prog-${key}`);

    // Mark previous done
    if (i > 0) {
      const prev = document.getElementById(`prog-${AGENTS[i - 1].key}`);
      if (prev) {
        prev.classList.remove('running');
        prev.classList.add('done');
        prev.querySelector('.progress-status').textContent = 'Done';
      }
    }

    if (el) {
      el.classList.add('running');
      el.querySelector('.progress-status').textContent = 'Analysing...';
    }

    // Update loading subtitle with agent name
    if (loadingSubtitle) {
      loadingSubtitle.textContent = `${label} is processing your idea...`;
    }

    await sleep(isDemo ? AGENT_REVEAL_DELAYS[i] : 0);
  }

  // Mark last agent done
  const last = document.getElementById(`prog-${AGENTS[AGENTS.length - 1].key}`);
  if (last) {
    last.classList.remove('running');
    last.classList.add('done');
    last.querySelector('.progress-status').textContent = 'Done';
  }
  if (loadingSubtitle) {
    loadingSubtitle.textContent = 'All agents complete. Building your blueprint...';
  }

  await sleep(isDemo ? 600 : 0);

  // Step 2: render results — cards fade in one by one
  renderResults(data);
}

// ─────────────────────────────────────────────────────────────────────────────
// View transitions
// ─────────────────────────────────────────────────────────────────────────────
function showHero() {
  heroSection.style.display   = '';
  loadingSection.classList.remove('active');
  resultsSection.classList.remove('active');
  restartBar.style.display    = 'none';
  demoNotice.style.display    = 'none';
  generateBtn.disabled        = false;
  generateBtn.innerHTML       = '<span class="btn-icon" aria-hidden="true">&#x26A1;</span> Generate Blueprint';
  blueprintGrid.innerHTML     = '';
  if (loadingSubtitle) {
    loadingSubtitle.textContent = 'Our 6 AI agents are working in parallel to analyse your startup idea.';
  }
  ideaInput.focus();
}

function showLoading() {
  heroSection.style.display = 'none';
  loadingSection.classList.add('active');
  resultsSection.classList.remove('active');
  restartBar.style.display  = 'none';
  generateBtn.disabled      = true;

  AGENTS.forEach(({ key }) => {
    const el = document.getElementById(`prog-${key}`);
    if (!el) return;
    el.classList.remove('running', 'done');
    el.querySelector('.progress-status').textContent = 'Pending';
  });
}

function showResults() {
  heroSection.style.display = 'none';
  loadingSection.classList.remove('active');
  resultsSection.classList.add('active');
  restartBar.style.display  = '';
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─────────────────────────────────────────────────────────────────────────────
// Render results
// ─────────────────────────────────────────────────────────────────────────────
function renderResults(data) {
  const { startup_idea, sections, demo_mode } = data;

  resultsIdeaText.textContent = startup_idea;
  blueprintGrid.innerHTML     = '';

  // Demo notice
  if (demoNotice) {
    demoNotice.style.display = demo_mode ? 'flex' : 'none';
  }

  // Build all cards first (hidden), then reveal with staggered animation
  const cards = AGENTS.map((meta, index) => {
    const content = sections[meta.key] || '';
    const isError = content.startsWith('[Agent unavailable');
    const card    = buildCard(meta, index + 1, content, isError, demo_mode);
    card.style.opacity   = '0';
    card.style.transform = 'translateY(12px)';
    card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    blueprintGrid.appendChild(card);
    return card;
  });

  showResults();

  // Staggered card reveal
  cards.forEach((card, i) => {
    setTimeout(() => {
      card.style.opacity   = '1';
      card.style.transform = 'translateY(0)';
    }, i * 120);
  });
}

function buildCard(meta, num, content, isError, isDemo) {
  const article = document.createElement('article');
  article.className = 'agent-card' + (meta.fullWidth ? ' full-width' : '');
  article.setAttribute('role', 'listitem');
  article.setAttribute('aria-label', `${meta.title} section`);

  const demoBadge = isDemo
    ? `<span class="agent-demo-badge" title="Demo mode output">Demo</span>`
    : '';

  article.innerHTML = `
    <div class="agent-card-header">
      <div class="agent-card-icon" style="background:${meta.iconBg}" aria-hidden="true">${escapeHtml(meta.icon)}</div>
      <div class="agent-card-meta">
        <div class="agent-card-title">${escapeHtml(meta.title)}</div>
        <div class="agent-card-subtitle">${escapeHtml(meta.subtitle)}</div>
      </div>
      <div class="agent-card-badges">
        ${demoBadge}
        <span class="agent-card-badge">Agent ${num}</span>
      </div>
    </div>
    <div class="agent-card-body">
      ${isError
        ? `<div class="agent-error">&#x26A0; ${escapeHtml(content)}</div>`
        : `<div class="agent-content">${renderMarkdownLite(content)}</div>`
      }
    </div>
  `;
  return article;
}

// ─────────────────────────────────────────────────────────────────────────────
// Markdown-lite renderer
// ─────────────────────────────────────────────────────────────────────────────
function renderMarkdownLite(text) {
  if (!text) return '';

  const lines = text.split('\n');
  const out   = [];
  let inList  = false;
  let inOl    = false;
  let inTable = false;

  const closeOpen = () => {
    if (inList)  { out.push('</ul>');    inList  = false; }
    if (inOl)    { out.push('</ol>');    inOl    = false; }
    if (inTable) { out.push('</tbody></table>'); inTable = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Table rows: | col | col |
    if (/^\s*\|/.test(line)) {
      const cells = line.split('|').slice(1, -1).map(c => c.trim());
      // Separator row (---|---|---) → skip
      if (cells.every(c => /^[-:]+$/.test(c))) continue;

      if (!inTable) {
        closeOpen();
        // Decide if this is a header row (previous non-empty line was also a |row)
        const prevLine = lines[i - 1] || '';
        const isHeader = /^\s*\|/.test(prevLine) && /^\s*\|[-: |]+\|/.test(lines[i + 1] || '');
        out.push('<div class="table-wrap"><table>');
        if (isHeader) {
          out.push('<thead><tr>');
          cells.forEach(c => out.push(`<th>${inlineStyles(c)}</th>`));
          out.push('</tr></thead><tbody>');
          inTable = true;
          continue;
        }
        out.push('<tbody>');
        inTable = true;
      }
      out.push('<tr>');
      cells.forEach(c => out.push(`<td>${inlineStyles(c)}</td>`));
      out.push('</tr>');
      continue;
    }

    // Headings: ## / ### → h4
    if (/^#{1,3}\s+/.test(line)) {
      closeOpen();
      out.push(`<h4>${inlineStyles(line.replace(/^#{1,3}\s+/, ''))}</h4>`);
      continue;
    }

    // Horizontal rule: --- separator
    if (/^---+$/.test(line.trim())) {
      closeOpen();
      out.push('<hr style="border:none;border-top:1px solid var(--border);margin:1rem 0"/>');
      continue;
    }

    // Bold-only line as heading: **Title**
    if (/^\*\*[^*]+\*\*\s*$/.test(line.trim())) {
      closeOpen();
      const inner = line.trim().replace(/^\*\*|\*\*$/g, '');
      out.push(`<h4>${inlineStyles(inner)}</h4>`);
      continue;
    }

    // Unordered list: - item or * item
    if (/^[-*]\s+/.test(line)) {
      if (inOl)    { out.push('</ol>');  inOl   = false; }
      if (inTable) { out.push('</tbody></table>'); inTable = false; }
      if (!inList) { out.push('<ul>');   inList  = true; }
      out.push(`<li>${inlineStyles(line.replace(/^[-*]\s+/, ''))}</li>`);
      continue;
    }

    // Numbered list: 1. item
    if (/^\d+\.\s+/.test(line)) {
      if (inList)  { out.push('</ul>');  inList  = false; }
      if (inTable) { out.push('</tbody></table>'); inTable = false; }
      if (!inOl)   { out.push('<ol>');   inOl    = true; }
      out.push(`<li>${inlineStyles(line.replace(/^\d+\.\s+/, ''))}</li>`);
      continue;
    }

    // Checklist: - [ ] item
    if (/^-\s+\[[ x]\]\s+/.test(line)) {
      if (inOl)    { out.push('</ol>');  inOl    = false; }
      if (inTable) { out.push('</tbody></table>'); inTable = false; }
      if (!inList) { out.push('<ul class="checklist">'); inList = true; }
      const checked = /\[x\]/i.test(line);
      const label   = line.replace(/^-\s+\[[ x]\]\s+/, '');
      out.push(`<li class="check-item${checked ? ' checked' : ''}">${inlineStyles(label)}</li>`);
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      closeOpen();
      out.push('<br/>');
      continue;
    }

    // Regular paragraph
    closeOpen();
    out.push(`<p>${inlineStyles(line)}</p>`);
  }

  closeOpen();
  return out.join('\n');
}

function inlineStyles(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`(.+?)`/g,       '<code style="font-family:var(--font-mono);background:var(--ibm-gray-10);padding:1px 4px;border-radius:2px;font-size:.85em">$1</code>');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

// ─────────────────────────────────────────────────────────────────────────────
// Copy / Download
// ─────────────────────────────────────────────────────────────────────────────
function buildPlainText(data) {
  const sep   = '='.repeat(64);
  const dash  = '-'.repeat(48);
  const lines = [
    sep,
    'STARTUP BLUEPRINT GENERATOR — IBM watsonx Orchestrate',
    data.demo_mode ? '(Demo Mode — generated locally)' : '(Live — IBM watsonx Orchestrate)',
    sep,
    '',
    'STARTUP IDEA:',
    data.startup_idea,
    '',
    sep,
    '',
  ];

  AGENTS.forEach((meta) => {
    const content = (data.sections || {})[meta.key] || '(no output)';
    lines.push(meta.title.toUpperCase());
    lines.push(dash);
    lines.push(content);
    lines.push('');
    lines.push('');
  });

  lines.push(sep);
  lines.push(`Generated: ${new Date().toLocaleString()}`);
  lines.push(sep);
  return lines.join('\n');
}

async function handleCopy() {
  if (!_currentBlueprint) return;
  const text = buildPlainText(_currentBlueprint);
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
  copyBtn.textContent = '&#x2713; Copied!';
  setTimeout(() => { copyBtn.innerHTML = '&#x1F4CB; Copy Full Blueprint'; }, 2000);
}

function handleDownload() {
  if (!_currentBlueprint) return;
  const text     = buildPlainText(_currentBlueprint);
  const slug     = (_currentBlueprint.startup_idea || 'blueprint')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40);
  const filename = `blueprint-${slug}.txt`;
  const blob     = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url      = URL.createObjectURL(blob);
  const a        = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────────────────────────────────────
// Error banner
// ─────────────────────────────────────────────────────────────────────────────
function showError(msg) {
  errorBanner.textContent = '\u26A0 ' + msg;
  errorBanner.classList.add('active');
}
function hideError() {
  errorBanner.classList.remove('active');
  errorBanner.textContent = '';
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility
// ─────────────────────────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
