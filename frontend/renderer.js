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

// --- NEW HELPER: Replaces preload.js ---
/**
 * This function now uses window.fetch() directly,
 * bypassing the broken context bridge.
 */
async function invokeAPI(url, options) {
    try {
        const isFormData = options.body instanceof FormData;

        if (!isFormData) {
            // Stringify JSON body
            options.body = JSON.stringify(options.body);
            if (!options.headers) {
                options.headers = {};
            }
            options.headers['Content-Type'] = 'application/json';
        }
        // If it's FormData, we do NOT set Content-Type header

        const response = await fetch(url, options);
        const data = await response.json(); 

        if (!response.ok) {
            throw new Error(data.message || `Server returned status: ${response.status}`);
        }
        return data;

    } catch (error) {
        console.error('Fetch error in renderer:', error);
        throw error;
    }
}
// --- END NEW HELPER ---


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
  // --- UPDATED: Using new invokeAPI function ---
  invokeAPI('http://127.0.0.1:5001/listen', { method: 'POST' })
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
      addMessageToChat('error', error.message || 'Could not connect to the brain.');
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
        let options = {
            method: 'POST'
        };

        if (isDocumentMode) {
            // --- Route to Document Q&A ---
            endpoint = 'http://127.0.0.1:5001/ask-document';
            options.body = { user_input: userText };
        } else {
            // --- Route to General Text Command ---
            endpoint = 'http://1.0.0.1:5001/text-command'; // <--- There was a typo here, fixed to 127.0.0.1
            endpoint = 'http://127.0.0.1:5001/text-command';
            options.body = { user_input: userText };
        }
        
        // 2. Start the API call (using new invokeAPI function)
        invokeAPI(endpoint, options)
        .then(data => {
            setProcessingState(false);
            console.log(`Got response from ${endpoint}:`, data);
            addMessageToChat('ai', data.full_text);
        })
        .catch(error => {
            console.error(`Error calling ${endpoint}:`, error);
            setProcessingState(false);
            addMessageToChat('error', error.message || 'Could not connect to the brain.');
        });
    }
});
// --- END OF MODIFIED HANDLER ---


// --- NEW: Document Upload Listeners (MODIFIED) ---
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
});

docUploadInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setProcessingState(true);
    uploadDocBtn.disabled = true; // Disable upload btn during upload
    addMessageToChat('system', `Uploading and processing ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file); // <-- key is 'file'

    // --- THIS IS THE FIX ---
    // We now call our *new* invokeAPI function
    invokeAPI('http://127.0.0.1:5001/upload', {
        method: 'POST',
        body: formData
    })
    // --- END OF FIX ---
        .then(data => {
            setProcessingState(false);
            uploadDocBtn.disabled = false;

            // Handle success
            isDocumentMode = true;
            currentDocumentName = file.name;
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


// --- 3D TILT + GLOW EFFECT ---
responseBox.addEventListener('mousemove', (e) => {
    const rect = responseBox.getBoundingClientRect();
    
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const deltaX = x - centerX;
    const deltaY = y - centerY;
    
    const maxRotate = 8; 
    
    const rotateY = (deltaX / centerX) * maxRotate;
    const rotateX = -(deltaY / centerY) * maxRotate;
    
    responseBox.style.setProperty('--mouse-x', `${x}px`);
    responseBox.style.setProperty('--mouse-y', `${y}px`);
    responseBox.style.setProperty('--rotate-x', `${rotateX}deg`);
    responseBox.style.setProperty('--rotate-y', `${rotateY}deg`);
});

responseBox.addEventListener('mouseenter', () => {
    responseBox.classList.add('hover-active');
});

responseBox.addEventListener('mouseleave', () => {
    responseBox.classList.remove('hover-active');
    
    responseBox.style.setProperty('--rotate-x', '0deg');
    responseBox.style.setProperty('--rotate-y', '0deg');
});

// --- NEW: Initialize Liquid Ether Background ---
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