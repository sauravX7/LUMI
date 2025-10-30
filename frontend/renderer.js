// This script runs in the index.html window

// --- THIS IS THE FIX ---
// We use require() to load 'three' and the GLTFLoader
// This is the correct way in Electron.
const THREE = require('three');
const { GLTFLoader } = require('three/examples/jsm/loaders/GLTFLoader.js');
// --- END OF FIX ---

// 1. --- SETUP THE 3D SCENE ---
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true }); // alpha: true makes it transparent

renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(0, 1, 1);
scene.add(directionalLight);

camera.position.z = 5;

// 2. --- LOAD THE 3D MODEL ---
const loader = new GLTFLoader(); // This will now work

let avatar;
let originalColor;

loader.load(
  './avatar.glb', // The file you downloaded
  function (gltf) {
    avatar = gltf.scene;
    avatar.scale.set(1.5, 1.5, 1.5);
    scene.add(avatar);
    
    avatar.traverse((node) => {
      if (node.isMesh) {
        originalColor = node.material.color.clone();
      }
    });
  },
  undefined,
  function (error) {
    console.error(error);
  }
);

// 3. --- ANIMATION LOOP ---
function animate() {
  requestAnimationFrame(animate);
  if (avatar) {
    avatar.rotation.y += 0.005;
  }
  renderer.render(scene, camera);
}
animate();

// 4. --- HANDLE CLICK EVENT ---
let isListening = false;

window.addEventListener('click', () => {
  if (isListening || !avatar) return;

  isListening = true;
  
  avatar.traverse((node) => {
    if (node.isMesh) node.material.color.set(0xff0000); // Set color to red
  });
  
  // Call our Python backend
  fetch('http://127.0.0.1:5001/listen', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      console.log('Got response from Python:', data);
      isListening = false;
      if (avatar) {
        avatar.traverse((node) => {
          if (node.isMesh) node.material.color.set(originalColor); // Reset color
        });
      }
    })
    .catch(error => {
      console.error('Error calling Python server:', error);
      isListening = false;
       if (avatar) {
        avatar.traverse((node) => {
          if (node.isMesh) node.material.color.set(originalColor); // Reset color
        });
      }
    });
});