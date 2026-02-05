const API_URL = 'http://localhost:5000';

const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');
const preview = document.getElementById('preview');
const previewImg = document.getElementById('previewImg');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');
const statsCard = document.getElementById('statsCard');
const scrubBtn = document.getElementById('scrubBtn');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loadingText');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');

let selectedFile = null;
let scrubbedBlob = null;

// Check server health on load
async function checkServerHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
            console.warn('Server health check failed');
        }
    } catch (error) {
        console.error('Cannot connect to server:', error);
        alert(' Cannot connect to backend server. Make sure it\'s running on port 5000.');
    }
}

checkServerHealth();

// Simulate progress for better UX
function simulateProgress(duration) {
    let progress = 0;
    const interval = 50;
    const increment = (interval / duration) * 100;
    
    const progressInterval = setInterval(() => {
        progress += increment;
        if (progress >= 95) {
            progress = 95;
            clearInterval(progressInterval);
        }
        progressFill.style.width = progress + '%';
        progressPercent.textContent = Math.floor(progress) + '%';
    }, interval);
    
    return progressInterval;
}

// Validate file before upload
function validateFile(file) {
    const supportedFormats = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
    const maxSize = 100 * 1024 * 1024; // 100MB
    
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!supportedFormats.includes(ext)) {
        return {
            valid: false,
            error: `Unsupported format: ${ext}`,
            hint: `Supported formats: ${supportedFormats.join(', ')}`
        };
    }
    
    if (file.size > maxSize) {
        return {
            valid: false,
            error: 'File too large',
            hint: `Maximum size: 100MB (your file: ${(file.size / 1024 / 1024).toFixed(2)}MB)`
        };
    }
    
    if (file.size === 0) {
        return {
            valid: false,
            error: 'File is empty',
            hint: 'Choose a valid image file'
        };
    }
    
    return { valid: true };
}

// File selection handler
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    
    if (file) {
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            alert(` ${validation.error}\n\n ${validation.hint}`);
            fileInput.value = '';
            return;
        }
        
        selectedFile = file;
        loadImagePreview(file);
    }
});

function loadImagePreview(file) {
    const reader = new FileReader();
    
    reader.onload = function(event) {
        const img = new Image();
        img.onload = function() {
            previewImg.src = event.target.result;
            preview.style.display = 'block';
            
            // Reset UI
            const sizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);
            statusText.textContent = `Image loaded (${sizeMB} MB) - Ready to scrub`;
            
            scrubBtn.style.display = 'inline-flex';
            downloadBtn.style.display = 'none';
            statsCard.style.display = 'none';
            
            // Store dimensions
            selectedFile.dimensions = { width: img.width, height: img.height };
        };
        img.onerror = function() {
            alert(' Failed to load image preview.\n\n File may be corrupted.');
            fileInput.value = '';
            selectedFile = null;
        };
        img.src = event.target.result;
    };
    
    reader.onerror = function() {
        alert(' Failed to read file.\n\n Check file permissions.');
        fileInput.value = '';
        selectedFile = null;
    };
    
    reader.readAsDataURL(file);
}

// Scrub button handler
scrubBtn.addEventListener('click', async function() {
    if (!selectedFile) return;
    
    // Show loading
    loading.style.display = 'flex';
    scrubBtn.disabled = true;
    
    statusText.textContent = 'Processing...';
    
    // Reset progress
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    
    const startTime = performance.now();
    const originalSizeMB = (selectedFile.size / 1024 / 1024).toFixed(2);
    
    // Start progress simulation
    const progressInterval = simulateProgress(3000);
    
    try {
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        // Update loading text
        loadingText.textContent = 'Removing metadata...';
        
        const response = await fetch(`${API_URL}/scrub`, {
            method: 'POST',
            body: formData
        });
        
        // Handle errors from server
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Server error');
        }
        
        // Get processing time from server
        const serverTime = response.headers.get('X-Processing-Time');
        const metadataRemoved = response.headers.get('X-Metadata-Removed');
        
        scrubbedBlob = await response.blob();
        const endTime = performance.now();
        
        // Complete progress
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';
        
        const totalTime = ((endTime - startTime) / 1000).toFixed(2);
        const finalSizeMB = (scrubbedBlob.size / 1024 / 1024).toFixed(2);
        const sizeChange = ((scrubbedBlob.size - selectedFile.size) / selectedFile.size * 100).toFixed(1);
        const speedMBps = (selectedFile.size / 1024 / 1024 / parseFloat(totalTime)).toFixed(2);
        
        // Update preview
        const scrubbedURL = URL.createObjectURL(scrubbedBlob);
        previewImg.src = scrubbedURL;
        
        // Update status
        statusText.textContent = `${metadataRemoved || 'Metadata'} successfully removed!`;
        
        // Show stats
        statsCard.style.display = 'block';
        document.getElementById('timeStat').textContent = `${totalTime}s`;
        document.getElementById('originalSizeStat').textContent = `${originalSizeMB} MB`;
        document.getElementById('finalSizeStat').textContent = `${finalSizeMB} MB`;
        document.getElementById('dimensionsStat').textContent = 
            `${selectedFile.dimensions.width} × ${selectedFile.dimensions.height}`;
        document.getElementById('speedStat').textContent = `${speedMBps} MB/s`;
        
        const changeColor = sizeChange > 0 ? '#e74c3c' : '#38ef7d';
        const changeSymbol = sizeChange > 0 ? '+' : '';
        document.getElementById('changeStat').innerHTML = 
            `<span style="color: ${changeColor}; font-weight: 900;">${changeSymbol}${sizeChange}%</span>`;
        
        // Update buttons
        scrubBtn.style.display = 'none';
        downloadBtn.style.display = 'inline-flex';
        
        // Celebrate!
        confetti();
        
    } catch (error) {
        clearInterval(progressInterval);
        statusText.textContent = 'Error: ' + error.message;
        console.error('Scrubbing error:', error);
        
        // Show user-friendly error
        alert(` Processing failed\n\n${error.message}\n\n Try a different image or check the server logs.`);
        
    } finally {
        loading.style.display = 'none';
        scrubBtn.disabled = false;
    }
});

// Download button handler
downloadBtn.addEventListener('click', function() {
    if (!scrubbedBlob) return;
    
    const url = URL.createObjectURL(scrubbedBlob);
    const link = document.createElement('a');
    link.href = url;
    
    const extension = scrubbedBlob.type.includes('png') ? 'png' : 
                     scrubbedBlob.type.includes('webp') ? 'webp' : 'jpg';
    const timestamp = new Date().toISOString().slice(0,10);
    link.download = `scrubbed_${timestamp}_${Date.now()}.${extension}`;
    
    link.click();
    URL.revokeObjectURL(url);
});

// Reset button handler
resetBtn.addEventListener('click', function() {
    fileInput.value = '';
    selectedFile = null;
    scrubbedBlob = null;
    preview.style.display = 'none';
    statsCard.style.display = 'none';
});

// Drag and drop functionality
uploadBox.addEventListener('dragover', function(e) {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', function(e) {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', function(e) {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            alert(` ${validation.error}\n\n ${validation.hint}`);
            return;
        }
        
        selectedFile = file;
        loadImagePreview(file);
    }
});

// Simple confetti effect
function confetti() {
    const duration = 2000;
    const end = Date.now() + duration;
    
    (function frame() {
        const timeLeft = end - Date.now();
        
        if (timeLeft <= 0) return;
        
        const particleCount = 3;
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.style.position = 'fixed';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = '-10px';
            particle.style.width = '10px';
            particle.style.height = '10px';
            particle.style.backgroundColor = ['#667eea', '#764ba2', '#38ef7d', '#11998e'][Math.floor(Math.random() * 4)];
            particle.style.borderRadius = '50%';
            particle.style.pointerEvents = 'none';
            particle.style.zIndex = '9999';
            particle.style.animation = 'fall 2s linear';
            
            document.body.appendChild(particle);
            
            setTimeout(() => particle.remove(), 2000);
        }
        
        requestAnimationFrame(frame);
    }());
    
    if (!document.getElementById('confetti-style')) {
        const style = document.createElement('style');
        style.id = 'confetti-style';
        style.textContent = `
            @keyframes fall {
                to {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}