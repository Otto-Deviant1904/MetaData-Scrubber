const API_URL = 'http://localhost:5000';

const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const previewImg = document.getElementById('previewImg');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');
const statsCard = document.getElementById('statsCard');
const scrubBtn = document.getElementById('scrubBtn');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');
const loading = document.getElementById('loading');

let selectedFile = null;
let scrubbedBlob = null;

// Handle file selection
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    
    if (file && file.type.startsWith('image/')) {
        selectedFile = file;
        
        const reader = new FileReader();
        reader.onload = function(event) {
            previewImg.src = event.target.result;
            preview.style.display = 'block';
            
            // Reset UI
            statusIcon.textContent = '⏳';
            const sizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);
            statusText.textContent = `Image loaded (${sizeMB} MB) - Ready to scrub`;
            statusText.style.color = '#333';
            
            scrubBtn.style.display = 'inline-flex';
            downloadBtn.style.display = 'none';
            statsCard.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
});

// Handle scrub button
scrubBtn.addEventListener('click', async function() {
    if (!selectedFile) return;
    
    loading.style.display = 'flex';
    scrubBtn.disabled = true;
    
    statusText.textContent = 'Processing...';
    
    const startTime = performance.now();
    const originalSizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);
    
    try {
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        const response = await fetch(`${API_URL}/scrub`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to scrub metadata');
        }
        
        scrubbedBlob = await response.blob();
        const endTime = performance.now();
        
        const timeTaken = ((endTime - startTime) / 1000).toFixed(2);
        const finalSizeMB = (scrubbedBlob.size / 1024 / 1024).toFixed(2);
        const sizeChange = ((scrubbedBlob.size - selectedFile.size) / selectedFile.size * 100).toFixed(1);
        
        // Update preview
        const scrubbedURL = URL.createObjectURL(scrubbedBlob);
        previewImg.src = scrubbedURL;
        
        // Update status
        statusText.textContent = 'Metadata successfully removed!';
        statusText.style.color = '#38ef7d';
        
        // Show stats
        statsCard.style.display = 'block';
        document.getElementById('timeStat').textContent = `${timeTaken}s`;
        document.getElementById('originalSizeStat').textContent = `${originalSizeMB} MB`;
        document.getElementById('finalSizeStat').textContent = `${finalSizeMB} MB`;
        
        const changeColor = sizeChange > 0 ? '#e74c3c' : '#38ef7d';
        const changeSymbol = sizeChange > 0 ? '+' : '';
        document.getElementById('changeStat').innerHTML = 
            `<span style="color: ${changeColor}">${changeSymbol}${sizeChange}%</span>`;
        
        // Update buttons
        scrubBtn.style.display = 'none';
        downloadBtn.style.display = 'inline-flex';
        
    } catch (error) {
        statusText.textContent = 'Error: ' + error.message;
        statusText.style.color = '#e74c3c';
        console.error('Error:', error);
    } finally {
        loading.style.display = 'none';
        scrubBtn.disabled = false;
    }
});

// Handle download button
downloadBtn.addEventListener('click', function() {
    if (!scrubbedBlob) return;
    
    const url = URL.createObjectURL(scrubbedBlob);
    const link = document.createElement('a');
    link.href = url;
    
    // Get file extension from blob type
    const extension = scrubbedBlob.type.includes('png') ? 'png' : 'jpg';
    link.download = `scrubbed_image_${Date.now()}.${extension}`;
    
    link.click();
    URL.revokeObjectURL(url);
});

// Handle reset button
resetBtn.addEventListener('click', function() {
    fileInput.value = '';
    selectedFile = null;
    scrubbedBlob = null;
    preview.style.display = 'none';
});

// Drag and drop functionality
const uploadBox = document.querySelector('.upload-box');

uploadBox.addEventListener('dragover', function(e) {
    e.preventDefault();
    uploadBox.style.borderColor = '#764ba2';
    uploadBox.style.background = 'linear-gradient(135deg, #e0e7ff 0%, #cfe2ff 100%)';
});

uploadBox.addEventListener('dragleave', function(e) {
    e.preventDefault();
    uploadBox.style.borderColor = '#667eea';
    uploadBox.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)';
});

uploadBox.addEventListener('drop', function(e) {
    e.preventDefault();
    uploadBox.style.borderColor = '#667eea';
    uploadBox.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)';
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        fileInput.files = e.dataTransfer.files;
        fileInput.dispatchEvent(new Event('change'));
    }
});