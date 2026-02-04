const API_URL = 'http://127.0.0.1:5000';

const fileInput = document.getElementById('fileInput');
const dropzone = document.getElementById('dropzone');
const preview = document.getElementById('preview');
const previewImg = document.getElementById('previewImg');
const statusText = document.getElementById('statusText');
const scrubBtn = document.getElementById('scrubBtn');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');
const loading = document.getElementById('loading');

let selectedFile = null;
let scrubbedBlob = null;

/* ---------- CORE FILE HANDLER ---------- */
function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    alert('Please select an image file');
    return;
  }

  selectedFile = file;

  const reader = new FileReader();
  reader.onload = () => {
    previewImg.src = reader.result;
    preview.style.display = 'block';
    statusText.textContent = `Loaded ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    statusText.style.color = '#38d996';
    scrubBtn.style.display = 'inline-flex';
    downloadBtn.style.display = 'none';
  };
  reader.readAsDataURL(file);
}

/* ---------- CLICK UPLOAD ---------- */
dropzone.addEventListener('click', () => {
  fileInput.click();
});

fileInput.addEventListener('change', (e) => {
  handleFile(e.target.files[0]);
});

/* ---------- DRAG & DROP ---------- */
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.style.borderColor = '#4f7cff';
});

dropzone.addEventListener('dragleave', () => {
  dropzone.style.borderColor = '#2c3142';
});

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.style.borderColor = '#2c3142';
  handleFile(e.dataTransfer.files[0]);
});

/* ---------- SCRUB ---------- */
scrubBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  loading.style.display = 'flex';
  statusText.textContent = 'Processing…';

  const formData = new FormData();
  formData.append('image', selectedFile);

  try {
    const res = await fetch(`${API_URL}/scrub`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Upload failed');

    scrubbedBlob = await res.blob();
    previewImg.src = URL.createObjectURL(scrubbedBlob);

    statusText.textContent = 'Metadata removed';
    statusText.style.color = '#38d996';

    scrubBtn.style.display = 'none';
    downloadBtn.style.display = 'inline-flex';

  } catch (err) {
    statusText.textContent = err.message;
    statusText.style.color = '#e74c3c';
  } finally {
    loading.style.display = 'none';
  }
});

/* ---------- DOWNLOAD ---------- */
downloadBtn.addEventListener('click', () => {
  if (!scrubbedBlob) return;
  const url = URL.createObjectURL(scrubbedBlob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `scrubbed_${Date.now()}.jpg`;
  a.click();
  URL.revokeObjectURL(url);
});

/* ---------- RESET ---------- */
resetBtn.addEventListener('click', () => {
  fileInput.value = '';
  selectedFile = null;
  scrubbedBlob = null;
  preview.style.display = 'none';
});
