const { app, BrowserWindow, screen } = require('electron'); // <-- Import 'screen'
const path = require('path');

function createWindow () {
  // --- THIS IS THE FIX ---
  // 1. Get the primary screen's size
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // 2. Create the window to match the full screen size
  const mainWindow = new BrowserWindow({
    width: width,
    height: height,
    // ---
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    transparent: true,
    frame: false,
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