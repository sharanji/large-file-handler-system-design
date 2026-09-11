const LAST_SESSION_KEY = 'lastUploadSessionId';
const RESUME_KEY = 'pendingChunkedUpload';
// GCS resumable chunks (except the last) must be a multiple of 256 KiB.
const CHUNK_SIZE = 8 * 256 * 1024;

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

function fileFingerprint(file) {
  return `${file.name}|${file.size}|${file.lastModified}`;
}

function loadResume(file) {
  const raw = localStorage.getItem(RESUME_KEY);
  if (!raw) {
    return null;
  }
  try {
    const data = JSON.parse(raw);
    if (data.fingerprint !== fileFingerprint(file)) {
      return null;
    }
    if (data.expires_at && Date.now() > Date.parse(data.expires_at)) {
      localStorage.removeItem(RESUME_KEY);
      return null;
    }
    return data;
  } catch {
    localStorage.removeItem(RESUME_KEY);
    return null;
  }
}

function saveResume(state) {
  localStorage.setItem(RESUME_KEY, JSON.stringify(state));
}

function clearResume() {
  localStorage.removeItem(RESUME_KEY);
}

function parseRangeEnd(rangeHeader) {
  if (!rangeHeader) {
    return -1;
  }
  const match = /bytes=0-(\d+)/.exec(rangeHeader);
  return match ? Number(match[1]) : -1;
}

function queryGcsOffset(uploadUrl, total) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);
    xhr.setRequestHeader('Content-Range', `bytes */${total}`);
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) {
        resolve(total);
        return;
      }
      if (xhr.status === 308) {
        resolve(parseRangeEnd(xhr.getResponseHeader('Range')) + 1);
        return;
      }
      resolve(0);
    };
    xhr.onerror = () => resolve(0);
    xhr.send();
  });
}

function putChunkToGcs(uploadUrl, chunk, start, total, contentType) {
  const endInclusive = start + chunk.size - 1;
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl);
    xhr.setRequestHeader('Content-Type', contentType);
    xhr.setRequestHeader('Content-Range', `bytes ${start}-${endInclusive}/${total}`);
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201 || xhr.status === 308) {
        resolve();
        return;
      }
      reject(new Error(`Cloud upload failed (${xhr.status})`));
    };
    xhr.onerror = () => {
      reject(new Error('Cloud upload failed. Check GCS CORS for this origin.'));
    };
    xhr.send(chunk);
  });
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

async function uploadFileInChunks(file) {
  const contentType = file.type || 'application/octet-stream';
  let resume = loadResume(file);

  if (!resume) {
    const session = await createUploadSession(file);
    resume = {
      fingerprint: fileFingerprint(file),
      session_id: session.session_id,
      upload_url: session.upload_url,
      expires_at: session.expires_at,
      next_offset: 0,
      content_type: contentType,
    };
    saveResume(resume);
  } else {
    const gcsOffset = await queryGcsOffset(resume.upload_url, file.size);
    resume.next_offset = Math.max(resume.next_offset || 0, gcsOffset);
    saveResume(resume);
  }

  let offset = resume.next_offset || 0;
  setProgress(file.size ? (offset / file.size) * 90 : 0);

  if (offset >= file.size) {
    return resume.session_id;
  }

  while (offset < file.size) {
    const end = Math.min(offset + CHUNK_SIZE, file.size);
    const chunk = file.slice(offset, end);
    await putChunkToGcs(resume.upload_url, chunk, offset, file.size, contentType);
    offset = end;
    resume.next_offset = offset;
    saveResume(resume);
    setProgress((offset / file.size) * 90);
  }

  return resume.session_id;
}

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) {
    return;
  }
  const resume = loadResume(file);
  if (resume && (resume.next_offset || 0) > 0 && resume.next_offset < file.size) {
    showAlert(
      uploadStatus,
      'info',
      `Resume ready: ${file.name} will continue from byte ${resume.next_offset} (last failed chunk only).`
    );
  }
});

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
    const sessionId = await uploadFileInChunks(file);
    setProgress(92);
    const complete = await completeUpload(sessionId);
    clearResume();
    localStorage.setItem(LAST_SESSION_KEY, complete.session_id);
    setProgress(100);
    showAlert(
      uploadStatus,
      'success',
      `Uploaded ${file.name}. Indexing is running in the background.`
    );
  } catch (error) {
    showAlert(
      uploadStatus,
      'danger',
      `${error.message} Progress is saved; pick the same file again to retry the last chunk.`
    );
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
