const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

function createWindow () {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  const mainWindow = new BrowserWindow({
    width: width,
    height: height,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    
    // --- THIS IS THE FIX ---
    transparent: true,      // MUST be true for backdrop-filter
    frame: false,
    vibrancy: undefined,    // MUST be off
    backgroundColor: '#00000000', // Fully transparent
    // --- END OF FIX ---

    alwaysOnTop: true,
    focusable: true,
    skipTaskbar: true
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});