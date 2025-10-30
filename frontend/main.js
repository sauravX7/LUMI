const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow () {
  const mainWindow = new BrowserWindow({
    width: 300,
    height: 350,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    // --- These are the "overlay" settings ---
    transparent: true,  // Makes the window background transparent
    frame: false,       // Removes the window bar (close, minimize, etc.)
    alwaysOnTop: true,  // Makes it float over other windows
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});