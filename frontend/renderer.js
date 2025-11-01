// This script runs in the index.html window
let isListening = false;
let isFirstRun = true; // To clear the "Welcome" message

// Get the UI elements
const lumiUI = document.getElementById('lumi-ui');
const responseBox = document.getElementById('response-box');

// Attach the click listener to the LUMI orb
lumiUI.addEventListener('click', () => {
  if (isListening) return; // Don't do anything if already listening

  isListening = true;
  lumiUI.classList.add('listening'); // Add CSS class
  
  if (isFirstRun) {
    responseBox.innerHTML = ""; // Clear the box
    isFirstRun = false;
  }
  
  const listeningP = document.createElement('p');
  listeningP.className = 'user-message';
  listeningP.innerText = "Listening...";
  responseBox.appendChild(listeningP);
  responseBox.scrollTop = responseBox.scrollHeight; // Auto-scroll

  // --- THIS IS THE FIX ---
  // Call our new 'invokeAPI' function and get the JSON data directly
  window.electronAPI.invokeAPI('http://127.0.0.1:5001/listen', { method: 'POST' })
    .then(data => { // <-- 'data' is now the JSON object, not the 'response'
  // --- END OF FIX ---
      
      console.log('Got response from Python:', data);
      
      responseBox.removeChild(listeningP);
      
      if (data.user_text) {
        const userP = document.createElement('p');
        userP.className = 'user-message';
        userP.innerText = `You: ${data.user_text}`;
        responseBox.appendChild(userP);
      }
      
      const aiP = document.createElement('p');
      aiP.className = 'ai-message';
      aiP.innerText = `LUMI: ${data.full_text}`;
      responseBox.appendChild(aiP);
      
      responseBox.scrollTop = responseBox.scrollHeight;
      
      isListening = false;
      lumiUI.classList.remove('listening');
    })
    .catch(error => {
      console.error('Error calling Python server:', error);
      
      responseBox.removeChild(listeningP);
      
      const errorP = document.createElement('p');
      errorP.className = 'ai-message';
      errorP.style.color = '#ff4d4d';
      errorP.innerText = 'LUMI: Error: Could not connect to the brain.';
      responseBox.appendChild(errorP);
      responseBox.scrollTop = responseBox.scrollHeight;
      
      isListening = false;
      lumiUI.classList.remove('listening');
    });
});