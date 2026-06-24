import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

export default function HeroScene() {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 9;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    mount.appendChild(renderer.domElement);

    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.9, 0.55, 0.18));

    const helix = new THREE.Group();
    const sphereGeometry = new THREE.SphereGeometry(0.075, 20, 20);
    const tealMaterial = new THREE.MeshStandardMaterial({
      color: 0x00e5cc,
      emissive: 0x00e5cc,
      emissiveIntensity: 1.6,
      roughness: 0.2,
      metalness: 0.35,
    });

    for (let i = 0; i < 86; i += 1) {
      const y = (i - 43) * 0.105;
      const angle = i * 0.34;
      [0, Math.PI].forEach((offset) => {
        const sphere = new THREE.Mesh(sphereGeometry, tealMaterial);
        sphere.position.set(Math.cos(angle + offset) * 1.15, y, Math.sin(angle + offset) * 1.15);
        helix.add(sphere);
      });
    }
    scene.add(helix);

    const particleGeometry = new THREE.BufferGeometry();
    const particleCount = 700;
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 18;
      positions[i + 1] = (Math.random() - 0.5) * 12;
      positions[i + 2] = (Math.random() - 0.5) * 14;
    }
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({ color: 0xf0f4f8, size: 0.018, transparent: true, opacity: 0.58 }),
    );
    scene.add(particles);

    scene.add(new THREE.AmbientLight(0xbfefff, 0.55));
    const pointLight = new THREE.PointLight(0x00e5cc, 55, 22);
    pointLight.position.set(3, 3, 5);
    scene.add(pointLight);

    const mouse = { x: 0, y: 0 };
    const onMouseMove = (event) => {
      mouse.x = (event.clientX / window.innerWidth - 0.5) * 0.35;
      mouse.y = (event.clientY / window.innerHeight - 0.5) * 0.25;
    };
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      composer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('resize', onResize);

    let frameId = 0;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      helix.rotation.y += 0.004;
      helix.rotation.x += (mouse.y - helix.rotation.x) * 0.02;
      helix.rotation.z += (mouse.x - helix.rotation.z) * 0.02;
      particles.rotation.y -= 0.0008;
      composer.render();
    };
    animate();

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      mount.removeChild(renderer.domElement);
      sphereGeometry.dispose();
      tealMaterial.dispose();
      particleGeometry.dispose();
      renderer.dispose();
    };
  }, []);

  return <div ref={mountRef} className="fixed inset-0 z-0 h-screen w-screen" />;
}
