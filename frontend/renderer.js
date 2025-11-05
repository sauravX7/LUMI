// This script runs in the index.html window
let isListening = false;
let isFirstRun = true; // To clear the "Welcome" message
let isDocumentMode = false; // <-- NEW: Tracks Q&A mode
let currentDocumentName = ""; // <-- NEW: Stores doc name

// Get the UI elements
const lumiUI = document.getElementById('lumi-ui');
const responseBox = document.getElementById('response-box');
const responseContent = document.getElementById('response-content');
const commandInput = document.getElementById('command-input');

// --- NEW: Get Document UI Elements ---
const docStatusText = document.getElementById('doc-status-text');
const uploadDocBtn = document.getElementById('upload-doc-btn');
const clearDocBtn = document.getElementById('clear-doc-btn');
const docUploadInput = document.getElementById('doc-upload-input');
// --- END NEW ---


// --- NEW: Helper function to add messages to the chat ---
function addMessageToChat(author, text) {
  if (isFirstRun) {
    responseContent.innerHTML = "";
    isFirstRun = false;
  }
  
  const p = document.createElement('p');
  
  if (author === 'user') {
    p.className = 'user-message';
    p.innerText = `You: ${text}`;
  } else if (author === 'ai') {
    p.className = 'ai-message';
    p.innerText = `LUMI: ${text}`;
  } else if (author === 'error') {
    p.className = 'ai-message';
    p.style.color = '#ff4d4d';
    p.innerText = `LUMI Error: ${text}`;
  } else if (author === 'system') {
    p.className = 'ai-message';
    p.style.fontStyle = 'italic';
    p.style.opacity = '0.8';
    p.innerText = text;
  }
  
  responseContent.appendChild(p);
  responseContent.scrollTop = responseContent.scrollHeight;
  return p; // Return the element if we need to modify it (like 'Listening...')
}

// --- NEW: Helper to manage processing state ---
function setProcessingState(isProcessing) {
  isListening = isProcessing;
  commandInput.disabled = isProcessing;
  
  if (isProcessing) {
    lumiUI.classList.add('thinking');
  } else {
    lumiUI.classList.remove('thinking');
    lumiUI.classList.remove('listening'); // Ensure listening is also off
    commandInput.focus();
  }
}

// Attach the click listener to the LUMI orb
lumiUI.addEventListener('click', () => {
  if (isListening || isDocumentMode) {
     if(isDocumentMode) {
        addMessageToChat('system', 'In Document Mode. Use text input to ask questions or clear the document session.');
     }
     return;
  }

  isListening = true;
  lumiUI.classList.add('listening'); 
  
  const listeningP = addMessageToChat('system', 'Listening...');

  // 2. Start the API call
  window.electronAPI.invokeAPI('http://127.0.0.1:5001/listen', { method: 'POST' })
    .then(data => { 
      lumiUI.classList.remove('thinking');
      isListening = false;
      
      console.log('Got response from Python:', data);
      
      if (responseContent.contains(listeningP)) { 
          responseContent.removeChild(listeningP); 
      }
      
      if (data.user_text) {
        addMessageToChat('user', data.user_text);
      }
      addMessageToChat('ai', data.full_text);
    })
    .catch(error => {
      console.error('Error calling Python server (listen):', error);
      lumiUI.classList.remove('thinking');
      lumiUI.classList.remove('listening');
      isListening = false;
      
      if (responseContent.contains(listeningP)) { 
          responseContent.removeChild(listeningP); 
      }
      addMessageToChat('error', 'Could not connect to the brain.');
    });
    
  // 3. Start a 5-second timer to match the recording time
  setTimeout(() => {
    if (lumiUI.classList.contains('listening')) {
        lumiUI.classList.remove('listening');
        lumiUI.classList.add('thinking');
        listeningP.innerText = "Thinking...";
    }
  }, 5000); // 5000ms = 5 seconds
});


// --- MODIFIED: Text Input Handling (Now routes based on mode) ---
commandInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        if (isListening) return; 

        const userText = commandInput.value;
        if (!userText) return; 

        setProcessingState(true);
        commandInput.value = ''; // Clear the input

        addMessageToChat('user', userText);

        let endpoint = '';
        let body = {};

        if (isDocumentMode) {
            // --- Route to Document Q&A ---
            endpoint = 'http://127.0.0.1:5001/ask-document';
            body = { user_input: userText };
        } else {
            // --- Route to General Text Command ---
            endpoint = 'http://127.0.0.1:5001/text-command';
            body = { user_input: userText };
        }
        
        // 2. Start the API call
        window.electronAPI.invokeAPI(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(data => {
            setProcessingState(false);
            console.log(`Got response from ${endpoint}:`, data);
            addMessageToChat('ai', data.full_text);
        })
        .catch(error => {
            console.error(`Error calling ${endpoint}:`, error);
            setProcessingState(false);
            addMessageToChat('error', 'Could not connect to the brain.');
        });
    }
});
// --- END OF MODIFIED HANDLER ---


// --- NEW: Document Upload Listeners ---
uploadDocBtn.addEventListener('click', () => {
    docUploadInput.click(); // Trigger the hidden file input
});

clearDocBtn.addEventListener('click', () => {
    isDocumentMode = false;
    currentDocumentName = "";
    docStatusText.innerText = "Chatting with: LUMI (General)";
    clearDocBtn.classList.add('hidden');
    commandInput.placeholder = "Type your command...";
    addMessageToChat('system', 'Document session cleared. You are now talking to LUMI.');
    
    // We can also (optionally) tell the backend to clear its memory,
    // but for now, just changing the frontend state is enough.
    // The backend will just overwrite the chain on the next upload.
});

docUploadInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setProcessingState(true);
    uploadDocBtn.disabled = true; // Disable upload btn during upload
    addMessageToChat('system', `Uploading and processing ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    window.electronAPI.invokeFileUpload('http://127.0.0.1:5001/upload', formData)
        .then(data => {
            setProcessingState(false);
            uploadDocBtn.disabled = false;

            // Handle success
            isDocumentMode = true;
            currentDocumentName = file.name;
            // Truncate name if too long for status bar
            const displayName = currentDocumentName.length > 20 ? currentDocumentName.substring(0, 17) + '...' : currentDocumentName;
            docStatusText.innerText = `Chatting with: ${displayName}`;
            clearDocBtn.classList.remove('hidden');
            commandInput.placeholder = "Ask a question about the document...";
            addMessageToChat('ai', `Successfully loaded ${file.name}. You can now ask questions about it.`);
        })
        .catch(error => {
            setProcessingState(false);
            uploadDocBtn.disabled = false;
            addMessageToChat('error', `Error loading document. ${error.message}`);
        });
    
    // Clear the file input so the 'change' event fires again
    event.target.value = null;
});
// --- END OF NEW LISTENERS ---


// --- 3D TILT + GLOW EFFECT (Unchanged, with typo fix) ---
responseBox.addEventListener('mousemove', (e) => {
    const rect = responseBox.getBoundingClientRect();
    
    // 1. Calculate mouse for GLOW (relative to top-left)
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // 2. Calculate mouse for TILT (relative to center)
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const deltaX = x - centerX;
    const deltaY = y - centerY;
    
    // Define a max rotation
    const maxRotate = 8; 
    
    const rotateY = (deltaX / centerX) * maxRotate;
    const rotateX = -(deltaY / centerY) * maxRotate;
    
    // Set all CSS properties at once
    responseBox.style.setProperty('--mouse-x', `${x}px`);
    
    // --- THIS IS THE FIX ---
    responseBox.style.setProperty('--mouse-y', `${y}px`); // Was ypx
    // --- END OF FIX ---
    
    responseBox.style.setProperty('--rotate-x', `${rotateX}deg`);
    responseBox.style.setProperty('--rotate-y', `${rotateY}deg`);
});

responseBox.addEventListener('mouseenter', () => {
    responseBox.classList.add('hover-active');
});

responseBox.addEventListener('mouseleave', () => {
    responseBox.classList.remove('hover-active');
    
    // Reset tilt properties to let the CSS transition back
    responseBox.style.setProperty('--rotate-x', '0deg');
    responseBox.style.setProperty('--rotate-y', '0deg');
});

window.addEventListener('DOMContentLoaded', () => {
    const bgCanvas = document.getElementById('bg-canvas');
    if (bgCanvas) {
        new LiquidEther(bgCanvas, {
            colors: ['#00e5ff', '#00aaff', '#ffffff'],
            mouseForce: 20,
            cursorSize: 100,
            isViscous: false,
            resolution: 0.5,
            autoDemo: true,
            autoSpeed: 0.5,
            autoIntensity: 2.2
        });
    }
});
