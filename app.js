// ScopeShift Production Engine (PS/P42 Commudle Hack Sprint)
// Modern Light Editorial Design System, Multi-Page Routing, Mobile Responsiveness & 3D Spatial Twin

(function () {
  'use strict';

  // Global App State
  let appState = null;
  let currentBeat = 1;
  let activePageId = 'page-cockpit';
  let diffModeActive = false;

  // UI Element Handles
  const stateEl = document.querySelector('#state');
  const reasonEl = document.querySelector('#reason');
  const sourcesEl = document.querySelector('#sources');
  const evidenceEl = document.querySelector('#evidence-ledger');
  const brdEl = document.querySelector('#brd');
  const eventsEl = document.querySelector('#events');
  const aiToggle = document.querySelector('#ai-toggle');
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

  // ==========================================================================
  // 1. Interactive 3D Spatial Requirements Twin Engine (Three.js Light Theme)
  // ==========================================================================
  let scene, camera, renderer;
  let nodeGroup, laserGroup, gyroGroup;
  let nodeBRD, nodeScreenshot, nodeNote, gyroCore, ring1, ring2, ring3;
  let clashBeam, clashBarrier, authBeam;
  let isDragging = false, prevMouseX = 0, prevMouseY = 0;
  let targetRotationX = 0.22, targetRotationY = -0.28;
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

    renderer = new THREE.WebGLRenderer({ antialias: true });
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

    renderer.render(scene, camera);
  }

  function update3DTopology(stateName) {
    if (!gyroCore) return;

    const coreBadge = document.querySelector('#core-3d-badge');
    const coreText = document.querySelector('#core-3d-text');
    const pulseDot = coreBadge ? coreBadge.querySelector('.pill-dot') : null;

    if (stateName === 'GOVERNED') {
      gyroCore.material.color.setHex(0x059669);
      gyroCore.material.emissive.setHex(0x059669);
      clashBeam.material.opacity = 0.0;
      clashBarrier.material.opacity = 0.0;
      authBeam.material.opacity = 0.95;
      nodeNote.visible = true;
      nodeNote.material.opacity = 1.0;

      if (coreText) coreText.textContent = 'TOPOLOGY: GOVERNED • CLIENT DIRECTIVE AUTHORIZED';
      if (pulseDot) pulseDot.style.background = 'var(--emerald)';
    } else if (stateName === 'DISPUTED') {
      gyroCore.material.color.setHex(0xe11d48);
      gyroCore.material.emissive.setHex(0xe11d48);
      clashBeam.material.opacity = 0.95;
      clashBarrier.material.opacity = 0.35;
      authBeam.material.opacity = 0.0;

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
      clashBeam.material.opacity = 0.0;
      clashBarrier.material.opacity = 0.0;
      authBeam.material.opacity = 0.0;

      if (coreText) coreText.textContent = 'TOPOLOGY: CONSISTENT • BRD BASELINE STANDS';
      if (pulseDot) pulseDot.style.background = 'var(--royal)';
    }
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

    const useLiveAi = Boolean(aiToggle?.checked);
    try {
      const res = await fetch('/api/demo/beat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ beat: beatNum, use_live_ai: useLiveAi }),
      });
      const data = await res.json();
      appState = data.state;

      if (data.extraction && data.extraction.mode !== 'none') {
        showLatency(data.extraction);
      } else {
        if (latencyBadge) latencyBadge.style.display = 'none';
      }

      renderAllModules(appState);
    } catch (err) {
      console.error('Beat trigger error:', err);
    }
  }

  function showLatency(meta) {
    if (!latencyBadge) return;
    latencyBadge.style.display = 'inline-flex';
    latencyBadge.textContent = `${meta.mode.toUpperCase()}: ${meta.latency_ms}ms (${meta.model || 'Gemini'})`;
  }

  function setActiveBeatBtn(beat) {
    document.querySelectorAll('.stage-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`#btn-beat-${beat}`)?.classList.add('active');
  }

  function renderAllModules(state) {
    if (!state) return;

    renderCockpit(state);
    renderClaimsMatrix(state);
    renderStudioLedger(state);
    renderGovernedBrd(state);
    renderAuditLedger(state);

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

    update3DTopology(stateStr);

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
              <span>Citations: [${r.citations ? r.citations.map(c => c.source_id).join(', ') : ''}]</span>
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
        <td>${statusText}</td>
      `;
      studioLedgerRows.appendChild(tr);
    });
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

  // --------------------------------------------------------------------------
  // Module 4: Governed BRD & Diff Viewer
  // --------------------------------------------------------------------------
  function renderGovernedBrd(state) {
    if (!brdDocView || !state.resolutions) return;

    let html = `
      <h1>Business Requirements Document (BRD) &bull; Governed Specification</h1>
      <p style="color: var(--text-muted); font-size: 13px;">
        Generated by <strong>ScopeShift Deterministic Engine</strong> (PS/P42 Commudle Hack Sprint)<br>
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
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--emerald-text);">${escapeHtml(entry.hash.slice(0, 16))}...${escapeHtml(entry.hash.slice(-8))}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${escapeHtml(entry.prev_hash.slice(0, 12))}...</td>
        <td><span class="brand-badge" style="background: var(--emerald-soft); color: var(--emerald-text); border-color: var(--emerald-border); font-size: 9px;">VERIFIED</span></td>
      `;
      auditChainRows.appendChild(tr);
    });
  }

  scrubber?.addEventListener('input', async () => {
    const targetSeq = parseInt(scrubber.value, 10);
    if (scrubberSeqBadge) scrubberSeqBadge.textContent = `SEQUENCE #${targetSeq}`;

    try {
      const res = await fetch('/api/demo/scrub', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sequence: targetSeq }),
      });
      const data = await res.json();
      renderAllModules(data.state);
    } catch (err) {
      console.error('Scrub failed:', err);
    }
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
        showToast(`[BLOCKED]: ${data.explanation}`);
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
  // Artifact Inspector Modal
  // --------------------------------------------------------------------------
  function openArtifactModal(sourceId) {
    if (!artifactModal || !modalBody || !modalTitle) return;
    const source = appState?.sources?.find(s => s.id === sourceId);
    if (!source) return;

    modalTitle.textContent = `${source.id} • ${source.type.toUpperCase()}`;

    if (source.type === 'screenshot') {
      modalBody.innerHTML = `
        <div style="text-align: center;">
          <img src="/fixtures/checkout.png" alt="Checkout Screenshot" style="max-width: 100%; border: 1px solid var(--border-light); border-radius: var(--radius-md);">
          <div style="margin-top: 14px; font-size: 13px; color: var(--text-muted); text-align: left;">
            <strong>Detected UI Element:</strong> &ldquo;${escapeHtml(source.quote)}&rdquo;<br>
            <strong>Observation:</strong> ${escapeHtml(source.observation)}<br>
            <span style="color: var(--crimson-text); font-weight: 700;">Invariant Check: Seeing a button is not approving the button. Observation cannot authorize.</span>
          </div>
        </div>
      `;
    } else {
      modalBody.innerHTML = `
        <div style="background: var(--surface-subtle); padding: 18px; border-radius: var(--radius-md); font-family: var(--font-mono); font-size: 13px;">
          <p style="margin: 0 0 10px; color: var(--text-muted); text-transform: uppercase;">Original Evidence Text:</p>
          <pre style="white-space: pre-wrap; color: var(--text-headline); margin: 0 0 16px;">${escapeHtml(source.quote)}</pre>
          <div style="border-top: 1px solid var(--border-light); padding-top: 10px; font-size: 12px;">
            <strong>Verified In Text:</strong> ${source.quote_verified ? '<span style="color: var(--emerald-text);">&check; YES</span>' : '<span style="color: var(--crimson-text);">&times; NO</span>'}<br>
            <strong>Scope Change Flag:</strong> ${source.proposed_scope_change ? 'TRUE (Authority Granted)' : 'FALSE (Observation Only)'}
          </div>
        </div>
      `;
    }

    artifactModal.style.display = 'flex';
  }

  modalClose?.addEventListener('click', () => {
    if (artifactModal) artifactModal.style.display = 'none';
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (artifactModal) artifactModal.style.display = 'none';
      if (governModal) governModal.style.display = 'none';
      if (chaosToast) chaosToast.style.display = 'none';
    } else if (e.key === '1' && !isInputActive()) {
      triggerBeat(1);
    } else if (e.key === '2' && !isInputActive()) {
      triggerBeat(2);
    } else if (e.key === '3' && !isInputActive()) {
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

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Initialize
  init3DMatrix();
  fetchState();

  // Route initial hash if present
  if (window.location.hash) {
    const initialKey = window.location.hash.replace(/^#\/?/, '');
    navigateTo(initialKey);
  }
})();
