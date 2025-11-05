const { contextBridge } = require('electron');

// Expose a new, smarter function to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
  
  // This function will handle the full fetch AND the .json() part
  invokeAPI: async (url, options) => {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        // Handle server errors (like 500)
        throw new Error(`Server returned status: ${response.status}`);
      }
      const data = await response.json(); // <-- Do the .json() conversion here
      return data; // <-- Return the clean data
    } catch (error) {
      // Handle network errors (like server not running)
      console.error('Fetch error in preload:', error);
      throw error;
    }
  },
  invokeFileUpload: async (url, formData) => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        // We DO NOT set Content-Type; browser does it for FormData
      });
      if (!response.ok) {
        throw new Error(`Server returned status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('File upload error in preload:', error);
      throw error;
    }
  }
});