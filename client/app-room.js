import * as THREE from 'three';
import { OrbitControls }   from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { createVRMAnimationClip, VRMAnimationLoaderPlugin, VRMLookAtQuaternionProxy } from '@pixiv/three-vrm-animation';

import { VRM_PATH, WS_URL }       from './config.js';
import { loadVRM }                from './vrmLoader.js';
import { AudioManager }           from './audioManager.js';
import { AnimationManager }       from './animationManager.js';
import { loadMixamoAnimation } from './loadMixamoAnimation.js';
import { showSubtitleStreaming } from './subtitles.js';

// Global variables
let currentMixer = null;
let vrm = null;
let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let animationMgr = null; // ADD THIS
const clock = new THREE.Clock();
let currentVrm = null;
let currentAction = null;

(async () => {
  // — Renderer / Scene / Camera —

  // TRANSPARENT BACKGROUND ALPHA 
  renderer = new THREE.WebGLRenderer({ alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);

  // SCENE
  scene = new THREE.Scene();


      // load in room 
  const glbloader = new GLTFLoader();

    glbloader.load('./backgrounds/glb/anime_class_room.glb', function(gltf) {
    const model = gltf.scene;
    model.scale.set(0.45, 0.45, 0.45); // Start with no scale reduction
    model.position.set(-2.7, 0, -0.7); // x,z
    model.rotation.set(0,2.3,0); // use the second number to rorate rooms 
    model.traverse((child) => {
      if (child.isMesh) {
        child.geometry.computeBoundingBox();
        child.geometry.computeBoundingSphere();
        
        child.material.depthWrite = true;
        child.material.depthTest = true;
        child.material.polygonOffset = true;
        child.material.polygonOffsetFactor = -1;
        child.material.polygonOffsetUnits = -1;

        child.updateMatrix();
        child.updateMatrixWorld(true);
        
        child.geometry.computeVertexNormals();
      }});    
    scene.add(model);
  });

  // CAMERA
  camera = new THREE.PerspectiveCamera(30, window.innerWidth/window.innerHeight, 0.1, 20);
  camera.position.set(0,1,0.9);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0,1.1,0);
  controls.update();

  // helpers
  // const gridHelper = new THREE.GridHelper( 10, 10 );
  // scene.add( gridHelper );

  // const axesHelper = new THREE.AxesHelper( 5 );
  // scene.add( axesHelper );

  // — Light —
  const dirLight = new THREE.DirectionalLight(0xffffff, 1);
  dirLight.position.set(3,15,-5);
  scene.add(dirLight);
  scene.add(new THREE.AmbientLight(0xffffff, 2.1));

  // — Load VRM —
  const vrmData = await loadVRM(VRM_PATH, scene);
  vrm = vrmData.vrm;
  const loader = vrmData.loader;
  currentMixer = new THREE.AnimationMixer(vrm.scene);

  // — Managers —
  const audioMgr = new AudioManager(vrm);
  animationMgr = new AnimationManager(vrm, audioMgr, renderer, scene, camera, controls);

  // Start the clock and animation loop
  clock.start();
  
  // SINGLE ANIMATION LOOP THAT HANDLES EVERYTHING
  function animate() {
    requestAnimationFrame(animate);
    const deltaTime = clock.getDelta();
    
    // Update current VRMA mixer if it exists
    if (currentMixer) {
      currentMixer.update(deltaTime);
    }
    
    // Update the animation manager (idle animations)
    if (animationMgr) {
      animationMgr.update(deltaTime);
    }
    
    // Update VRM and render
    vrm.update(deltaTime);
    renderer.render(scene, camera);
    controls.update();
  }
  
  // Start the animation loop once
  animate();

  // — WebSocket Listener —
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    // console.log('WebSocket connected');
    // document.getElementById('status').textContent = 'WS connected';
  };
  ws.onerror = err => console.error('WS error', err);
  ws.onmessage = async ({ data }) => {
    let msg;
    try {
      msg = JSON.parse(data);
      console.log(msg)
    } catch {
      return;
    }
    
    if (msg.type === 'start_animation') {
      const { audio_path, audio_text, audio_duraction, expression = 'neutral' } = msg;
      audioMgr.setExpression(expression);
      try {
        await audioMgr.setupAudio(audio_path);
        await audioMgr.analyzeAudio();
        // SUBTITLE SECTION !!!! UNCOMMENT FOR IN BROWSER MODE, COMMENT OUT FOR OBS MODE
        // stream by word by default, you can stream by letter if you want by adding , "letter"
        // showSubtitleStreaming(audio_text, audio_duraction, "letter"); // 4 seconds total
        // play audio 
        animationMgr.play();
      } catch (e) {
        console.error('Failed to play animation:', e);
      }
    }

    if (msg.type === 'start_vrma') {
      const { animation_url } = msg;
      try {
        // Load VRMA
        const gltfVrma = await loader.loadAsync(animation_url);
        const vrmAnimation = gltfVrma.userData.vrmAnimations[0];

        // Create animation clip
        const clip = createVRMAnimationClip(vrmAnimation, vrm);
        
        // Stop previous mixer if it exists
        // if (currentMixer) {
        //   currentMixer.stopAllAction();
        // }
        
        // Tell AnimationManager that VRMA is playing
        animationMgr.setVRMAPlaying(true);
        
        // Create new mixer and assign to global variable

        // animation blending
        const newAction = currentMixer.clipAction( clip );
        // newAction.setLoop(THREE.LoopOnce, 1);
        newAction.reset().play();


        if ( currentAction && currentAction !== newAction ) {
        currentAction.crossFadeTo( newAction, 0.5, false );
      }

        currentAction = newAction;
        
        // Listen for when the animation finishes
        action.addEventListener('finished', () => {
          animationMgr.setVRMAPlaying(false);
          currentMixer = null;
        });
        
      } catch (err) {
        console.error("Failed to load VRMA animation:", err);
      }
    }


    if (msg.type === 'start_mixamo') {
      const { animation_url } = msg;
      try {
        console.log("THIS IS A MIXAMO ANIMATION")
        console.log(animation_url)
        currentVrm = vrm

        // Load animation
		    const clip = await loadMixamoAnimation( animation_url, currentVrm );

        // animation blending
        const newAction = currentMixer.clipAction( clip );
        newAction.reset().play();

        if ( currentAction && currentAction !== newAction ) {
        currentAction.crossFadeTo( newAction, 0.5, false );
      }

      currentAction = newAction;
	} 

        
      catch (err) {
        console.error("Failed to load MIXAMO animation:", err);
      }
    }
  };

  // — Handle resize —
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth/window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

})();