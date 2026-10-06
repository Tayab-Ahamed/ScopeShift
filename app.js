// ScopeShift Production Engine
// Modern Light Editorial Design System, Multi-Page Routing, Mobile Responsiveness & 3D Spatial Twin

(function () {
  'use strict';

  // Global App State
  let appState = null;
  let currentBeat = 1;
  let activePageId = 'page-cockpit';
  let diffModeActive = false;
  let prevHeroState = null; // Stream E: hero claim state seen on the last render

  // UI Element Handles
  const stateEl = document.querySelector('#state');
  const reasonEl = document.querySelector('#reason');
  const sourcesEl = document.querySelector('#sources');
  const evidenceEl = document.querySelector('#evidence-ledger');
  const brdEl = document.querySelector('#brd');
  const eventsEl = document.querySelector('#events');
  const extractionModePill = document.querySelector('#extraction-mode-pill');
  const extractionModeText = document.querySelector('#extraction-mode-text');
  const latencyBadge = document.querySelector('#extraction-latency');
  const mirrorEl = document.querySelector('#mirror-note');

  // Page 2
  const claimsGrid = document.querySelector('#matrix-claims-grid');

  // Page 3
  const ingestForm = document.querySelector('#ingest-form');
  const inpSourceType = document.querySelector('#inp-source-type');
  const inpClaimId = document.querySelector('#inp-claim-id');
  const inpText = document.querySelector('#inp-text');
  const inpQuote = document.querySelector('#inp-quote');
  const quoteFeedback = document.querySelector('#quote-feedback');
  const inpScopeChange = document.querySelector('#inp-scope-change');
  const inpValueJson = document.querySelector('#inp-value-json');
  const studioLedgerRows = document.querySelector('#studio-ledger-rows');

  // Page 4
  const brdDocView = document.querySelector('#brd-document-view');
  const brdDiffView = document.querySelector('#brd-diff-view');
  const diffBaselineContent = document.querySelector('#diff-baseline-content');
  const diffGovernedContent = document.querySelector('#diff-governed-content');
  const btnToggleDiff = document.querySelector('#btn-toggle-diff');
  const btnCopyMd = document.querySelector('#btn-copy-md');

  // Page 5
  const scrubber = document.querySelector('#time-scrubber');
  const scrubberSeqBadge = document.querySelector('#scrubber-seq-badge');
  const auditChainRows = document.querySelector('#audit-chain-rows');

  // Navigation & Drawer
  const mobileToggle = document.querySelector('#btn-mobile-toggle');
  const mobileDrawer = document.querySelector('#mobile-drawer');

  // Modals & Toasts
  const artifactModal = document.querySelector('#artifact-modal');
  const modalTitle = document.querySelector('#modal-title');
  const modalBody = document.querySelector('#modal-body');
  const modalClose = document.querySelector('#modal-close');
  const governModal = document.querySelector('#govern-modal');
  const governForm = document.querySelector('#govern-form');
  const governModalClose = document.querySelector('#govern-modal-close');
  const govClaimId = document.querySelector('#gov-claim-id');
  const govDirective = document.querySelector('#gov-directive');
  const govValueJson = document.querySelector('#gov-value-json');
  const chaosToast = document.querySelector('#chaos-toast');
  const toastMessage = document.querySelector('#toast-message');
  const toastClose = document.querySelector('#toast-close');

  // Stream E: keyboard shortcut help overlay
  const helpOverlay = document.querySelector('#help-overlay');
  const helpClose = document.querySelector('#help-close');

  function toggleHelp(show) {
    if (!helpOverlay) return;
    const willShow = typeof show === 'boolean' ? show : helpOverlay.style.display !== 'flex';
    helpOverlay.style.display = willShow ? 'flex' : 'none';
  }

  function closeHelp() {
    if (helpOverlay) helpOverlay.style.display = 'none';
  }

  helpClose?.addEventListener('click', closeHelp);
  helpOverlay?.addEventListener('click', (e) => {
    if (e.target === helpOverlay) closeHelp(); // backdrop click
  });

  // ==========================================================================
  // 1. Interactive 3D Spatial Requirements Twin Engine (Three.js Light Theme)
  // ==========================================================================
  let scene, camera, renderer;
  let nodeGroup, laserGroup, gyroGroup;
  let nodeBRD, nodeScreenshot, nodeNote, gyroCore, ring1, ring2, ring3;
  let clashBeam, clashBarrier, authBeam;
  let isDragging = false, prevMouseX = 0, prevMouseY = 0;
  let targetRotationX = 0.22, targetRotationY = -0.28;
  let twinAnim = { clash: false, beam: false }; // Stream D: driven by real claim states
  const raycaster = new THREE.Raycaster();
  const mouseVec = new THREE.Vector2();

  function init3DMatrix() {
    const container = document.querySelector('#canvas-container');
    if (!container || typeof THREE === 'undefined') return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    scene.fog = new THREE.FogExp2(0xf8fafc, 0.035);

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 6.5, 15);
    camera.lookAt(0, 0, 0);

    renderer = null;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch (err) {
      // Stream D: defensive — a WebGL failure must never break the page.
      console.error('3D twin: WebGL unavailable, hiding viewport (page unaffected):', err);
      container.innerHTML = '<p class="canvas-fallback">3D spatial twin unavailable (WebGL failed to initialize). The evidence ledger below is unaffected.</p>';
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.prepend(renderer.domElement);

    // Subtle Architectural Ground Grid
    const gridHelper = new THREE.GridHelper(30, 30, 0xcbd5e1, 0xe2e8f0);
    gridHelper.position.y = -2;
    scene.add(gridHelper);

    // Soft Ambient & Studio Directional Lights
    const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight1.position.set(12, 18, 12);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x2563eb, 0.3);
    dirLight2.position.set(-12, -8, -12);
    scene.add(dirLight2);

    nodeGroup = new THREE.Group();
    scene.add(nodeGroup);

    // --- 1. Resolver Gyroscope Core at Center (0, 0, 0) ---
    gyroGroup = new THREE.Group();
    scene.add(gyroGroup);

    const coreGeom = new THREE.OctahedronGeometry(1.0, 0);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0xe11d48,
      emissive: 0xe11d48,
      emissiveIntensity: 0.5,
      metalness: 0.8,
      roughness: 0.2,
    });
    gyroCore = new THREE.Mesh(coreGeom, coreMat);
    gyroGroup.add(gyroCore);

    const ringMat = new THREE.MeshBasicMaterial({ color: 0x64748b, wireframe: true });
    ring1 = new THREE.Mesh(new THREE.TorusGeometry(1.6, 0.03, 16, 60), ringMat);
    ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.0, 0.03, 16, 60), ringMat);
    ring3 = new THREE.Mesh(new THREE.TorusGeometry(2.4, 0.03, 16, 60), ringMat);
    gyroGroup.add(ring1);
    gyroGroup.add(ring2);
    gyroGroup.add(ring3);

    // Helper: Create Text Canvas Texture for 3D Node Labels
    function createLabelTexture(label, sub, bgColor, textColor) {
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, 256, 128);
      ctx.strokeStyle = textColor;
      ctx.lineWidth = 6;
      ctx.strokeRect(4, 4, 248, 120);

      ctx.fillStyle = textColor;
      ctx.font = 'bold 22px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(label, 128, 52);

      ctx.font = '16px monospace';
      ctx.fillText(sub, 128, 86);
      return new THREE.CanvasTexture(canvas);
    }

    // --- 2. Node: BRD Baseline Tablet (SRC-01) ---
    const brdGeom = new THREE.BoxGeometry(2.2, 1.4, 0.2);
    const brdTex = createLabelTexture('BRD BASELINE', 'REQ: UPI ONLY', '#ffffff', '#2563eb');
    const brdMat = new THREE.MeshStandardMaterial({
      map: brdTex,
      metalness: 0.2,
      roughness: 0.3,
    });
    nodeBRD = new THREE.Mesh(brdGeom, brdMat);
    nodeBRD.position.set(-5.2, 1.0, -0.8);
    nodeBRD.userData = { id: 'SRC-01', title: 'BRD Baseline (UPI Only)' };
    nodeGroup.add(nodeBRD);

    const brdEdge = new THREE.LineSegments(
      new THREE.EdgesGeometry(brdGeom),
      new THREE.LineBasicMaterial({ color: 0x2563eb, linewidth: 2 })
    );
    nodeBRD.add(brdEdge);

    // --- 3. Node: Staging UI Screen (SRC-02) ---
    const shotGeom = new THREE.BoxGeometry(2.0, 1.4, 0.2);
    const shotTex = createLabelTexture('UI SCREENSHOT', 'BTN: PAY W/ CARD', '#ffffff', '#e11d48');
    const shotMat = new THREE.MeshStandardMaterial({
      map: shotTex,
      metalness: 0.2,
      roughness: 0.3,
    });
    nodeScreenshot = new THREE.Mesh(shotGeom, shotMat);
    nodeScreenshot.position.set(5.2, 1.0, -0.8);
    nodeScreenshot.userData = { id: 'SRC-02', title: 'Staging Screenshot (Card Button)' };
    nodeGroup.add(nodeScreenshot);

    const shotEdge = new THREE.LineSegments(
      new THREE.EdgesGeometry(shotGeom),
      new THREE.LineBasicMaterial({ color: 0xe11d48, linewidth: 2 })
    );
    nodeScreenshot.add(shotEdge);

    // --- 4. Node: Client Scope Directive Memo (SRC-03) ---
    const noteGeom = new THREE.BoxGeometry(2.2, 1.4, 0.2);
    const noteTex = createLabelTexture('CLIENT DIRECTIVE', 'CARD IN SCOPE', '#ffffff', '#059669');
    const noteMat = new THREE.MeshStandardMaterial({
      map: noteTex,
      metalness: 0.2,
      roughness: 0.3,
    });
    nodeNote = new THREE.Mesh(noteGeom, noteMat);
    nodeNote.position.set(0, 3.8, 2.2);
    nodeNote.userData = { id: 'SRC-03', title: 'Client Scope Directive' };
    nodeGroup.add(nodeNote);

    const noteEdge = new THREE.LineSegments(
      new THREE.EdgesGeometry(noteGeom),
      new THREE.LineBasicMaterial({ color: 0x059669, linewidth: 2 })
    );
    nodeNote.add(noteEdge);

    // --- 5. Volumetric Laser Vectors & Conflict Barrier ---
    laserGroup = new THREE.Group();
    scene.add(laserGroup);

    // Clashing Vector from UI Screenshot to Core Barrier
    const clashPoints = [nodeScreenshot.position, new THREE.Vector3(0, 1.0, -0.8), nodeBRD.position];
    const clashGeom = new THREE.BufferGeometry().setFromPoints(clashPoints);
    clashBeam = new THREE.Line(
      clashGeom,
      new THREE.LineBasicMaterial({ color: 0xe11d48, linewidth: 3, transparent: true, opacity: 0.95 })
    );
    laserGroup.add(clashBeam);

    // Conflict Alert Barrier Shield
    const barGeom = new THREE.PlaneGeometry(2.4, 2.4);
    const barMat = new THREE.MeshBasicMaterial({
      color: 0xe11d48,
      transparent: true,
      opacity: 0.25,
      side: THREE.DoubleSide,
      wireframe: true,
    });
    clashBarrier = new THREE.Mesh(barGeom, barMat);
    clashBarrier.position.set(0, 1.0, -0.8);
    laserGroup.add(clashBarrier);

    // Governed Authority vector from client note into Core
    const authPoints = [nodeNote.position, new THREE.Vector3(0, 0, 0)];
    const authGeom = new THREE.BufferGeometry().setFromPoints(authPoints);
    authBeam = new THREE.Line(
      authGeom,
      new THREE.LineBasicMaterial({ color: 0x059669, linewidth: 3, transparent: true, opacity: 0.0 })
    );
    laserGroup.add(authBeam);

    // Mouse / Touch Interaction Controls
    container.addEventListener('mousedown', (e) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    window.addEventListener('mouseup', () => { isDragging = false; });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      targetRotationY += deltaX * 0.005;
      targetRotationX += deltaY * 0.005;
      targetRotationX = Math.max(-0.6, Math.min(0.9, targetRotationX));
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    // Touch Support for Mobile
    container.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        isDragging = true;
        prevMouseX = e.touches[0].clientX;
        prevMouseY = e.touches[0].clientY;
      }
    }, { passive: true });

    window.addEventListener('touchend', () => { isDragging = false; });

    window.addEventListener('touchmove', (e) => {
      if (!isDragging || e.touches.length !== 1) return;
      const deltaX = e.touches[0].clientX - prevMouseX;
      const deltaY = e.touches[0].clientY - prevMouseY;
      targetRotationY += deltaX * 0.006;
      targetRotationX += deltaY * 0.006;
      targetRotationX = Math.max(-0.6, Math.min(0.9, targetRotationX));
      prevMouseX = e.touches[0].clientX;
      prevMouseY = e.touches[0].clientY;
    }, { passive: true });

    // Click on 3D Node (Raycaster)
    container.addEventListener('click', (e) => {
      if (!renderer) return; // twin failed to init — nothing to click
      const rect = renderer.domElement.getBoundingClientRect();
      mouseVec.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseVec.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouseVec, camera);

      const intersects = raycaster.intersectObjects([nodeBRD, nodeScreenshot, nodeNote]);
      if (intersects.length > 0) {
        const hit = intersects[0].object;
        if (hit.userData && hit.userData.id) {
          openArtifactModal(hit.userData.id);
        }
      }
    });

    // Window Resize Handler
    window.addEventListener('resize', () => {
      if (!renderer || !camera || !container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });

    animate3D();
  }

  function animate3D() {
    requestAnimationFrame(animate3D);

    // Smooth camera orbit damping
    scene.rotation.y += (targetRotationY - scene.rotation.y) * 0.08;
    scene.rotation.x += (targetRotationX - scene.rotation.x) * 0.08;

    // Gyroscope rotation
    if (ring1) ring1.rotation.x += 0.012;
    if (ring2) ring2.rotation.y += 0.014;
    if (ring3) ring3.rotation.z += 0.016;

    if (gyroCore) {
      gyroCore.rotation.x += 0.007;
      gyroCore.rotation.y += 0.009;
    }

    // Stream D: data-driven pulse — each node glows with its source's real
    // claim state (set by window.ScopeShiftTwin.update), and the clash
    // barrier breathes while any dispute is live.
    const t = performance.now() / 1000;
    [nodeBRD, nodeScreenshot, nodeNote].forEach(n => {
      if (!n || !n.material || !n.material.emissive) return;
      const st = n.userData && n.userData.claimState;
      n.material.emissiveIntensity = (st === 'DISPUTED' || st === 'GOVERNED')
        ? 0.45 + 0.35 * Math.sin(t * 4)
        : 0.12;
    });
    if (twinAnim.clash && clashBarrier) {
      clashBarrier.material.opacity = 0.22 + 0.14 * Math.sin(t * 3.2);
    }

    renderer.render(scene, camera);
  }

  // Stream D: data-driven 3D twin. Per-node pulse colors come from the real
  // claim state of each node's source (red DISPUTED / emerald GOVERNED /
  // cobalt CONSISTENT); the clash barrier lives while ANY claim is disputed
  // and the emerald authority beam while ANY claim is governed. Called from
  // the normal render path — never throws, so the page keeps working if the
  // twin failed to initialize.
  window.ScopeShiftTwin = {
    update(snapshot) {
      try {
        if (!snapshot || !gyroCore) return;
        const res = snapshot.resolutions || {};
        const claimBySource = {};
        (snapshot.sources || []).forEach(s => { claimBySource[s.id] = s.claim_id; });
        const COLOR = { DISPUTED: 0xe11d48, GOVERNED: 0x059669, CONSISTENT: 0x2563eb };
        [nodeBRD, nodeScreenshot, nodeNote].forEach(n => {
          if (!n || !n.userData || !n.userData.id || !n.material || !n.material.emissive) return;
          const cid = claimBySource[n.userData.id];
          const st = (cid && res[cid]) ? res[cid].state : null;
          n.userData.claimState = st || 'NONE';
          n.material.emissive.setHex(COLOR[st] || 0x64748b);
        });
      } catch (err) {
        console.warn('ScopeShiftTwin.update failed (non-fatal):', err);
      }
    },
  };

  function update3DTopology(stateName, snapshot) {
    if (!gyroCore) return;

    const coreBadge = document.querySelector('#core-3d-badge');
    const coreText = document.querySelector('#core-3d-text');
    const pulseDot = coreBadge ? coreBadge.querySelector('.pill-dot') : null;

    if (stateName === 'GOVERNED') {
      gyroCore.material.color.setHex(0x059669);
      gyroCore.material.emissive.setHex(0x059669);
      nodeNote.visible = true;
      nodeNote.material.opacity = 1.0;

      if (coreText) coreText.textContent = 'TOPOLOGY: GOVERNED • CLIENT DIRECTIVE AUTHORIZED';
      if (pulseDot) pulseDot.style.background = 'var(--emerald)';
    } else if (stateName === 'DISPUTED') {
      gyroCore.material.color.setHex(0xe11d48);
      gyroCore.material.emissive.setHex(0xe11d48);

      if (currentBeat === 3) {
        nodeNote.material.color.setHex(0x94a3b8);
        nodeNote.material.opacity = 0.4;
        if (coreText) coreText.textContent = 'TOPOLOGY: DISPUTED • CLIENT AUTHORITY WITHDRAWN';
      } else {
        nodeNote.material.color.setHex(0x059669);
        nodeNote.material.opacity = 1.0;
        if (coreText) coreText.textContent = 'TOPOLOGY: DISPUTED • RED CLASH BARRIER ACTIVE';
      }

      if (pulseDot) pulseDot.style.background = 'var(--crimson)';
    } else {
      gyroCore.material.color.setHex(0x2563eb);
      gyroCore.material.emissive.setHex(0x2563eb);

      if (coreText) coreText.textContent = 'TOPOLOGY: CONSISTENT • BRD BASELINE STANDS';
      if (pulseDot) pulseDot.style.background = 'var(--royal)';
    }

    // Data-driven conflict vectors from the live snapshot: the red clash
    // barrier shows while ANY claim is DISPUTED, the emerald authority beam
    // while ANY claim is GOVERNED (not just the hero claim).
    const states = snapshot && snapshot.resolutions
      ? Object.values(snapshot.resolutions).map(r => r.state)
      : [stateName];
    twinAnim.clash = states.includes('DISPUTED');
    twinAnim.beam = states.includes('GOVERNED');
    clashBeam.material.opacity = twinAnim.clash ? 0.95 : 0.0;
    clashBarrier.material.opacity = twinAnim.clash ? 0.3 : 0.0;
    authBeam.material.opacity = twinAnim.beam ? 0.95 : 0.0;
  }

  // Camera preset buttons
  document.querySelector('#cam-iso')?.addEventListener('click', () => {
    targetRotationX = 0.22;
    targetRotationY = -0.28;
    camera.position.set(0, 6.5, 15);
    camera.lookAt(0, 0, 0);
    setActiveCamBtn('#cam-iso');
  });

  document.querySelector('#cam-top')?.addEventListener('click', () => {
    targetRotationX = 1.35;
    targetRotationY = 0;
    camera.position.set(0, 18, 0.1);
    camera.lookAt(0, 0, 0);
    setActiveCamBtn('#cam-top');
  });

  document.querySelector('#cam-core')?.addEventListener('click', () => {
    targetRotationX = 0.05;
    targetRotationY = 0;
    camera.position.set(0, 1.2, 7.5);
    camera.lookAt(0, 0, 0);
    setActiveCamBtn('#cam-core');
  });

  function setActiveCamBtn(selector) {
    document.querySelectorAll('.btn-cam').forEach(b => b.classList.remove('active'));
    document.querySelector(selector)?.classList.add('active');
  }

  // ==========================================================================
  // 2. Full Page Navigation & Routing Controller (SPA Hash Routing)
  // ==========================================================================
  const pageMap = {
    'cockpit': 'page-cockpit',
    'matrix': 'page-matrix',
    'studio': 'page-studio',
    'brd': 'page-brd',
    'audit': 'page-audit',
  };

  function navigateTo(hashKey) {
    const pageId = pageMap[hashKey] || 'page-cockpit';
    activePageId = pageId;

    // Update active nav links
    document.querySelectorAll('.nav-link').forEach(link => {
      const isTarget = link.getAttribute('data-page') === pageId;
      link.classList.toggle('active', isTarget);
    });

    // Update visible page view
    document.querySelectorAll('.page-view').forEach(view => {
      view.classList.toggle('active', view.id === pageId);
    });

    // Close mobile drawer if open
    if (mobileDrawer) mobileDrawer.classList.remove('open');

    // Trigger canvas resize if returning to overview
    if (pageId === 'page-cockpit' && renderer) {
      const container = document.querySelector('#canvas-container');
      if (container) {
        renderer.setSize(container.clientWidth, container.clientHeight);
      }
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  window.addEventListener('hashchange', () => {
    const key = window.location.hash.replace(/^#\/?/, '');
    navigateTo(key);
  });

  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const pageId = link.getAttribute('data-page');
      const hashKey = Object.keys(pageMap).find(k => pageMap[k] === pageId) || 'cockpit';
      window.location.hash = hashKey;
    });
  });

  // Mobile Menu Toggle
  mobileToggle?.addEventListener('click', () => {
    if (mobileDrawer) mobileDrawer.classList.toggle('open');
  });

  // ==========================================================================
  // 3. API Communication & State Rendering
  // ==========================================================================
  async function fetchState() {
    try {
      const res = await fetch('/api/state');
      if (!res.ok) throw new Error('Failed to load state');
      appState = await res.json();
      renderAllModules(appState);
    } catch (err) {
      console.error('State load error:', err);
    }
  }

  async function triggerBeat(beatNum) {
    currentBeat = beatNum;
    setActiveBeatBtn(beatNum);

    // Honest extraction: no live-AI path in the stage UI. The server reports the real
    // mode (live only if a GEMINI_API_KEY is configured, otherwise deterministic fallback).
    try {
      const res = await fetch('/api/demo/beat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ beat: beatNum, use_live_ai: false }),
      });
      const data = await res.json();
      appState = data.state;

      if (data.extraction && data.extraction.mode !== 'none') {
        showLatency(data.extraction);
      } else {
        if (latencyBadge) latencyBadge.style.display = 'none';
      }

      if (data.already_applied && data.hint) {
        showToast(`[NO-OP] ${data.hint}`);
      }

      renderAllModules(appState);
    } catch (err) {
      console.error('Beat trigger error:', err);
    }
  }

  function showLatency(meta) {
    if (!latencyBadge) return;
    latencyBadge.style.display = 'inline-flex';
    if (meta.mode === 'deterministic-fallback') {
      latencyBadge.textContent = `deterministic fallback — pre-extracted evidence (${meta.latency_ms}ms; replay never calls Gemini)`;
    } else {
      latencyBadge.textContent = `LIVE: ${meta.latency_ms}ms (${meta.model || 'Gemini'})`;
    }
    // Keep the status pill showing the real mode reported by the server.
    if (extractionModeText) {
      if (meta.mode === 'deterministic-fallback') {
        extractionModeText.textContent = 'EXTRACTION: DETERMINISTIC PIPELINE (VERIFIED)';
        extractionModePill?.classList.remove('live');
      } else if (meta.mode === 'live') {
        extractionModeText.textContent = `EXTRACTION: GEMINI MULTI-MODAL (${meta.model || 'gemini'})`;
        extractionModePill?.classList.add('live');
      }
    }
  }

  function setActiveBeatBtn(beat) {
    document.querySelectorAll('.stage-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`#btn-beat-${beat}`)?.classList.add('active');
    setTeleprompterBeat(beat); // Stream E: teleprompter follows beat state
  }

  // --------------------------------------------------------------------------
  // Stage narrative captions controller
  // --------------------------------------------------------------------------
  const teleprompter = document.querySelector('#teleprompter');
  const TELEPROMPTER_KEY = 'scopeshift.teleprompter.dismissed';

  function setTeleprompterBeat(beat) {
    if (!teleprompter) return;
    teleprompter.querySelectorAll('.teleprompter-line').forEach(line => {
      line.classList.toggle('active', Number(line.getAttribute('data-beat')) === beat);
    });
  }

  function initTeleprompter() {
    if (!teleprompter) return;
    let dismissed = false;
    try {
      dismissed = window.localStorage.getItem(TELEPROMPTER_KEY) === '1';
    } catch (err) { /* storage unavailable — keep the bar visible */ }
    teleprompter.style.display = dismissed ? 'none' : 'flex';
    setTeleprompterBeat(currentBeat);
  }

  document.querySelector('#teleprompter-close')?.addEventListener('click', () => {
    if (!teleprompter) return;
    teleprompter.style.display = 'none';
    try {
      window.localStorage.setItem(TELEPROMPTER_KEY, '1');
    } catch (err) { /* non-fatal */ }
  });

  function renderAllModules(state) {
    if (!state) return;

    renderCockpit(state);
    renderClaimsMatrix(state);
    renderStudioLedger(state);
    renderGovernedBrd(state);
    renderAuditLedger(state);
    renderHeatmap(state);

    if (scrubber && state.events) {
      scrubber.max = Math.max(state.events.length, 4);
      const lastSeq = state.events.length > 0 ? state.events[state.events.length - 1].event_sequence : 0;
      scrubber.value = lastSeq;
      if (scrubberSeqBadge) scrubberSeqBadge.textContent = `SEQUENCE #${lastSeq}`;
    }
  }

  // --------------------------------------------------------------------------
  // Module 1: Cockpit Panels
  // --------------------------------------------------------------------------
  function renderCockpit(state) {
    const primaryClaim = state.resolutions?.['checkout.payment_methods'] || {};
    const stateStr = primaryClaim.state || 'UNKNOWN';

    if (stateEl) {
      stateEl.textContent = stateStr;
      stateEl.className = 'state-badge-giant ' + (
        stateStr === 'GOVERNED' ? 'state-badge-governed' :
        stateStr === 'DISPUTED' ? 'state-badge-disputed' : 'state-badge-consistent'
      );
    }

    if (reasonEl) {
      reasonEl.textContent = primaryClaim.reason || 'No conflict active.';
    }

    // Stream E: cinematic beat transitions — animate only when the hero claim
    // state actually changed since the last render.
    if (prevHeroState !== null && prevHeroState !== stateStr) {
      transitionStateBadge(prevHeroState, stateStr);
    }
    prevHeroState = stateStr;

    update3DTopology(stateStr, state);
    if (window.ScopeShiftTwin && typeof window.ScopeShiftTwin.update === 'function') {
      window.ScopeShiftTwin.update(state);
    }

    // Quadrant 1: Sources
    if (sourcesEl && state.sources) {
      sourcesEl.innerHTML = '';
      state.sources.forEach(s => {
        const borderClass = s.type === 'brd' ? 'data-card-royal' : s.type === 'screenshot' ? 'data-card-amber' : 'data-card-emerald';
        const card = document.createElement('div');
        card.className = `data-card ${borderClass}`;
        const activeText = s.active ? '<span style="color: var(--emerald-text); font-weight: 700;">ACTIVE</span>' : '<span style="color: var(--crimson-text); font-weight: 700;">WITHDRAWN</span>';
        card.innerHTML = `
          <div class="card-topbar">
            <span class="card-sid">${escapeHtml(s.id)}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
              <span class="card-type-tag">${escapeHtml(s.type)}</span>
              ${activeText}
            </div>
          </div>
          <p class="card-quote-box">&ldquo;${escapeHtml(s.quote)}&rdquo;</p>
          <div class="card-bottombar">
            <span style="font-size: 11px;">${escapeHtml(s.observation || s.claim_id)}</span>
            <button class="btn-cam btn-inspect" data-sid="${escapeHtml(s.id)}">Inspect</button>
          </div>
        `;
        sourcesEl.appendChild(card);
      });

      sourcesEl.querySelectorAll('.btn-inspect').forEach(b => {
        b.addEventListener('click', () => openArtifactModal(b.getAttribute('data-sid')));
      });
    }

    // Quadrant 2: Evidence Ledger
    if (evidenceEl && state.sources) {
      evidenceEl.innerHTML = '';
      state.sources.forEach(e => {
        const verTag = e.quote_verified
          ? '<span class="indicator-valid">&check; VERIFIED QUOTE</span>'
          : '<span class="indicator-invalid">&times; UNVERIFIED</span>';
        const card = document.createElement('div');
        card.className = 'data-card';
        card.innerHTML = `
          <div class="card-topbar">
            <strong>${escapeHtml(e.id)} &bull; ${escapeHtml(e.claim_id)}</strong>
            <span class="card-type-tag">${e.proposed_scope_change ? 'Scope Directive' : 'Observation'}</span>
          </div>
          <p class="card-quote-box">${escapeHtml(e.quote)}</p>
          <div class="card-bottombar">
            ${verTag}
            <span>${e.active ? 'Active in Log' : 'Withdrawn'}</span>
          </div>
        `;
        evidenceEl.appendChild(card);
      });
    }

    // Quadrant 3: Current BRD
    if (brdEl && state.resolutions) {
      brdEl.innerHTML = '';
      let published = 0;

      for (const [cid, r] of Object.entries(state.resolutions)) {
        if (r.in_brd) {
          published++;
          const card = document.createElement('div');
          card.className = 'data-card data-card-emerald';
          card.innerHTML = `
            <div class="card-topbar">
              <strong style="color: var(--text-headline); font-size: 13px;">${escapeHtml(r.title || cid)}</strong>
              <span class="card-type-tag" style="background: var(--emerald-soft); color: var(--emerald-text);">${escapeHtml(r.state)}</span>
            </div>
            <p style="margin: 0 0 8px; font-weight: 700; color: var(--text-headline); font-size: 13px;">${escapeHtml(r.requirement)}</p>
            <p style="margin: 0 0 10px; font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${escapeHtml(r.rule || '')}</p>
            <div class="card-bottombar">
              <span>Authority: <strong>${escapeHtml(r.governing_source || 'Baseline')}</strong></span>
              <span>Citations: [${r.citations ? r.citations.map(c => escapeHtml(c.source_id)).join(', ') : ''}]</span>
            </div>
          `;
          brdEl.appendChild(card);
        }
      }

      if (published === 0) {
        brdEl.innerHTML = `
          <div style="padding: 24px; text-align: center; border: 1px dashed var(--crimson-border); border-radius: var(--radius-md); color: var(--crimson-text); font-family: var(--font-mono); font-size: 12px;">
            <strong>[ ALL CONFLICTING CLAIMS WITHHELD ]</strong>
            <p style="margin: 8px 0 0; color: var(--text-muted); font-size: 11px;">
              Contradictions between visual observations and baseline documents strictly withhold publication until explicit client scope authorization.
            </p>
          </div>
        `;
      }
    }

    // Quadrant 4: Event Log
    if (eventsEl && state.events) {
      eventsEl.innerHTML = '';
      state.events.forEach(ev => {
        const row = document.createElement('div');
        row.className = 'seq-row';
        const actionSpan = ev.event === 'ADDED'
          ? '<span class="seq-action-added">[ADDED]</span>'
          : '<span class="seq-action-removed">[REMOVED]</span>';
        row.innerHTML = `
          <span class="seq-num">#${ev.event_sequence}</span>
          <span style="font-weight: 600;">${escapeHtml(ev.source_id)}</span>
          ${actionSpan}
        `;
        eventsEl.appendChild(row);
      });
    }

    if (mirrorEl && state.mirror_note) {
      mirrorEl.textContent = state.mirror_note;
    }
  }

  // --------------------------------------------------------------------------
  // Module 2: Multi-Claim Governance Matrix
  // --------------------------------------------------------------------------
  // Stream E: per-claim event-sequence sparkline. Dots are colored by the
  // claim's real resolver state at each timeline step (red DISPUTED, emerald
  // GOVERNED, cobalt CONSISTENT, gray no-data), computed from the snapshot's
  // own event history — no new fetch, no scripted data.
  const SPARK_CLASS = {
    DISPUTED: 'spark-disputed',
    GOVERNED: 'spark-governed',
    CONSISTENT: 'spark-consistent',
  };

  function buildSparkline(timeline, claimId) {
    if (!Array.isArray(timeline) || timeline.length === 0) {
      return '<span class="spark-empty">no event history</span>';
    }
    const dots = timeline.map(step => {
      const info = step.claims && step.claims[claimId];
      const st = info ? info.state : 'NONE';
      const cls = SPARK_CLASS[st] || 'spark-none';
      return `<span class="spark-dot ${cls}" title="Seq #${step.sequence}: ${escapeHtml(st)}"></span>`;
    }).join('');
    return `<div class="sparkline" role="img" aria-label="State history for ${escapeHtml(claimId)}">${dots}</div>`;
  }

  function renderClaimsMatrix(state) {
    if (!claimsGrid || !state.resolutions) return;
    claimsGrid.innerHTML = '';

    for (const [cid, res] of Object.entries(state.resolutions)) {
      const stateBadge = res.state === 'GOVERNED'
        ? '<span class="brand-badge" style="background: var(--emerald-soft); color: var(--emerald-text); border-color: var(--emerald-border);">GOVERNED</span>'
        : res.state === 'DISPUTED'
        ? '<span class="brand-badge" style="background: var(--crimson-soft); color: var(--crimson-text); border-color: var(--crimson-border);">DISPUTED</span>'
        : res.state === 'CONSISTENT'
        ? '<span class="brand-badge" style="background: var(--royal-soft); color: var(--royal-text); border-color: var(--royal-border);">CONSISTENT</span>'
        : '<span class="brand-badge">UNKNOWN</span>';

      const card = document.createElement('div');
      card.className = 'claim-panel-card';

      let citationsHtml = '';
      if (res.citations && res.citations.length > 0) {
        citationsHtml = res.citations.map(c => `
          <li class="citation-pill-item">
            <span class="card-type-tag">${escapeHtml(c.source_id)}</span>
            <span style="color: var(--text-muted);">(${escapeHtml(c.role)}):</span>
            <span style="font-weight: 500;">&ldquo;${escapeHtml(c.quote)}&rdquo;</span>
          </li>
        `).join('');
      } else {
        citationsHtml = '<li style="font-size: 11px; color: var(--text-muted);">No active citations attached</li>';
      }

      card.innerHTML = `
        <div class="claim-panel-header">
          <div class="claim-title-cluster">
            <h4 class="claim-h3">${escapeHtml(res.title || cid)}</h4>
            <span class="claim-code-id">${escapeHtml(cid)}</span>
          </div>
          ${stateBadge}
        </div>
        <div class="claim-panel-body">
          <div class="claim-field-label">Governed Requirement</div>
          <div class="claim-req-display">
            ${res.requirement ? escapeHtml(res.requirement) : '<span style="color: var(--crimson-text); font-family: var(--font-mono); font-size: 12px;">[ WITHHELD FROM BRD: CONFLICT DETECTED ]</span>'}
          </div>

          <div class="claim-field-label">Business Constraint / Rule</div>
          <div class="claim-rule-display">
            ${escapeHtml(res.rule || res.reason || 'Evaluating evidence constraint...')}
          </div>

          <div class="claim-field-label">State History (per event sequence)</div>
          <div class="claim-spark-row">
            ${buildSparkline(state.timeline, cid)}
          </div>

          <div class="claim-field-label">Active Citation Verification</div>
          <ul class="citation-pill-list">
            ${citationsHtml}
          </ul>

          <div class="claim-action-footer">
            <button class="btn-pill btn-emerald btn-gov-claim" data-claim="${escapeHtml(cid)}">
              + Authorize Scope
            </button>
            ${res.governing_source ? `
              <button class="btn-pill btn-crimson btn-withdraw-claim" data-sid="${escapeHtml(res.governing_source)}">
                &minus; Revoke Scope (${escapeHtml(res.governing_source)})
              </button>
            ` : ''}
          </div>
        </div>
      `;
      claimsGrid.appendChild(card);
    }

    claimsGrid.querySelectorAll('.btn-gov-claim').forEach(btn => {
      btn.addEventListener('click', () => openGovernModal(btn.getAttribute('data-claim')));
    });

    claimsGrid.querySelectorAll('.btn-withdraw-claim').forEach(btn => {
      btn.addEventListener('click', () => withdrawScope(btn.getAttribute('data-sid')));
    });
  }

  // --------------------------------------------------------------------------
  // Module 3: Ingestion Studio Ledger & Live Quote Proofing
  // --------------------------------------------------------------------------
  function renderStudioLedger(state) {
    if (!studioLedgerRows || !state.sources) return;
    studioLedgerRows.innerHTML = '';

    state.sources.forEach(s => {
      const tr = document.createElement('tr');
      const verBadge = s.quote_verified
        ? '<span style="color: var(--emerald-text); font-weight: 700;">&check; VERIFIED</span>'
        : '<span style="color: var(--crimson-text); font-weight: 700;">&times; UNVERIFIED</span>';
      const statusText = s.active
        ? '<span style="color: var(--emerald-text); font-weight: 600;">Active</span>'
        : '<span style="color: var(--crimson-text); font-weight: 600;">Withdrawn</span>';

      tr.innerHTML = `
        <td><strong>${escapeHtml(s.id)}</strong></td>
        <td><span class="card-type-tag">${escapeHtml(s.type)}</span></td>
        <td><code>${escapeHtml(s.claim_id)}</code></td>
        <td style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">&ldquo;${escapeHtml(s.quote)}&rdquo;</td>
        <td>${verBadge}</td>
        <td>${quoteMeterHtml(s.quote_verified)}</td>
        <td>${statusText}</td>
      `;
      studioLedgerRows.appendChild(tr);
    });
  }

  // Stream E: quote-match strength meter — display-only, derived from the
  // deterministic code-verified quote check. Honest scale: verified = 100%,
  // unverified = 0%. Not a model score.
  function quoteMeterHtml(verified) {
    const pct = verified ? 100 : 0;
    return `
      <span class="quote-meter" title="code-verified quote substring check: ${pct}%">
        <span class="quote-meter-bar"><span class="quote-meter-fill ${verified ? '' : 'zero'}" style="width: ${pct}%"></span></span>
        <span class="quote-meter-label">${pct}% &bull; code-verified</span>
      </span>`;
  }

  function checkQuoteMatch() {
    if (!inpText || !inpQuote || !quoteFeedback) return;
    const textVal = inpText.value.trim().toLowerCase();
    const quoteVal = inpQuote.value.trim().toLowerCase();

    if (!quoteVal) {
      quoteFeedback.className = 'quote-match-indicator indicator-invalid';
      quoteFeedback.innerHTML = '&times; Please enter quote to verify against content.';
      return;
    }

    if (inpSourceType.value === 'screenshot') {
      quoteFeedback.className = 'quote-match-indicator indicator-valid';
      quoteFeedback.innerHTML = '&check; Screenshot element quote registered.';
      return;
    }

    if (textVal.includes(quoteVal)) {
      quoteFeedback.className = 'quote-match-indicator indicator-valid';
      quoteFeedback.innerHTML = '&check; Exact substring verified in text.';
    } else {
      quoteFeedback.className = 'quote-match-indicator indicator-invalid';
      quoteFeedback.innerHTML = '&times; Quote NOT found in content! Verification will reject.';
    }
  }

  inpText?.addEventListener('input', checkQuoteMatch);
  inpQuote?.addEventListener('input', checkQuoteMatch);
  inpSourceType?.addEventListener('change', () => {
    const isScreenshot = inpSourceType.value === 'screenshot';
    const isClientNote = inpSourceType.value === 'client_note';
    const scopeToggleGroup = document.querySelector('#scope-toggle-group');

    if (scopeToggleGroup) {
      scopeToggleGroup.style.display = isScreenshot ? 'none' : 'block';
    }
    if (inpScopeChange) {
      inpScopeChange.checked = isClientNote;
      inpScopeChange.disabled = isScreenshot;
    }
    checkQuoteMatch();
  });

  inpClaimId?.addEventListener('change', () => {
    if (!inpValueJson) return;
    const cid = inpClaimId.value;
    if (cid === 'checkout.payment_methods') {
      inpValueJson.value = JSON.stringify({ methods: ['Card'], exclusive: false }, null, 2);
    } else if (cid === 'checkout.currency') {
      inpValueJson.value = JSON.stringify({ currency: 'USD' }, null, 2);
    } else if (cid === 'auth.mfa_requirement') {
      inpValueJson.value = JSON.stringify({ mfa_required: true, channels: ['TOTP Authenticator', 'SMS OTP'] }, null, 2);
    } else if (cid === 'refunds.settlement_sla') {
      inpValueJson.value = JSON.stringify({ sla_hours: 24, instant_settlement: true }, null, 2);
    }
  });

  ingestForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    let parsedVal = {};
    try {
      parsedVal = JSON.parse(inpValueJson.value);
    } catch {
      alert('Value JSON is invalid syntax.');
      return;
    }

    const payload = {
      source_type: inpSourceType.value,
      claim_id: inpClaimId.value,
      text: inpText.value,
      quote: inpQuote.value,
      observation: `Ingested note: ${inpQuote.value.slice(0, 50)}`,
      proposed_scope_change: Boolean(inpScopeChange.checked),
      value: parsedVal,
      region: inpSourceType.value === 'screenshot' ? [100, 100, 200, 50] : null,
    };

    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        alert('Validation Error: ' + (data.error?.message || 'Ingestion rejected.'));
        return;
      }

      appState = data.state;
      renderAllModules(appState);
      alert(`Success! Ingested as ${data.source_id} and appended to audit log.`);
      inpText.value = '';
      inpQuote.value = '';
    } catch (err) {
      alert('Failed submitting ingestion: ' + err.message);
    }
  });

  // Multi-Modal Gemini Extraction form handler (/api/extract)
  const extractForm = document.querySelector('#extract-form');
  const inpExtractType = document.querySelector('#inp-extract-type');
  const inpExtractFile = document.querySelector('#inp-extract-file');
  const inpExtractText = document.querySelector('#inp-extract-text');
  const inpExtractSender = document.querySelector('#inp-extract-sender');
  const inpExtractChannel = document.querySelector('#inp-extract-channel');
  const extractReceiptsContainer = document.querySelector('#extract-receipts-container');
  const extractReceiptsList = document.querySelector('#extract-receipts-list');
  const extractMetaTag = document.querySelector('#extract-meta-tag');
  const btnRunExtract = document.querySelector('#btn-run-extract');

  extractForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = inpExtractFile?.files?.[0];
    const text = (inpExtractText?.value || '').trim();
    const sourceType = inpExtractType?.value || 'client_note';
    const sender = (inpExtractSender?.value || '').trim();
    const channel = (inpExtractChannel?.value || '').trim();

    if (!file && !text) {
      alert('Please upload a file (.pdf, .png, .jpg) or enter text to extract.');
      return;
    }

    if (btnRunExtract) {
      btnRunExtract.disabled = true;
      btnRunExtract.textContent = 'Extracting and verifying claims…';
    }

    try {
      let res;
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('source_type', sourceType);
        if (text) formData.append('text', text);
        if (sender) formData.append('sender', sender);
        if (channel) formData.append('channel', channel);
        res = await fetch('/api/extract', {
          method: 'POST',
          body: formData,
        });
      } else {
        res = await fetch('/api/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_type: sourceType,
            text: text,
            sender: sender || null,
            channel: channel || null,
          }),
        });
      }

      const data = await res.json();
      if (!res.ok) {
        alert('Extraction failed: ' + (data.error?.message || 'Server error'));
        return;
      }

      if (data.state) {
        appState = data.state;
        renderAllModules(appState);
      }

      if (extractReceiptsContainer && extractReceiptsList) {
        extractReceiptsContainer.style.display = 'block';
        const ext = data.extraction || {};
        if (extractMetaTag) {
          extractMetaTag.textContent = `${ext.route || ext.mode} • ${ext.model || 'model'} • ${ext.latency_ms || 0}ms`;
        }
        const receipts = data.receipts || [];
        const claims = data.claims || [];
        if (receipts.length === 0 && claims.length === 0) {
          extractReceiptsList.innerHTML = `<p style="font-size: 13px; color: var(--crimson-text); margin: 6px 0;">No claims extracted. Reason: ${escapeHtml(ext.reason || 'Offline or no claims found in input')}</p>`;
        } else {
          extractReceiptsList.innerHTML = receipts.map(r => {
            const isOk = r.status === 'verified';
            const badgeCls = isOk ? 'indicator-valid' : 'indicator-invalid';
            const badgeTxt = isOk ? '✓ VERIFIED' : '✗ REJECTED / UNVERIFIED';
            return `
              <div style="background: var(--surface-card); border: 1px solid var(--border-light); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <strong style="font-size: 13px;">${escapeHtml(r.claim_id)}</strong>
                  <span class="${badgeCls}">${badgeTxt}</span>
                </div>
                ${r.source_id ? `<p style="margin: 2px 0; font-size: 12px;"><strong>Source ID:</strong> <code>${escapeHtml(r.source_id)}</code></p>` : ''}
                ${r.observation ? `<p style="margin: 2px 0; font-size: 12px; color: var(--text-muted);">${escapeHtml(r.observation)}</p>` : ''}
                ${r.error ? `<p style="margin: 2px 0; font-size: 12px; color: var(--crimson-text);"><strong>Rejection Rationale:</strong> ${escapeHtml(r.error)}</p>` : ''}
                <p style="margin: 2px 0; font-size: 11px; color: var(--text-muted);">Governing Authority: <strong>${r.governing ? 'YES (Admitted to BRD)' : 'NO (Observation Only)'}</strong></p>
              </div>
            `;
          }).join('');
        }
      }
      refreshCloudStatus();
      showToast(`Extraction complete: ${data.receipts?.length || 0} claims processed through validation pipeline.`);
    } catch (err) {
      alert('Error during extraction: ' + err.message);
    } finally {
      if (btnRunExtract) {
        btnRunExtract.disabled = false;
        btnRunExtract.textContent = 'Σ Extract & Validate with Gemini (/api/extract)';
      }
    }
  });

  // --------------------------------------------------------------------------
  // Scenario presets: each step is a real POST /api/ingest through the same
  // validation boundary as the manual form. Rejections are reported, not hidden.
  // --------------------------------------------------------------------------
  const PRESETS = {
    mfa: [
      { label: 'Baseline BRD: MFA optional', source_type: 'brd', claim_id: 'auth.mfa_requirement',
        text: 'REQ-SEC-01: Login uses a password only. MFA is optional for all users.',
        quote: 'MFA is optional for all users', proposed_scope_change: false,
        value: { mfa_required: false } },
      { label: 'Client note: MFA mandated', source_type: 'client_note', claim_id: 'auth.mfa_requirement',
        text: 'Following the security review, MFA is required for all logins via TOTP and SMS.',
        quote: 'MFA is required for all logins via TOTP and SMS', proposed_scope_change: true,
        value: { mfa_required: true, channels: ['TOTP Authenticator', 'SMS OTP'] } },
    ],
    currency: [
      { label: 'Baseline BRD: INR pricing', source_type: 'brd', claim_id: 'checkout.currency',
        text: 'REQ-PAY-02: All prices are shown and charged in INR.',
        quote: 'All prices are shown and charged in INR', proposed_scope_change: false,
        value: { currency: 'INR' } },
      { label: 'Client note: switch to USD', source_type: 'client_note', claim_id: 'checkout.currency',
        text: 'For the international launch, checkout currency changes to USD.',
        quote: 'checkout currency changes to USD', proposed_scope_change: true,
        value: { currency: 'USD' } },
    ],
    hostile: [
      { label: 'Screenshot claiming scope authority', source_type: 'screenshot', claim_id: 'checkout.payment_methods',
        text: 'Pay with Card', quote: 'Pay with Card', proposed_scope_change: true,
        value: { methods: ['Card'] }, region: [460, 285, 370, 80] },
      { label: 'Note with fabricated quote', source_type: 'client_note', claim_id: 'checkout.payment_methods',
        text: 'Maybe we could think about Card at some point.', quote: 'Card is approved for v1',
        proposed_scope_change: true, value: { methods: ['Card'] } },
      { label: 'Invented claim id', source_type: 'client_note', claim_id: 'checkout.bitcoin',
        text: 'Please add Bitcoin payments.', quote: 'Please add Bitcoin payments', proposed_scope_change: true,
        value: { methods: ['Bitcoin'] } },
    ],
  };

  const presetLog = document.querySelector('#preset-log');

  async function runPreset(key) {
    const steps = PRESETS[key];
    if (!steps || !presetLog) return;
    document.querySelectorAll('.preset-btn').forEach(b => { b.disabled = true; });
    presetLog.style.display = 'block';
    presetLog.innerHTML = '';
    try {
      for (const step of steps) {
        const payload = {
          source_type: step.source_type,
          claim_id: step.claim_id,
          text: step.text,
          quote: step.quote,
          observation: step.label,
          proposed_scope_change: step.proposed_scope_change,
          value: step.value,
          region: step.region || null,
        };
        let line;
        try {
          const res = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json();
          if (res.ok) {
            appState = data.state;
            renderAllModules(appState);
            const ev = data.evidence || {};
            const authority = ev.governing ? 'can govern' : 'observation only';
            line = { ok: true, text: `${step.label} \u2192 accepted as ${data.source_id} (${authority}, quote ${ev.quote_verified ? 'verified' : 'unverified'})` };
          } else {
            line = { ok: false, text: `${step.label} \u2192 rejected at the boundary: ${data.error?.message || 'validation error'}` };
          }
        } catch (err) {
          line = { ok: false, text: `${step.label} \u2192 request failed: ${err.message}` };
        }
        const row = document.createElement('div');
        row.className = 'preset-log-row ' + (line.ok ? 'ok' : 'blocked');
        row.textContent = (line.ok ? '\u2713 ' : '\u2298 ') + line.text;
        presetLog.appendChild(row);
        await sleep(450);
      }
    } finally {
      document.querySelectorAll('.preset-btn').forEach(b => { b.disabled = false; });
    }
  }

  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => runPreset(btn.getAttribute('data-preset')));
  });

  // --------------------------------------------------------------------------
  // Module 4: Governed BRD & Diff Viewer
  // --------------------------------------------------------------------------
  function renderGovernedBrd(state) {
    if (!brdDocView || !state.resolutions) return;

    let html = `
      <h1>Business Requirements Document (BRD) &bull; Governed Specification</h1>
      <p style="color: var(--text-muted); font-size: 13px;">
        Generated by <strong>ScopeShift Deterministic Engine</strong> (Enterprise Edition)<br>
        Core Governance Invariant: <em>Seeing a button is not approving the button.</em>
      </p>

      <h2>1. Current Governed Requirements</h2>
    `;

    let activeCount = 0;
    const diffBaseline = [];
    const diffGoverned = [];

    for (const [cid, res] of Object.entries(state.resolutions)) {
      if (res.in_brd) {
        activeCount++;
        html += `
          <div class="brd-spec-box">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
              <strong style="font-size: 16px; color: var(--text-headline);">${escapeHtml(res.title || cid)}</strong>
              <span class="brand-badge" style="background: var(--emerald-soft); color: var(--emerald-text); border-color: var(--emerald-border);">${escapeHtml(res.state)} &bull; ${escapeHtml(res.basis)}</span>
            </div>
            <p style="margin: 0 0 6px; font-size: 14px; font-weight: 700; color: var(--text-headline);">
              ${escapeHtml(res.requirement)}
            </p>
            <p style="margin: 0 0 10px; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
              <strong>Business Rule:</strong> ${escapeHtml(res.rule || '')}
            </p>
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); border-top: 1px solid var(--border-light); padding-top: 8px;">
              Governing Authority: <strong>${escapeHtml(res.governing_source || 'BRD Baseline')}</strong> &bull;
              Citations: ${res.citations ? res.citations.map(c => `[${escapeHtml(c.source_id)}: &ldquo;${escapeHtml(c.quote)}&rdquo;]`).join(', ') : 'None'}
            </div>
          </div>
        `;
        diffGoverned.push(`<div class="diff-line-added"><strong>${escapeHtml(res.title)}:</strong> ${escapeHtml(res.requirement)}</div>`);
      } else {
        diffBaseline.push(`<div class="diff-line-withheld"><strong>${escapeHtml(res.title)}:</strong> Withheld due to contradiction</div>`);
      }
    }

    if (activeCount === 0) {
      html += `
        <p style="color: var(--crimson-text); font-family: var(--font-mono); font-size: 13px;">
          *No requirements currently published. All conflicting claims are withheld until explicit client scope authorization.*
        </p>
      `;
    }

    html += `
      <h2>2. Disputed &amp; Withheld Claims</h2>
    `;

    for (const [cid, res] of Object.entries(state.resolutions)) {
      if (!res.in_brd) {
        html += `
          <div style="background: #ffffff; border: 1px solid var(--crimson-border); border-left: 4px solid var(--crimson); border-radius: var(--radius-md); padding: 16px; margin-bottom: 12px;">
            <strong style="color: var(--crimson-text); font-size: 14px;">${escapeHtml(res.title || cid)} (${escapeHtml(res.state)})</strong>
            <p style="margin: 6px 0 0; font-size: 13px; color: var(--text-body); line-height: 1.5;">
              ${escapeHtml(res.reason)}
            </p>
          </div>
        `;
      }
    }

    brdDocView.innerHTML = html;

    if (diffBaselineContent) diffBaselineContent.innerHTML = diffBaseline.join('') || '<p style="color: var(--text-muted);">No baseline deviations.</p>';
    if (diffGovernedContent) diffGovernedContent.innerHTML = diffGoverned.join('') || '<p style="color: var(--text-muted);">No governed requirements active.</p>';
  }

  btnToggleDiff?.addEventListener('click', () => {
    diffModeActive = !diffModeActive;
    if (brdDiffView) brdDiffView.style.display = diffModeActive ? 'grid' : 'none';
    if (btnToggleDiff) btnToggleDiff.textContent = diffModeActive ? 'Hide Baseline Diff' : 'Toggle Baseline Diff';
  });

  btnCopyMd?.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/export/markdown');
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      showToast('Governed BRD Markdown copied to clipboard!');
    } catch {
      alert('Failed copying to clipboard.');
    }
  });

  // --------------------------------------------------------------------------
  // Module 5: Cryptographic Audit Ledger & Scrubber
  // --------------------------------------------------------------------------
  function renderAuditLedger(state) {
    if (!auditChainRows || !state.audit_chain) return;
    auditChainRows.innerHTML = '';

    state.audit_chain.forEach(entry => {
      const tr = document.createElement('tr');
      const actionSpan = entry.event === 'ADDED'
        ? '<span class="seq-action-added">[ADDED]</span>'
        : '<span class="seq-action-removed">[REMOVED]</span>';

      tr.innerHTML = `
        <td><strong>#${entry.sequence}</strong></td>
        <td>${actionSpan}</td>
        <td><code>${escapeHtml(entry.source_id)}</code></td>
        <td style="font-size: 12px;">${escapeHtml(entry.sender || '—')} ${entry.channel ? `<small style="color: var(--text-muted);">(${escapeHtml(entry.channel)})</small>` : ''}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--emerald-text);">${escapeHtml(entry.hash.slice(0, 16))}...${escapeHtml(entry.hash.slice(-8))}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${escapeHtml(entry.prev_hash.slice(0, 12))}...</td>
        <td><span class="brand-badge integrity-pending" data-integrity="${entry.sequence}">UNCHECKED</span></td>
      `;
      auditChainRows.appendChild(tr);
    });
  }

  // Reused render path: manual scrub input, cinematic replay, and automated walkthrough
  // all funnel through this one function.
  async function scrubToSequence(targetSeq) {
    if (scrubberSeqBadge) scrubberSeqBadge.textContent = `SEQUENCE #${targetSeq}`;
    try {
      const res = await fetch('/api/demo/scrub', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sequence: targetSeq }),
      });
      const data = await res.json();
      renderAllModules(data.state);
      return data.state;
    } catch (err) {
      console.error('Scrub failed:', err);
      return null;
    }
  }

  scrubber?.addEventListener('input', () => {
    stopReplay(); // a manual scrub takes over from the auto-replay
    scrubToSequence(parseInt(scrubber.value, 10));
  });

  // Chaos Buttons
  document.querySelectorAll('.chaos-test-tile').forEach(btn => {
    btn.addEventListener('click', async () => {
      const chaosType = btn.getAttribute('data-chaos');
      try {
        const res = await fetch('/api/demo/chaos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chaos_type: chaosType }),
        });
        const data = await res.json();
        const rule = data.rule_fired || 'n/a';
        const classification = data.classification || 'n/a';
        showToast(`[BLOCKED]: ${data.explanation} | RULE FIRED: ${rule} | CLASSIFICATION: ${classification}`);
      } catch (err) {
        showToast('Chaos call failed: ' + err.message);
      }
    });
  });

  function showToast(msg) {
    if (!chaosToast || !toastMessage) return;
    toastMessage.textContent = msg;
    chaosToast.style.display = 'flex';
  }

  toastClose?.addEventListener('click', () => {
    if (chaosToast) chaosToast.style.display = 'none';
  });

  // --------------------------------------------------------------------------
  // Scope Authoring Modal
  // --------------------------------------------------------------------------
  function openGovernModal(claimId) {
    if (!governModal || !govClaimId) return;
    govClaimId.value = claimId;
    document.querySelector('#govern-modal-title').textContent = `Authorize Scope Directive for ${claimId}`;

    if (claimId === 'checkout.payment_methods') {
      govDirective.value = 'Client Directive: Card is authorized in scope. UPI moves to Phase 2.';
      govValueJson.value = JSON.stringify({ methods: ['Card'], deferred: ['UPI'] }, null, 2);
    } else if (claimId === 'checkout.currency') {
      govDirective.value = 'Client Directive: Base checkout currency shall be USD.';
      govValueJson.value = JSON.stringify({ currency: 'USD' }, null, 2);
    } else if (claimId === 'auth.mfa_requirement') {
      govDirective.value = 'Client Directive: Mandatory Multi-Factor Authentication (MFA) is strictly required for all logins via TOTP and SMS.';
      govValueJson.value = JSON.stringify({ mfa_required: true, channels: ['TOTP Authenticator', 'SMS OTP'] }, null, 2);
    } else if (claimId === 'refunds.settlement_sla') {
      govDirective.value = 'Client Directive: Customer refund settlement SLA shall be 24 hours with instant automated settlement.';
      govValueJson.value = JSON.stringify({ sla_hours: 24, instant_settlement: true }, null, 2);
    }

    governModal.style.display = 'flex';
  }

  governModalClose?.addEventListener('click', () => {
    if (governModal) governModal.style.display = 'none';
  });

  governForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    let parsedVal = {};
    try {
      parsedVal = JSON.parse(govValueJson.value);
    } catch {
      alert('Value JSON is invalid syntax.');
      return;
    }

    try {
      const res = await fetch('/api/govern', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: govClaimId.value,
          directive: govDirective.value,
          value: parsedVal,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert('Authorizing rejected: ' + (data.error?.message || 'Error'));
        return;
      }
      governModal.style.display = 'none';
      appState = data.state;
      renderAllModules(appState);
      showToast(`Directive authorized as ${data.source_id}. Claim promoted to GOVERNED!`);
    } catch (err) {
      alert('Error: ' + err.message);
    }
  });

  async function withdrawScope(sourceId) {
    if (!confirm(`Revoke client scope authority for ${sourceId}?`)) return;
    try {
      const res = await fetch('/api/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: sourceId }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert('Withdrawal rejected: ' + (data.error?.message || 'Error'));
        return;
      }
      appState = data.state;
      renderAllModules(appState);
      showToast(`Authority revoked for ${sourceId}. Claim withheld and marked DISPUTED.`);
    } catch (err) {
      alert('Error: ' + err.message);
    }
  }

  // --------------------------------------------------------------------------
  // Backend status cluster (BigQuery / GCS / Vertex: cloud vs local mirror)
  // --------------------------------------------------------------------------
  function refreshCloudStatus() {
    const badges = {
      bigquery: document.querySelector('#cloud-bq'),
      gcs: document.querySelector('#cloud-gcs'),
      vertex: document.querySelector('#cloud-vertex'),
    };
    fetch('/api/cloud/status')
      .then(r => r.json())
      .then(data => {
        for (const [key, el] of Object.entries(badges)) {
          if (!el || !data[key]) continue;
          const st = data[key];
          const label = el.querySelector('.cloud-label');
          if (label) label.textContent = `${key === 'gcs' ? 'GCS' : key === 'bigquery' ? 'BigQuery' : 'Vertex'} · ${st.connected ? 'live' : 'local'}`;
          el.classList.toggle('connected', !!st.connected);
          el.title = `${key}: ${st.connected ? 'connected' : 'local mirror active'} — ${st.reason || ''}`;
        }
        // True route pill and failure reason (Task 3)
        const route = data.route || (data.extraction && data.extraction.route) || 'offline';
        const failReason = data.last_failure_reason || (data.extraction && data.extraction.last_failure_reason);
        const studioRoutePill = document.querySelector('#studio-route-pill');
        if (studioRoutePill) {
          studioRoutePill.textContent = `ROUTE: ${route.toUpperCase()}`;
          studioRoutePill.className = 'brand-badge ' + (route.startsWith('live') ? 'integrity-ok' : '');
          if (failReason) studioRoutePill.title = `Last failure: ${failReason}`;
        }
        if (extractionModeText) {
          if (route === 'live-gemini') {
            extractionModeText.textContent = 'ROUTE: LIVE-GEMINI';
            extractionModePill?.classList.add('live');
          } else if (route === 'live-vertex') {
            extractionModeText.textContent = 'ROUTE: LIVE-VERTEX';
            extractionModePill?.classList.add('live');
          } else {
            extractionModeText.textContent = 'ROUTE: OFFLINE' + (failReason ? ` (${failReason.slice(0, 30)})` : '');
            extractionModePill?.classList.remove('live');
          }
          if (extractionModePill) {
            extractionModePill.title = `True route: ${route}${failReason ? ` | Reason: ${failReason}` : ''}`;
          }
        }
      })
      .catch(() => { /* badges keep their muted "local" default */ });
  }

  // --------------------------------------------------------------------------
  // Provenance Inspector: side-by-side evidence for the headline claim,
  // opened by clicking the state banner.
  // --------------------------------------------------------------------------
  const PROVENANCE_CLAIM = 'checkout.payment_methods';

  function openProvenanceModal() {
    if (!artifactModal || !modalBody || !modalTitle || !appState) return;
    const res = appState.resolutions?.[PROVENANCE_CLAIM];
    if (!res) return;
    const active = (appState.sources || []).filter(s => s.claim_id === PROVENANCE_CLAIM && s.active);
    const typeLabel = { brd: 'Baseline document', screenshot: 'UI observation', client_note: 'Client statement' };
    const authorityLabel = { brd: 'Baseline only', screenshot: 'Cannot authorize', client_note: 'Can authorize if verified' };

    modalTitle.textContent = `Provenance \u2022 ${res.title || PROVENANCE_CLAIM} \u2022 ${res.state}`;

    const cards = active.map(s => {
      const region = Array.isArray(s.region) && s.region.length === 4 ? s.region : null;
      const shot = s.type === 'screenshot'
        ? `<div class="shot-wrap"><img class="prov-shot" data-sid="${escapeHtml(s.id)}" src="/fixtures/checkout.png" alt="Screenshot ${escapeHtml(s.id)}" style="max-width: 100%; display: block; border-radius: var(--radius-md); border: 1px solid var(--border-light);">${region ? '<div class="shot-region prov-region"></div>' : ''}</div>`
        : '';
      const governing = res.governing_source === s.id;
      return `
        <div class="prov-card ${governing ? 'prov-governing' : ''}">
          <div class="prov-card-head">
            <span class="brand-badge">${escapeHtml(s.id)}</span>
            <span class="prov-type">${escapeHtml(typeLabel[s.type] || s.type)}</span>
            <span class="prov-auth">${escapeHtml(authorityLabel[s.type] || '')}</span>
          </div>
          ${shot}
          <p class="prov-quote">&ldquo;${escapeHtml(s.quote)}&rdquo;</p>
          ${s.sender ? `<p style="font-size: 11px; color: var(--text-muted); margin: 3px 0;"><strong>Sender:</strong> ${escapeHtml(s.sender)} ${s.channel ? `&bull; <strong>Channel:</strong> ${escapeHtml(s.channel)}` : ''}</p>` : ''}
          <p class="prov-meta">${s.quote_verified ? '\u2713 Quote verified against source' : '\u26A0 Quote unverified'}${governing ? ' \u2022 GOVERNING' : ''}</p>
        </div>`;
    }).join('');

    modalBody.innerHTML = `
      <div class="prov-grid">${cards || '<p class="prov-meta">No active evidence for this claim.</p>'}</div>
      <div class="prov-verdict prov-${escapeHtml(String(res.state).toLowerCase())}">
        <strong>Resolver verdict: ${escapeHtml(res.state)}</strong>
        <p>${escapeHtml(res.reason || '')}</p>
        <p class="prov-invariant">Seeing a button is not approving the button. Only a verified client decision can govern.</p>
      </div>`;
    artifactModal.style.display = 'flex';

    // Scale each cited region onto its displayed screenshot.
    modalBody.querySelectorAll('.prov-shot').forEach(img => {
      const src = active.find(s => s.id === img.getAttribute('data-sid'));
      const ov = img.parentElement.querySelector('.prov-region');
      if (!src || !ov || !Array.isArray(src.region)) return;
      const place = () => {
        if (!img.clientWidth) return;
        const sx = img.clientWidth / (img.naturalWidth || 900);
        const sy = img.clientHeight / (img.naturalHeight || 620);
        ov.style.left = (src.region[0] * sx) + 'px';
        ov.style.top = (src.region[1] * sy) + 'px';
        ov.style.width = (src.region[2] * sx) + 'px';
        ov.style.height = (src.region[3] * sy) + 'px';
      };
      if (img.complete) place(); else img.addEventListener('load', place);
    });
  }

  const stateBannerEl = document.querySelector('#state-banner');
  if (stateBannerEl) {
    stateBannerEl.classList.add('state-banner-clickable');
    stateBannerEl.setAttribute('role', 'button');
    stateBannerEl.setAttribute('tabindex', '0');
    stateBannerEl.setAttribute('title', 'Inspect the evidence behind this verdict');
    stateBannerEl.addEventListener('click', openProvenanceModal);
    stateBannerEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openProvenanceModal(); }
    });
  }

  // --------------------------------------------------------------------------
  // Artifact Inspector Modal
  // --------------------------------------------------------------------------
  function openArtifactModal(sourceId) {
    if (!artifactModal || !modalBody || !modalTitle) return;
    const source = appState?.sources?.find(s => s.id === sourceId);
    if (!source) return;

    modalTitle.textContent = `${source.id} • ${source.type.toUpperCase()}`;

    if (source.type === 'screenshot') {
      // Artifact URL resolves server-side: signed GCS URL when cloud is
      // connected, otherwise the local /fixtures path (honest "via" label).
      fetch(`/api/artifact?source_id=${encodeURIComponent(sourceId)}`)
        .then(r => r.json())
        .then(info => {
          const src = escapeHtml(info.url || '/fixtures/checkout.png');
          const via = info.via === 'gcs' ? 'served from GCS (signed URL)' : 'served locally (/fixtures)';
          // The cited region comes from the evidence record ([x, y, w, h] in
          // original-image pixels) and is scaled to the displayed image.
          const region = Array.isArray(source.region) && source.region.length === 4 ? source.region : null;
          modalBody.innerHTML = `
        <div style="text-align: center;">
          <div class="shot-wrap">
            <img id="shot-img" src="${src}" alt="Checkout Screenshot" style="max-width: 100%; border: 1px solid var(--border-light); border-radius: var(--radius-md); display: block;">
            ${region ? '<div class="shot-region" id="shot-region" title="Cited evidence region"></div><div class="shot-region-label" id="shot-region-label">cited region</div>' : ''}
          </div>
          <div style="margin-top: 14px; font-size: 13px; color: var(--text-muted); text-align: left;">
            <strong>Detected UI Element:</strong> &ldquo;${escapeHtml(source.quote)}&rdquo;<br>
            <strong>Observation:</strong> ${escapeHtml(source.observation)}<br>
            <strong>Artifact:</strong> ${via}<br>
            ${region
              ? `<strong>Cited region:</strong> [${region.map(n => escapeHtml(String(n))).join(', ')}] on the 900&times;620 original, scaled to the displayed image.<br>`
              : '<strong>Cited region:</strong> none recorded for this evidence.<br>'}
            <span style="color: var(--crimson-text); font-weight: 700;">Invariant Check: Seeing a button is not approving the button. Observation cannot authorize.</span>
          </div>
        </div>
      `;
          if (region) {
            const placeRegion = () => {
              const img = document.querySelector('#shot-img');
              const ov = document.querySelector('#shot-region');
              const lbl = document.querySelector('#shot-region-label');
              if (!img || !ov || !img.clientWidth) return;
              const natW = img.naturalWidth || 900;
              const natH = img.naturalHeight || 620;
              const sx = img.clientWidth / natW;
              const sy = img.clientHeight / natH;
              const l = region[0] * sx, t = region[1] * sy;
              ov.style.left = l + 'px';
              ov.style.top = t + 'px';
              ov.style.width = (region[2] * sx) + 'px';
              ov.style.height = (region[3] * sy) + 'px';
              if (lbl) {
                lbl.style.left = l + 'px';
                lbl.style.top = Math.max(0, t - 2) + 'px';
              }
            };
            const shotImg = document.querySelector('#shot-img');
            if (shotImg.complete && shotImg.naturalWidth) placeRegion();
            else shotImg.addEventListener('load', placeRegion);
          }
        })
        .catch(() => {
          modalBody.innerHTML = `<div style="text-align: center;"><img src="/fixtures/checkout.png" alt="Checkout Screenshot" style="max-width: 100%;"></div>`;
        });
    } else {
      renderTextArtifact(source);
    }

    artifactModal.style.display = 'flex';
  }

  // Stream D: artifact proof — highlight the exact verified quote substring
  // inside the live source text. First tries a verbatim match; falls back to
  // an NFKC/case/whitespace-tolerant search that maps back into the original
  // text offsets. Never throws — worst case the quote shows unhighlighted.
  function normalizeForSearch(s) {
    return String(s || '')
      .normalize('NFKC')
      .replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/[–—]/g, '-')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim();
  }

  function locateQuote(text, quote) {
    if (!text || !quote) return null;
    let i = text.indexOf(quote);
    if (i >= 0) return [i, i + quote.length];
    const map = [];
    let norm = '';
    for (let k = 0; k < text.length; k++) {
      const frag = normalizeForSearch(text[k]);
      if (frag === ' ') {
        if (!norm.endsWith(' ')) { norm += ' '; map.push(k); }
      } else if (frag) {
        for (const ch of frag) { norm += ch; map.push(k); }
      }
    }
    norm = norm.trim();
    const qn = normalizeForSearch(quote);
    if (!qn || !norm) return null;
    const j = norm.indexOf(qn);
    if (j < 0 || j >= map.length) return null;
    const start = map[j];
    const endIdx = map[Math.min(j + qn.length - 1, map.length - 1)] + 1;
    return [start, Math.max(endIdx, start + 1)];
  }

  const TEXT_ARTIFACT_URLS = { brd: '/fixtures/brd.txt', client_note: '/fixtures/client_note.txt' };

  function textArtifactMeta(source) {
    return `
          <div style="border-top: 1px solid var(--border-light); padding-top: 10px; font-size: 12px;">
            <strong>Verified In Text:</strong> ${source.quote_verified ? '<span style="color: var(--emerald-text);">&check; YES</span>' : '<span style="color: var(--crimson-text);">&times; NO</span>'}<br>
            <strong>Scope Change Flag:</strong> ${source.proposed_scope_change ? 'TRUE (Authority Granted)' : 'FALSE (Observation Only)'}
          </div>`;
  }

  function renderTextArtifact(source) {
    const quoteOnly = `
        <div style="background: var(--surface-subtle); padding: 18px; border-radius: var(--radius-md); font-family: var(--font-mono); font-size: 13px;">
          <p style="margin: 0 0 10px; color: var(--text-muted); text-transform: uppercase;">Recorded Quote (artifact text unavailable):</p>
          <pre style="white-space: pre-wrap; color: var(--text-headline); margin: 0 0 16px;">${escapeHtml(source.quote)}</pre>
          ${textArtifactMeta(source)}
        </div>`;
    const url = TEXT_ARTIFACT_URLS[source.type];
    if (!url) {
      modalBody.innerHTML = quoteOnly;
      return;
    }
    modalBody.innerHTML = `
        <div style="background: var(--surface-subtle); padding: 18px; border-radius: var(--radius-md); font-family: var(--font-mono); font-size: 13px;">
          <p style="margin: 0 0 10px; color: var(--text-muted); text-transform: uppercase;">Original Evidence Text:</p>
          <pre style="white-space: pre-wrap; color: var(--text-headline); margin: 0 0 16px;">Loading artifact text&hellip;</pre>
        </div>`;
    fetch(url)
      .then(r => { if (!r.ok) throw new Error('artifact text unavailable'); return r.text(); })
      .then(text => {
        const span = locateQuote(text, source.quote);
        const body = span
          ? escapeHtml(text.slice(0, span[0]))
            + '<mark class="quote-mark">' + escapeHtml(text.slice(span[0], span[1])) + '</mark>'
            + escapeHtml(text.slice(span[1]))
          : escapeHtml(text)
            + '<p class="mark-miss">The verified quote is on the evidence record, but this live copy of the artifact no longer contains it verbatim.</p>';
        modalBody.innerHTML = `
        <div style="background: var(--surface-subtle); padding: 18px; border-radius: var(--radius-md); font-family: var(--font-mono); font-size: 13px;">
          <p style="margin: 0 0 10px; color: var(--text-muted); text-transform: uppercase;">Original Evidence Text (verified quote highlighted):</p>
          <pre style="white-space: pre-wrap; color: var(--text-headline); margin: 0 0 16px;">${body}</pre>
          ${textArtifactMeta(source)}
        </div>`;
      })
      .catch(() => { modalBody.innerHTML = quoteOnly; });
  }

  modalClose?.addEventListener('click', () => {
    if (artifactModal) artifactModal.style.display = 'none';
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (artifactModal) artifactModal.style.display = 'none';
      if (governModal) governModal.style.display = 'none';
      if (chaosToast) chaosToast.style.display = 'none';
      closeHelp();
      if (judgeActive) exitJudgeMode();
    } else if (e.key === '?' && !isInputActive()) {
      toggleHelp();
    } else if (e.key === '1' && !isInputActive() && !judgeActive) {
      triggerBeat(1);
    } else if (e.key === '2' && !isInputActive() && !judgeActive) {
      triggerBeat(2);
    } else if (e.key === '3' && !isInputActive() && !judgeActive) {
      triggerBeat(3);
    }
  });

  function isInputActive() {
    const el = document.activeElement;
    return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT');
  }

  // 3-Beat Buttons
  document.querySelector('#btn-beat-1')?.addEventListener('click', () => triggerBeat(1));
  document.querySelector('#btn-beat-2')?.addEventListener('click', () => triggerBeat(2));
  document.querySelector('#btn-beat-3')?.addEventListener('click', () => triggerBeat(3));

  // Stream E: visible stage-recovery reset — double-click-to-confirm (inline,
  // no modal) so an accidental stage wipe is hard but recovery is one click.
  const btnResetDemo = document.querySelector('#btn-reset-demo');
  let resetArmed = false;
  let resetArmTimer = null;

  function disarmReset() {
    resetArmed = false;
    if (resetArmTimer) {
      clearTimeout(resetArmTimer);
      resetArmTimer = null;
    }
    if (btnResetDemo) {
      btnResetDemo.classList.remove('armed');
      btnResetDemo.innerHTML = '&#10226; Reset State';
    }
  }

  btnResetDemo?.addEventListener('click', async () => {
    if (!resetArmed) {
      resetArmed = true;
      btnResetDemo.classList.add('armed');
      btnResetDemo.innerHTML = 'Click again to confirm reset';
      resetArmTimer = setTimeout(disarmReset, 3000);
      return;
    }
    disarmReset();
    try {
      const res = await fetch('/api/demo/reset', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        showToast('Reset rejected: ' + (data.error?.message || 'server refused the reset'));
        return;
      }
      stopFeed();
      stopReplay();
      exitJudgeMode(true);
      appState = data; // /api/demo/reset returns the snapshot directly
      currentBeat = 1;
      prevHeroState = null; // re-seed — don't animate the reset itself
      setActiveBeatBtn(1);
      renderAllModules(appState);
      showToast('System state reset to initial baseline.');
    } catch (err) {
      showToast('Reset failed: ' + err.message);
    }
  });

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ==========================================================================
  // 6. Live Evidence Feed (SSE) & Automated Walkthrough
  // ==========================================================================
  const btnJudgeMode = document.querySelector('#btn-judge-mode');
  const btnFeedStart = document.querySelector('#btn-feed-start');
  const btnFeedStop = document.querySelector('#btn-feed-stop');
  const feedTicker = document.querySelector('#feed-ticker');
  const judgeOverlay = document.querySelector('#judge-overlay');
  const judgeProgress = document.querySelector('#judge-progress');
  const judgeCaption = document.querySelector('#judge-caption');
  const judgeActions = document.querySelector('#judge-actions');

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // --------------------------------------------------------------------------
  // 6a. Live evidence feed client
  // --------------------------------------------------------------------------
  let feedSource = null;

  const FEED_ICONS = {
    slack: '\uD83D\uDCAC', email: '\u2709\uFE0F', screenshot: '\uD83D\uDCF8',
    directive: '\uD83D\uDCDC', withdrawal: '\u21A9\uFE0F',
  };
  const FEED_LABELS = {
    slack: 'SLACK', email: 'EMAIL', screenshot: 'SCREENSHOT',
    directive: 'CLIENT DIRECTIVE', withdrawal: 'WITHDRAWAL',
  };

  function setFeedButtons(running) {
    if (btnFeedStart) btnFeedStart.disabled = running;
    if (btnFeedStop) btnFeedStop.disabled = !running;
  }

  function appendFeedItem(d) {
    if (!feedTicker) return;
    if (feedTicker.querySelector('.feed-empty')) feedTicker.innerHTML = '';

    const kind = d.kind || 'email';
    const transitions = d.transitions || [];
    const deltaHtml = transitions.map(t => {
      const toGov = t.to === 'GOVERNED';
      const cls = toGov ? 'feed-tr-governed' : (t.to === 'DISPUTED' ? 'feed-tr-disputed' : 'feed-tr-other');
      return `<span class="feed-transition ${cls}">${escapeHtml(t.claim_id)}: ${escapeHtml(t.from || '?')} &rarr; ${escapeHtml(t.to)}</span>`;
    }).join('');

    const verTag = d.quote_verified
      ? '<span class="indicator-valid">&check; quote verified</span>'
      : (d.ingest_error
        ? `<span class="indicator-invalid">&times; rejected: ${escapeHtml(d.ingest_error)}</span>`
        : '<span class="indicator-invalid">&times; unverified</span>');
    const govTag = d.governing
      ? '<span class="feed-gov-tag">GOVERNING AUTHORITY</span>'
      : (d.kind === 'withdrawal' && d.withdraws
        ? `<span class="feed-gov-tag feed-gov-revoke">REVOKES ${escapeHtml(d.withdraws.source_id)}</span>`
        : '');

    const item = document.createElement('div');
    item.className = `feed-item feed-kind-${escapeHtml(kind)}`;
    item.innerHTML = `
      <span class="feed-icon" aria-hidden="true">${FEED_ICONS[kind] || '\u2709\uFE0F'}</span>
      <div class="feed-body">
        <div class="feed-meta">
          <span class="feed-kind-tag">${escapeHtml(FEED_LABELS[kind] || kind.toUpperCase())}</span>
          ${d.source_id ? `<span class="feed-sid">${escapeHtml(d.source_id)}</span>` : ''}
          <span class="feed-claim">${escapeHtml(d.claim_id || '')}</span>
        </div>
        ${d.quote ? `<p class="feed-quote">&ldquo;${escapeHtml(d.quote)}&rdquo;</p>` : ''}
        ${d.observation ? `<p class="feed-obs">${escapeHtml(d.observation)}</p>` : ''}
        <div class="feed-delta">${verTag} ${govTag} ${deltaHtml}</div>
      </div>
    `;
    feedTicker.appendChild(item);
    feedTicker.scrollTop = feedTicker.scrollHeight;
  }

  let stateFlashTimer = null;
  function flashStateBadge() {
    if (!stateEl) return;
    stateEl.classList.remove('state-flash');
    void stateEl.offsetWidth; // restart the animation
    stateEl.classList.add('state-flash');
    if (stateFlashTimer) clearTimeout(stateFlashTimer);
    stateFlashTimer = setTimeout(() => stateEl.classList.remove('state-flash'), 1600);
  }

  // Stream E: cinematic beat transition. Called from the shared render path
  // (renderCockpit) whenever the hero claim state actually changes, so beats,
  // the live feed, the replay and the scrubber all get the same choreography:
  // the giant badge flips/slides, the rationale narrative flashes, and the
  // event-log column pulses. Reuses the Stream C state-flash keyframes.
  function transitionStateBadge(oldState, newState) {
    if (!stateEl || oldState === newState) return;
    flashStateBadge(); // Stream C keyframes, reused — not duplicated

    stateEl.classList.remove('badge-flip');
    void stateEl.offsetWidth;
    stateEl.classList.add('badge-flip');
    setTimeout(() => stateEl.classList.remove('badge-flip'), 900);

    if (reasonEl) {
      reasonEl.classList.remove('narrative-flash');
      void reasonEl.offsetWidth;
      reasonEl.classList.add('narrative-flash');
      setTimeout(() => reasonEl.classList.remove('narrative-flash'), 1600);
    }

    const logColumn = eventsEl ? eventsEl.closest('.quad-column') : null;
    if (logColumn) {
      logColumn.classList.remove('log-pulse');
      void logColumn.offsetWidth;
      logColumn.classList.add('log-pulse');
      setTimeout(() => logColumn.classList.remove('log-pulse'), 1600);
    }
  }

  function handleFeedArrival(d) {
    appendFeedItem(d);
    // Reuse the exact same render path as beats / ingest — no duplicated logic.
    if (d.state) {
      appState = d.state;
      renderAllModules(appState);
    }
    const heroTransition = (d.transitions || []).find(t => t.claim_id === 'checkout.payment_methods');
    if (heroTransition) flashStateBadge();
  }

  function handleFeedEnd(d) {
    if (!feedTicker) return;
    const note = document.createElement('p');
    note.className = 'feed-end-note';
    note.textContent = d && d.will_repeat
      ? 'Scenario pass complete — looping (booth mode). Press Stop to end.'
      : 'Scenario complete — every arrival above went through the real validation pipeline and event log.';
    feedTicker.appendChild(note);
    feedTicker.scrollTop = feedTicker.scrollHeight;
    if (!(d && d.will_repeat)) stopFeed();
  }

  function startFeed() {
    if (feedSource) return;
    exitJudgeMode(true); // the feed owns the timeline while it runs
    if (feedTicker) feedTicker.innerHTML = '<p class="feed-empty">Connecting to the evidence stream&hellip;</p>';
    try {
      feedSource = new EventSource('/api/feed');
    } catch (err) {
      if (feedTicker) feedTicker.innerHTML = '<p class="feed-empty">Stream failed to start in this browser.</p>';
      return;
    }
    feedSource.addEventListener('evidence-arrival', (e) => {
      try { handleFeedArrival(JSON.parse(e.data)); } catch (err) { console.error('Feed payload error:', err); }
    });
    feedSource.addEventListener('feed-end', (e) => {
      try { handleFeedEnd(JSON.parse(e.data)); } catch (err) { stopFeed(); }
    });
    feedSource.addEventListener('feed-start', () => {
      if (feedTicker && feedTicker.querySelector('.feed-empty')) feedTicker.innerHTML = '';
    });
    feedSource.onerror = () => {
      // Fires on network drop; a clean feed-end already closed the source.
      if (feedSource && feedSource.readyState === EventSource.CLOSED) stopFeed();
    };
    setFeedButtons(true);
  }

  function stopFeed() {
    if (feedSource) {
      feedSource.close();
      feedSource = null;
    }
    setFeedButtons(false);
  }

  btnFeedStart?.addEventListener('click', startFeed);
  btnFeedStop?.addEventListener('click', stopFeed);

  // --------------------------------------------------------------------------
  // 6b. Automated walkthrough: multi-stage simulation with narration
  // --------------------------------------------------------------------------
  // Captions for the multi-stage walkthrough demonstration
  const JUDGE_CAPTIONS = {
    intro: 'One checkout claim. Three conflicting sources. One accountable answer. Automated walkthrough demonstrates deterministic authority resolution as evidence evolves.',
    1: 'Stage 1 — Conflict detected. The BRD specifies UPI only; staging shows a Card button. Two sources disagree, so ScopeShift withholds the requirement. Seeing a button is not approving the button.',
    2: 'Stage 2 — The client explicitly authorizes the change. The quote is verified against source text, an authorized client decision governs — and the BRD updates with the governing citation.',
    3: 'Stage 3 — The client withdraws the decision. The requirement is withheld from the BRD — while the immutable audit trail preserves who withdrew it, when, and the prior specification.',
    done: 'Lifecycle walkthrough complete: DISPUTED \u2192 GOVERNED \u2192 DISPUTED. Every transition is backed by a verified citation in the immutable audit log — replay it, or inspect the audit trail.',
  };

  let judgeRunToken = 0;
  let judgeActive = false;

  function setJudgeCaption(text) {
    if (judgeCaption) judgeCaption.textContent = text;
  }

  function setJudgeProgress(text) {
    if (judgeProgress) judgeProgress.textContent = text;
  }

  function showJudgeExitOnly() {
    if (!judgeActions) return;
    judgeActions.innerHTML = '';
    const btn = document.createElement('button');
    btn.className = 'btn-pill btn-outline';
    btn.textContent = 'Exit walkthrough';
    btn.addEventListener('click', () => exitJudgeMode());
    judgeActions.appendChild(btn);
  }

  function showJudgeEndCard() {
    if (!judgeActions) return;
    judgeActions.innerHTML = '';

    const replay = document.createElement('button');
    replay.className = 'btn-pill btn-primary';
    replay.textContent = '\u27F3 Replay';
    replay.addEventListener('click', () => startJudgeMode());
    judgeActions.appendChild(replay);

    const audit = document.createElement('button');
    audit.className = 'btn-pill btn-outline';
    audit.textContent = 'Open audit trail';
    audit.addEventListener('click', () => {
      exitJudgeMode();
      window.location.hash = 'audit';
    });
    judgeActions.appendChild(audit);

    const exit = document.createElement('button');
    exit.className = 'btn-pill btn-outline';
    exit.textContent = 'Exit walkthrough';
    exit.addEventListener('click', () => exitJudgeMode());
    judgeActions.appendChild(exit);
  }

  async function startJudgeMode() {
    stopFeed(); // walkthrough owns the timeline while it runs
    // Reset-aware beats always start clean: beat 1 re-seeds first.
    if (window.location.hash !== '#cockpit' && window.location.hash !== '') {
      window.location.hash = 'cockpit';
    }
    const token = ++judgeRunToken;
    judgeActive = true;
    if (judgeOverlay) judgeOverlay.style.display = 'flex';
    showJudgeExitOnly();
    setJudgeProgress('WALKTHROUGH \u2022 INTRO');
    setJudgeCaption(JUDGE_CAPTIONS.intro);
    await sleep(2600);
    if (token !== judgeRunToken) return;

    for (const beat of [1, 2, 3]) {
      if (token !== judgeRunToken) return;
      setJudgeProgress(`SIMULATION \u2022 STAGE ${beat} / 3`);
      setJudgeCaption(JUDGE_CAPTIONS[beat]);
      await triggerBeat(beat);
      if (token !== judgeRunToken) return;
      await sleep(4000);
    }
    if (token !== judgeRunToken) return;
    judgeActive = false;
    setJudgeProgress('SIMULATION \u2022 COMPLETE');
    setJudgeCaption(JUDGE_CAPTIONS.done);
    showJudgeEndCard();
  }

  function exitJudgeMode(silent) {
    judgeRunToken++;
    judgeActive = false;
    if (judgeOverlay) judgeOverlay.style.display = 'none';
    if (!silent) showJudgeExitOnly();
  }

  btnJudgeMode?.addEventListener('click', startJudgeMode);

  // ==========================================================================
  // 7. Stream D: Tier-2 Differentiators
  // ==========================================================================

  // --------------------------------------------------------------------------
  // 7a. "Ask the evidence" — deterministic Q&A over the live snapshot
  // --------------------------------------------------------------------------
  const askForm = document.querySelector('#ask-form');
  const askInput = document.querySelector('#ask-input');
  const askAnswer = document.querySelector('#ask-answer');

  document.querySelectorAll('.ask-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      if (askInput) askInput.value = chip.getAttribute('data-q') || '';
      if (askForm && typeof askForm.requestSubmit === 'function') askForm.requestSubmit();
    });
  });

  askForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = (askInput?.value || '').trim();
    if (!q || !askAnswer) return;
    askAnswer.style.display = 'block';
    askAnswer.innerHTML = '<p class="ask-loading">Consulting the evidence snapshot&hellip;</p>';
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || 'Ask failed');
      renderAskAnswer(q, data);
    } catch (err) {
      askAnswer.innerHTML = `<p class="ask-error">Could not reach the evidence engine: ${escapeHtml(err.message)}</p>`;
    }
  });

  function renderAskAnswer(question, data) {
    if (!askAnswer) return;
    const cites = (data.citations || []).map(c => `
      <li class="ask-cite">
        <span class="card-type-tag">${escapeHtml(c.source_id)}</span>
        <span>&ldquo;${escapeHtml(c.quote)}&rdquo;</span>
      </li>`).join('');
    askAnswer.innerHTML = `
      <p class="ask-q">Q: ${escapeHtml(question)}</p>
      <p class="ask-a">${escapeHtml(data.answer)}</p>
      ${cites
        ? `<ul class="ask-cites">${cites}</ul>`
        : '<p class="ask-nocite">No citations — the engine had no evidence to cite for this.</p>'}
      <span class="brand-badge ask-mode">ANSWER MODE: ${escapeHtml(String(data.mode || 'deterministic').toUpperCase())} &bull; computed from the live snapshot</span>
    `;
  }

  // --------------------------------------------------------------------------
  // 7b. Cinematic time-travel auto-replay — reuses the scrub render path
  // --------------------------------------------------------------------------
  const btnReplay = document.querySelector('#btn-replay-story');
  const btnReplayStop = document.querySelector('#btn-replay-stop');
  const replayCaption = document.querySelector('#replay-caption');
  let replayToken = 0;

  function setReplayButtons(running) {
    if (btnReplay) btnReplay.disabled = running;
    if (btnReplayStop) btnReplayStop.disabled = !running;
  }

  // Captions are derived from real event data: the event at this sequence,
  // its source record, and the resulting claim states — nothing hardcoded.
  function buildReplayCaption(seq, state) {
    const ev = (state.events || []).find(e => e.event_sequence === seq);
    const primary = (state.resolutions || {})['checkout.payment_methods'] || {};
    const st = primary.state || 'UNKNOWN';
    if (!ev) {
      return `#0 — genesis. The evidence log is empty; sources are registered but nothing is active yet → ${st}.`;
    }
    const src = (state.sources || []).find(s => s.id === ev.source_id) || {};
    const what = src.observation || src.quote || '(no description)';
    let line = `#${seq} — ${ev.source_id} (${src.type || 'unknown'}) ${ev.event}: ${what} → ${st}.`;
    if (src.type === 'screenshot' && st === 'DISPUTED') {
      line += ' Seeing a button is not approving the button — an observation can never authorize scope.';
    }
    if (ev.event === 'REMOVED') {
      line += ' The requirement leaves the BRD, but the reason is retained in the audit trail.';
    }
    return line;
  }

  async function startReplay() {
    stopFeed();
    exitJudgeMode(true); // the replay owns the timeline while it runs
    const token = ++replayToken;
    setReplayButtons(true);
    if (replayCaption) replayCaption.style.display = 'block';
    const maxSeq = scrubber ? parseInt(scrubber.max, 10) : 0;
    for (let i = 0; i <= maxSeq; i++) {
      if (token !== replayToken) return;
      if (scrubber) scrubber.value = i;
      const state = await scrubToSequence(i); // the existing scrub render path
      if (token !== replayToken) return;
      if (state && replayCaption) replayCaption.textContent = buildReplayCaption(i, state);
      await sleep(1600);
    }
    if (token !== replayToken) return;
    stopReplay();
    fetchState(); // restore the live view after the story
  }

  function stopReplay() {
    replayToken++;
    setReplayButtons(false);
    if (replayCaption) replayCaption.style.display = 'none';
  }

  btnReplay?.addEventListener('click', startReplay);
  btnReplayStop?.addEventListener('click', stopReplay);

  // --------------------------------------------------------------------------
  // 7c. Contradiction heatmap — claims × sources, computed from the snapshot
  // --------------------------------------------------------------------------
  const heatmapTable = document.querySelector('#heatmap-table');
  const heatmapDetail = document.querySelector('#heatmap-detail');

  function heatCellClass(cid, source, cite) {
    if (cite) {
      switch (cite.role) {
        case 'governing': return 'cell-govern';
        case 'conflicting': return 'cell-conflict';
        case 'baseline': return 'cell-baseline';
        case 'corroborating': return 'cell-support';
        case 'superseded': return 'cell-superseded';
        default: return 'cell-neutral';
      }
    }
    return source.claim_id === cid ? 'cell-neutral' : 'cell-na';
  }

  const HEAT_LABEL = {
    'cell-govern': 'GOVERNS', 'cell-conflict': 'CONTRADICTS', 'cell-baseline': 'BASELINE',
    'cell-support': 'SUPPORTS', 'cell-superseded': 'SUPERSEDED',
    'cell-neutral': 'NEUTRAL', 'cell-na': '—',
  };

  function renderHeatmap(state) {
    if (!heatmapTable || !state.resolutions || !state.sources) return;
    const cids = Object.keys(state.resolutions);
    const sources = [...state.sources].sort((a, b) => String(a.id).localeCompare(String(b.id)));
    const citeRole = {};
    for (const cid of cids) {
      citeRole[cid] = {};
      for (const c of (state.resolutions[cid].citations || [])) citeRole[cid][c.source_id] = c;
    }
    let html = '<thead><tr><th>Claim \\ Source</th>' +
      sources.map(s => `<th title="${escapeHtml(s.type)}">${escapeHtml(s.id)}</th>`).join('') + '</tr></thead><tbody>';
    for (const cid of cids) {
      const title = state.resolutions[cid].title || cid;
      html += `<tr><th title="${escapeHtml(cid)}">${escapeHtml(title)}</th>`;
      for (const s of sources) {
        const cls = heatCellClass(cid, s, citeRole[cid][s.id]);
        html += `<td class="heat-cell ${cls}" data-cid="${escapeHtml(cid)}" data-sid="${escapeHtml(s.id)}" tabindex="0" title="${escapeHtml(title)} × ${escapeHtml(s.id)}: ${HEAT_LABEL[cls]}">${HEAT_LABEL[cls]}</td>`;
      }
      html += '</tr>';
    }
    heatmapTable.innerHTML = html + '</tbody>';
    if (heatmapDetail) heatmapDetail.style.display = 'none';
  }

  function showHeatDetail(cid, sid) {
    if (!heatmapDetail || !appState) return;
    const r = appState.resolutions[cid];
    const src = (appState.sources || []).find(s => s.id === sid);
    if (!r || !src) return;
    const cite = (r.citations || []).find(c => c.source_id === sid);
    const role = cite ? cite.role : (src.claim_id === cid ? 'neutral' : 'unrelated');
    const counterpartRole = {
      conflicting: 'baseline', baseline: 'conflicting', governing: 'superseded',
      superseded: 'governing', corroborating: 'baseline', observation: 'baseline',
    }[role];
    const counterparts = counterpartRole ? (r.citations || []).filter(c => c.role === counterpartRole) : [];
    // FR-7 mirror: only a verified client-note scope change can govern.
    const canGovern = Boolean(src.proposed_scope_change && src.quote_verified && src.type === 'client_note');
    const verdictWord = {
      conflicting: 'CONTRADICTS', governing: 'GOVERNS', baseline: 'BASELINE',
      corroborating: 'SUPPORTS', superseded: 'SUPERSEDED', observation: 'OBSERVATION',
      neutral: 'NEUTRAL', unrelated: 'UNRELATED',
    }[role] || String(role).toUpperCase();

    const counterHtml = counterparts.length
      ? counterparts.map(c => `<div class="heat-ev"><span class="card-type-tag">${escapeHtml(c.source_id)}</span> <span class="heat-role">${escapeHtml(c.role)}</span><p>&ldquo;${escapeHtml(c.quote)}&rdquo;</p></div>`).join('')
      : '<p class="heat-none">No counterpart evidence on the other side of this pair.</p>';

    heatmapDetail.style.display = 'block';
    heatmapDetail.innerHTML = `
      <div class="heat-detail-head">
        <strong>${escapeHtml(r.title || cid)} &times; ${escapeHtml(sid)}</strong>
        <span class="brand-badge">${verdictWord}</span>
      </div>
      <div class="heat-ev-grid">
        <div class="heat-ev">
          <span class="card-type-tag">${escapeHtml(src.id)}</span>
          <span class="heat-role">${escapeHtml(src.type)} &bull; ${escapeHtml(role)}</span>
          <p>&ldquo;${escapeHtml(src.quote)}&rdquo;</p>
          <div class="heat-validation">
            quote_verified: <strong>${src.quote_verified ? 'YES' : 'NO'}</strong> &bull;
            proposed_scope_change: <strong>${src.proposed_scope_change ? 'TRUE' : 'FALSE'}</strong> &bull;
            can govern (FR-7): <strong>${canGovern ? 'YES' : 'NO'}</strong>
          </div>
        </div>
        <div class="heat-vs">vs</div>
        <div>${counterHtml}</div>
      </div>
      <p class="heat-rule"><strong>Rule:</strong> ${escapeHtml(r.rule || r.reason || '')}</p>
      <p class="heat-reason">${escapeHtml(String(r.reason || '').slice(0, 420))}</p>
    `;
    heatmapDetail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  heatmapTable?.addEventListener('click', (e) => {
    const td = e.target.closest('td.heat-cell');
    if (td && appState) showHeatDetail(td.getAttribute('data-cid'), td.getAttribute('data-sid'));
  });
  heatmapTable?.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const td = e.target.closest('td.heat-cell');
    if (td && appState) {
      e.preventDefault();
      showHeatDetail(td.getAttribute('data-cid'), td.getAttribute('data-sid'));
    }
  });

  // --------------------------------------------------------------------------
  // 7d. Verify hash chain — genuine client-side recomputation via WebCrypto
  // --------------------------------------------------------------------------
  const btnVerifyChain = document.querySelector('#btn-verify-chain');
  const verifyStatus = document.querySelector('#verify-chain-status');

  async function sha256Hex(str) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  btnVerifyChain?.addEventListener('click', async () => {
    if (!verifyStatus) return;
    if (!window.crypto || !crypto.subtle) {
      verifyStatus.textContent = 'WebCrypto unavailable in this browser — cannot verify client-side.';
      return;
    }
    verifyStatus.classList.remove('bad');
    verifyStatus.textContent = 'Recomputing hashes…';
    try {
      const res = await fetch('/api/audit/chain');
      const data = await res.json();
      const blocks = data.blocks || [];
      let prev = data.genesis_prev_hash || '0'.repeat(64);
      let okCount = 0;
      for (const b of blocks) {
        const recomputed = await sha256Hex(b.hash_input);
        const ok = recomputed === b.hash && b.prev_hash === prev;
        if (ok) okCount++;
        prev = b.hash;
        const cell = auditChainRows?.querySelector(`[data-integrity="${b.sequence}"]`);
        if (cell) {
          cell.innerHTML = ok
            ? '<span class="brand-badge integrity-ok">VERIFIED ✓</span>'
            : '<span class="brand-badge integrity-bad">MISMATCH ✗</span>';
        }
      }
      if (blocks.length > 0 && okCount === blocks.length) {
        verifyStatus.textContent = `Chain valid: ${okCount}/${blocks.length} blocks recomputed and linked.`;
      } else {
        verifyStatus.textContent = `Chain INVALID: ${blocks.length - okCount}/${blocks.length} blocks failed.`;
        verifyStatus.classList.add('bad');
      }
    } catch (err) {
      verifyStatus.textContent = 'Verification failed: ' + err.message;
      verifyStatus.classList.add('bad');
    }
  });

  // Initialize
  init3DMatrix();
  initTeleprompter();
  fetchState();
  refreshCloudStatus();

  // Route initial hash if present
  if (window.location.hash) {
    const initialKey = window.location.hash.replace(/^#\/?/, '');
    navigateTo(initialKey);
  }
})();
