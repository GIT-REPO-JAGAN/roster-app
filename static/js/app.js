// ... (Previous Drag & Drop, Date Summary, and Step Tracker functions remain same) ...

async function generate() {
  const apiKey    = document.getElementById('api_key').value.trim();
  const startDate = document.getElementById('start_date').value;
  const endDate   = document.getElementById('end_date').value;
  const customPrompt = document.getElementById('custom_prompt').value.trim();
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
  formData.append('custom_prompt', customPrompt); // ADDED
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

// ... (Keep all other helper functions like showError, startProgress, etc.) ...
