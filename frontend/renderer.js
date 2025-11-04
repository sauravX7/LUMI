// This script runs in the index.html window
let isListening = false;
let isFirstRun = true; // To clear the "Welcome" message

// Get the UI elements
const lumiUI = document.getElementById('lumi-ui');
const responseBox = document.getElementById('response-box');

// --- THIS FIXES THE ERROR ---
// We now target the *inner* div for text, as defined in index.html
const responseContent = document.getElementById('response-content');
// ---

// Attach the click listener to the LUMI orb
lumiUI.addEventListener('click', () => {
  if (isListening) return; // Don't do anything if already processing

  isListening = true;
  lumiUI.classList.add('listening'); // 1. Add .listening (red pulse)
  
  if (isFirstRun) {
    responseContent.innerHTML = ""; // <-- Fixes error
    isFirstRun = false;
  }
  
  const listeningP = document.createElement('p');
  listeningP.className = 'user-message';
  listeningP.innerText = "Listening...";
  responseContent.appendChild(listeningP); // <-- Fixes error
  responseContent.scrollTop = responseContent.scrollHeight; // <-- Fixes error

  // 2. Start the API call
  window.electronAPI.invokeAPI('http://127.0.0.1:5001/listen', { method: 'POST' })
    .then(data => { 
      // 5. API returns, remove .thinking
      lumiUI.classList.remove('thinking');
      isListening = false;
      
      console.log('Got response from Python:', data);
      
      if (responseContent.contains(listeningP)) { // <-- Fixes error
          responseContent.removeChild(listeningP); // <-- Fixes error
      }
      
      if (data.user_text) {
        const userP = document.createElement('p');
        userP.className = 'user-message';
        userP.innerText = `You: ${data.user_text}`;
        responseContent.appendChild(userP); // <-- Fixes error
      }
      
      const aiP = document.createElement('p');
      aiP.className = 'ai-message';
      aiP.innerText = `LUMI: ${data.full_text}`;
      responseContent.appendChild(aiP); // <-- Fixes error
      
      responseContent.scrollTop = responseContent.scrollHeight; // <-- Fixes error
    })
    .catch(error => {
      console.error('Error calling Python server:', error);

      lumiUI.classList.remove('thinking');
      lumiUI.classList.remove('listening');
      isListening = false;
      
      if (responseContent.contains(listeningP)) { // <-- Fixes error
          responseContent.removeChild(listeningP); // <-- Fixes error
      }
      
      const errorP = document.createElement('p');
      errorP.className = 'ai-message';
      errorP.style.color = '#ff4d4d'; // Typo fixed (was style..color)
      errorP.innerText = 'LUMI: Error: Could not connect to the brain.';
      responseContent.appendChild(errorP); // <-- Fixes error
      responseContent.scrollTop = responseContent.scrollHeight; // <-- Fixes error
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


// --- 3D TILT + GLOW EFFECT ---
// This code targets the OUTER wrapper ('responseBox')

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
    responseBox.style.setProperty('--mouse-y', `${y}px`);
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


