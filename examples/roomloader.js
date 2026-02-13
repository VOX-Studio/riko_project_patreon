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