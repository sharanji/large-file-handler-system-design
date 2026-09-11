const LAST_SESSION_KEY = 'lastUploadSessionId';

const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');
const progressWrap = document.getElementById('upload-progress-wrap');
const progressBar = document.getElementById('upload-progress');
const uploadStatus = document.getElementById('upload-status');

const searchForm = document.getElementById('search-form');
const queryInput = document.getElementById('query-input');
const limitLastFile = document.getElementById('limit-last-file');
const searchBtn = document.getElementById('search-btn');
const searchStatus = document.getElementById('search-status');
const searchResults = document.getElementById('search-results');

function showAlert(el, type, message) {
  el.className = `alert mt-3 alert-${type}`;
  el.textContent = message;
  el.classList.remove('d-none');
}

function hideAlert(el) {
  el.classList.add('d-none');
}

function setProgress(percent) {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  progressBar.style.width = `${value}%`;
  progressBar.textContent = `${value}%`;
}

async function createUploadSession(file) {
  const response = await fetch('/api/file-handler/create-upload-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
      origin: window.location.origin,
    }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to create upload session');
  }
  return data;
}

function putFileToGcs(uploadUrl, file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setProgress((event.loaded / event.total) * 90);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
        return;
      }
      reject(new Error(`Cloud upload failed (${xhr.status})`));
    };
    xhr.onerror = () => {
      reject(new Error('Cloud upload failed. Check GCS CORS for this origin.'));
    };
    xhr.send(file);
  });
}

async function completeUpload(sessionId) {
  const response = await fetch('/api/file-handler/complete-upload-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to index file');
  }
  return data;
}

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    showAlert(uploadStatus, 'warning', 'Choose a file first.');
    return;
  }

  hideAlert(uploadStatus);
  uploadBtn.disabled = true;
  progressWrap.classList.remove('d-none');
  setProgress(5);

  try {
    const session = await createUploadSession(file);
    await putFileToGcs(session.upload_url, file);
    setProgress(92);
    const complete = await completeUpload(session.session_id);
    localStorage.setItem(LAST_SESSION_KEY, complete.session_id);
    setProgress(100);
    showAlert(
      uploadStatus,
      'success',
      `Uploaded ${file.name}. Indexing is running in the background.`
    );
  } catch (error) {
    showAlert(uploadStatus, 'danger', error.message);
  } finally {
    uploadBtn.disabled = false;
  }
});

function renderHits(hits) {
  searchResults.innerHTML = '';
  hits.forEach((hit) => {
    const item = document.createElement('li');
    item.className = 'list-group-item';
    const title = document.createElement('div');
    title.className = 'fw-semibold';
    title.textContent = `${hit.filename || 'file'} · lines ${hit.line_start}–${hit.line_end}`;
    item.appendChild(title);
    const snippets = hit.snippets && hit.snippets.length ? hit.snippets : ['No snippet'];
    snippets.forEach((snippet) => {
      const p = document.createElement('p');
      p.className = 'mb-1 small';
      p.innerHTML = snippet;
      item.appendChild(p);
    });
    searchResults.appendChild(item);
  });
}

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    showAlert(searchStatus, 'warning', 'Enter a word to search.');
    return;
  }

  hideAlert(searchStatus);
  searchResults.innerHTML = '';
  searchBtn.disabled = true;

  const payload = { query };
  if (limitLastFile.checked) {
    const sessionId = localStorage.getItem(LAST_SESSION_KEY);
    if (!sessionId) {
      showAlert(searchStatus, 'warning', 'Upload a file first, or uncheck “last uploaded file”.');
      searchBtn.disabled = false;
      return;
    }
    payload.session_id = sessionId;
  }

  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Search failed');
    }
    if (!data.hits.length) {
      showAlert(searchStatus, 'info', `No matches for “${query}”.`);
      return;
    }
    showAlert(searchStatus, 'success', `${data.total} matching chunk(s).`);
    renderHits(data.hits);
  } catch (error) {
    showAlert(searchStatus, 'danger', error.message);
  } finally {
    searchBtn.disabled = false;
  }
});
