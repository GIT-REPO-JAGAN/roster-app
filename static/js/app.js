// ── Drag & Drop ──────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.style.borderColor = '#3b82f6'; });
dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = ''; });
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.style.borderColor = '';
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

function onFileSelect(e) { if (e.target.files[0]) setFile(e.target.files[0]); }

function setFile(file) {
  if (!file.name.endsWith('.xlsx')) { showError('Please upload a .xlsx file.'); return; }
  document.getElementById('file-name-display').textContent = file.name;
  document.getElementById('file-info').classList.remove('hidden');
  dropZone.classList.add('hidden');
  markStep(2);
}

function clearFile() {
  document.getElementById('roster_file').value = '';
  document.getElementById('file-info').classList.add('hidden');
  dropZone.classList.remove('hidden');
}

// ── Date range summary ───────────────────────────────────────────────────────
document.getElementById('start_date').addEventListener('change', updateDateSummary);
document.getElementById('end_date').addEventListener('change', updateDateSummary);

function updateDateSummary() {
  const s = document.getElementById('start_date').value;
  const e = document.getElementById('end_date').value;
  const el = document.getElementById('date-summary');
  if (s && e) {
    const days = Math.round((new Date(e) - new Date(s)) / 86400000) + 1;
    if (days > 0) {
      el.textContent = `📆 ${days} day${days > 1 ? 's' : ''} selected`;
      el.classList.remove('hidden');
      markStep(3);
    } else {
      el.textContent = '⚠ End date must be after start date';
      el.classList.remove('hidden');
    }
  } else {
    el.classList.add('hidden');
  }
}

// ── Step tracker ─────────────────────────────────────────────────────────────
function markStep(n) {
  document.querySelectorAll('.step-item').forEach((el, i) => {
    el.classList.toggle('active', i + 1 === n || i + 1 < n);
  });
}
document.getElementById('api_key').addEventListener('input', () => {
  if (document.getElementById('api_key').value.trim()) markStep(2);
});

// ── Key visibility ────────────────────────────────────────────────────────────
function toggleKey() {
  const inp = document.getElementById('api_key');
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

// ── Progress helpers ─────────────────────────────────────────────────────────
const STEPS = ['sstep-1','sstep-2','sstep-3','sstep-4'];
let stepTimers = [];

function startProgress() {
  document.getElementById('status-panel').classList.remove('hidden');
  document.getElementById('result-panel').classList.add('hidden');
  document.getElementById('error-panel').classList.add('hidden');
  STEPS.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('done','active');
    el.querySelector('.sstep-icon').textContent = '⏳';
  });
  setProgress(0);

  const delays = [0, 800, 2200, 4000];
  const progresses = [15, 40, 70, 90];
  STEPS.forEach((id, i) => {
    const t = setTimeout(() => {
      if (i > 0) {
        const prev = document.getElementById(STEPS[i-1]);
        prev.classList.remove('active');
        prev.classList.add('done');
        prev.querySelector('.sstep-icon').textContent = '✅';
      }
      document.getElementById(id).classList.add('active');
      setProgress(progresses[i]);
    }, delays[i]);
    stepTimers.push(t);
  });
}

function finishProgress() {
  stepTimers.forEach(clearTimeout);
  STEPS.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('active');
    el.classList.add('done');
    el.querySelector('.sstep-icon').textContent = '✅';
  });
  setProgress(100);
}

function setProgress(pct) {
  document.getElementById('progress-bar').style.width = pct + '%';
}

// ── Show / hide helpers ──────────────────────────────────────────────────────
function showError(msg) {
  document.getElementById('error-text').textContent = msg;
  document.getElementById('error-panel').classList.remove('hidden');
  document.getElementById('status-panel').classList.add('hidden');
}

// ── Generate ─────────────────────────────────────────────────────────────────
async function generate() {
  const apiKey    = document.getElementById('api_key').value.trim();
  const startDate = document.getElementById('start_date').value;
  const endDate   = document.getElementById('end_date').value;
  const fileInput = document.getElementById('roster_file');

  document.getElementById('error-panel').classList.add('hidden');
  document.getElementById('result-panel').classList.add('hidden');

  if (!apiKey)            { showError('Please enter your Groq API key.'); return; }
  if (!fileInput.files[0]){ showError('Please upload a roster .xlsx file.'); return; }
  if (!startDate)         { showError('Please set a start date.'); return; }
  if (!endDate)           { showError('Please set an end date.'); return; }
  if (new Date(endDate) < new Date(startDate)) { showError('End date must be after start date.'); return; }

  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.querySelector('.btn-label').textContent = 'Generating...';

  startProgress();

  const formData = new FormData();
  formData.append('api_key',     apiKey);
  formData.append('start_date',  startDate);
  formData.append('end_date',    endDate);
  formData.append('roster_file', fileInput.files[0]);

  try {
    const res  = await fetch('/api/generate', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || 'An unknown error occurred.');
    } else {
      finishProgress();
      setTimeout(() => {
        document.getElementById('result-sub').textContent =
          `${data.employee_count} employees × schedule generated successfully.`;
        document.getElementById('btn-download').href = `/api/download/${data.download_id}`;
        document.getElementById('result-panel').classList.remove('hidden');
        markStep(4);
      }, 600);
    }
  } catch (err) {
    showError('Network error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-label').textContent = 'Generate Shift Schedule';
  }
}
