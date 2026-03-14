/* ══════════════════════════════════════════════════════════════
   codex-fx.js — Vault-JARVIS Interactive Effects
   Boot sequence · Particle trail · Glitch · Radiation spikes
   TriptokForge / Whitepages
══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ─── BOOT SEQUENCE ─────────────────────────────────────── */
  const boot = document.getElementById('boot-seq');
  const bootLines = document.getElementById('boot-lines');

  const BOOT_SCRIPT = [
    { text: '> VAULT-TEC TERMINAL  v7.3.1',              cls: '' },
    { text: '> INITIALIZING NEURAL SUBSYSTEMS...',        cls: '' },
    { text: '> WARNING: RADIATION LEVEL ELEVATED  [47%]', cls: 'err' },
    { text: '> LOADING JARVIS OVERLAY............  OK',   cls: 'cyn' },
    { text: '> FUSION CORE STATUS:  STABLE',              cls: '' },
    { text: '> AUTHENTICATING WHITEPAGES ACCESS...',      cls: '' },
    { text: '> ACCESS GRANTED. WELCOME BACK, OPERATOR.',  cls: 'ok' },
  ];

  if (boot && bootLines) {
    let lineIdx = 0;
    const cursor = document.createElement('span');
    cursor.className = 'boot-cursor';

    function typeLine() {
      if (lineIdx >= BOOT_SCRIPT.length) {
        cursor.remove();
        setTimeout(() => {
          boot.classList.add('fade-out');
          setTimeout(() => boot.remove(), 700);
        }, 700);
        return;
      }

      const { text, cls } = BOOT_SCRIPT[lineIdx++];
      const el = document.createElement('div');
      el.className = 'boot-line' + (cls ? ' ' + cls : '');
      bootLines.appendChild(el);
      bootLines.appendChild(cursor);

      let ci = 0;
      const speed = text.length > 35 ? 14 : 18;
      const iv = setInterval(() => {
        el.textContent = text.slice(0, ++ci);
        if (ci >= text.length) {
          clearInterval(iv);
          setTimeout(typeLine, 200 + Math.random() * 120);
        }
      }, speed);
    }

    setTimeout(typeLine, 600);
  }

  /* ─── PARTICLE TRAIL ────────────────────────────────────── */
  const canvas = document.getElementById('particle-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let W = (canvas.width  = window.innerWidth);
    let H = (canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
    });

    const particles = [];
    let active = false; // only emit while mouse is moving

    window.addEventListener('mousemove', (e) => {
      active = true;
      for (let i = 0; i < 3; i++) {
        particles.push({
          x:     e.clientX + (Math.random() - 0.5) * 8,
          y:     e.clientY + (Math.random() - 0.5) * 8,
          vx:    (Math.random() - 0.5) * 1.4,
          vy:    -Math.random() * 1.5 - 0.2,
          size:  Math.random() * 2.2 + 0.4,
          life:  1,
          decay: Math.random() * 0.035 + 0.018,
          // 60% green, 40% cyan
          rgb:   Math.random() > 0.4 ? '0,255,65' : '0,234,255',
        });
      }
    });

    function renderParticles() {
      ctx.clearRect(0, 0, W, H);
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x    += p.vx;
        p.y    += p.vy;
        p.vy   += 0.018; // gentle gravity
        p.life -= p.decay;
        if (p.life <= 0) { particles.splice(i, 1); continue; }

        ctx.save();
        ctx.globalAlpha = p.life * 0.65;
        ctx.shadowColor = `rgba(${p.rgb},0.9)`;
        ctx.shadowBlur  = 7;
        ctx.fillStyle   = `rgba(${p.rgb},${p.life})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
      requestAnimationFrame(renderParticles);
    }
    renderParticles();
  }

  /* ─── RANDOM CRT GLITCH FLASH ────────────────────────────── */
  const glitch = document.createElement('div');
  glitch.className = 'glitch-flash';
  document.body.appendChild(glitch);

  function triggerGlitch() {
    const dur = Math.random() * 90 + 35;
    glitch.style.opacity = '1';
    glitch.style.transform = `translateX(${(Math.random() - 0.5) * 5}px) skewX(${(Math.random() - 0.5) * 0.5}deg)`;

    // Occasionally double-flash
    const doubleFlash = Math.random() > 0.6;
    setTimeout(() => {
      glitch.style.opacity = '0';
      glitch.style.transform = '';
      if (doubleFlash) {
        setTimeout(() => {
          glitch.style.opacity = '0.7';
          setTimeout(() => { glitch.style.opacity = '0'; }, 40);
        }, 60);
      }
    }, dur);

    setTimeout(triggerGlitch, Math.random() * 14000 + 5000);
  }
  setTimeout(triggerGlitch, 4000);

  /* ─── RADIATION SPIKE (RED FLASH) ───────────────────────── */
  const radFlash = document.createElement('div');
  Object.assign(radFlash.style, {
    position: 'fixed', inset: '0', pointerEvents: 'none',
    zIndex: '9999', opacity: '0', background: 'rgba(255,42,42,0.07)',
    transition: 'opacity 0.12s ease',
  });
  document.body.appendChild(radFlash);

  function triggerRadSpike() {
    radFlash.style.transition = 'opacity 0.08s ease';
    radFlash.style.opacity = '1';
    setTimeout(() => {
      radFlash.style.transition = 'opacity 0.25s ease';
      radFlash.style.opacity = '0';
      // Second smaller pulse
      setTimeout(() => {
        radFlash.style.transition = 'opacity 0.05s ease';
        radFlash.style.opacity = '0.55';
        setTimeout(() => {
          radFlash.style.transition = 'opacity 0.3s ease';
          radFlash.style.opacity = '0';
        }, 70);
      }, 300);
    }, 120);

    setTimeout(triggerRadSpike, Math.random() * 28000 + 14000);
  }
  setTimeout(triggerRadSpike, 9000);

  /* ─── ACTIVE SECTION TRACKING ────────────────────────────── */
  const sections = document.querySelectorAll('.doc[id]');
  const navLinks  = document.querySelectorAll('.sb-a');

  if (sections.length && navLinks.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          navLinks.forEach((l) => l.classList.remove('active'));
          const target = document.querySelector(`.sb-a[href="#${entry.target.id}"]`);
          if (target) target.classList.add('active');
        }
      });
    }, { rootMargin: '-15% 0px -75% 0px' });

    sections.forEach((s) => observer.observe(s));
  }

  /* ─── CLICK RIPPLE ON INTERACTIVE ELEMENTS ───────────────── */
  document.addEventListener('click', (e) => {
    const el = e.target.closest('a, button, .clickable');
    if (!el) return;

    const ripple = document.createElement('span');
    const rect   = el.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height) * 2;
    Object.assign(ripple.style, {
      position: 'absolute',
      borderRadius: '50%',
      width:  size + 'px',
      height: size + 'px',
      left:   (e.clientX - rect.left - size / 2) + 'px',
      top:    (e.clientY - rect.top  - size / 2) + 'px',
      background: 'rgba(0,255,65,0.12)',
      transform: 'scale(0)',
      transition: 'transform 0.5s ease, opacity 0.5s ease',
      opacity: '1',
      pointerEvents: 'none',
      zIndex: '1',
    });

    // Only if element is positioned
    const pos = getComputedStyle(el).position;
    if (pos === 'static') el.style.position = 'relative';
    el.style.overflow = 'hidden';
    el.appendChild(ripple);

    requestAnimationFrame(() => {
      ripple.style.transform = 'scale(1)';
      ripple.style.opacity = '0';
    });
    setTimeout(() => ripple.remove(), 550);
  });

})();
