document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('roster_file');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', e => { 
            e.preventDefault(); 
            dropZone.style.borderColor = '#3b82f6'; 
        });

        dropZone.addEventListener('dragleave', () => { 
            dropZone.style.borderColor = ''; 
        });

        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.style.borderColor = '';
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        });

        fileInput.addEventListener('change', e => {
            if (e.target.files[0]) handleFile(e.target.files[0]);
        });
    }
});

function handleFile(file) {
    if (!file.name.endsWith('.xlsx')) {
        showError('Please upload a .xlsx file.');
        return;
    }
    document.getElementById('file-name-display').textContent = file.name;
    document.getElementById('file-info').classList.remove('hidden');
    document.getElementById('drop-zone').classList.add('hidden');
    markStep(2);
}

function clearFile() {
    document.getElementById('roster_file').value = '';
    document.getElementById('file-info').classList.add('hidden');
    document.getElementById('drop-zone').classList.remove('hidden');
}

function toggleKey() {
    const inp = document.getElementById('api_key');
    inp.type = inp.type === 'password' ? 'text' : 'password';
}

function markStep(n) {
    document.querySelectorAll('.step-item').forEach((el, i) => {
        el.classList.toggle('active', i + 1 === n || i + 1 < n);
    });
}

async function generate() {
    const apiKey = document.getElementById('api_key').value.trim();
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    const customPrompt = document.getElementById('custom_prompt').value.trim();
    const fileInput = document.getElementById('roster_file');

    if (!apiKey || !fileInput.files[0] || !startDate || !endDate) {
        showError('Please complete all required fields.');
        return;
    }

    const btn = document.getElementById('btn-generate');
    btn.disabled = true;
    startProgress();

    const formData = new FormData();
    formData.append('api_key', apiKey);
    formData.append('start_date', startDate);
    formData.append('end_date', endDate);
    formData.append('custom_prompt', customPrompt);
    formData.append('roster_file', fileInput.files[0]);

    try {
        const res = await fetch('/api/generate', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Generation failed');

        finishProgress();
        document.getElementById('result-sub').textContent = `${data.employee_count} employees scheduled.`;
        document.getElementById('btn-download').href = `/api/download/${data.download_id}`;
        document.getElementById('result-panel').classList.remove('hidden');
        markStep(4);
    } catch (err) {
        showError(err.message);
    } finally {
        btn.disabled = false;
    }
}

function showError(msg) {
    document.getElementById('error-text').textContent = msg;
    document.getElementById('error-panel').classList.remove('hidden');
    document.getElementById('status-panel').classList.add('hidden');
}

function startProgress() {
    document.getElementById('status-panel').classList.remove('hidden');
    document.getElementById('result-panel').classList.add('hidden');
    document.getElementById('error-panel').classList.add('hidden');
    document.getElementById('progress-bar').style.width = '30%';
}

function finishProgress() {
    document.getElementById('progress-bar').style.width = '100%';
    setTimeout(() => document.getElementById('status-panel').classList.add('hidden'), 1000);
}
