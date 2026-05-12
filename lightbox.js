/**
 * Lightweight Lightbox — works for <img> and <video> elements.
 * Include this script at the bottom of any project page.
 * Automatically makes all images and videos inside .main-content clickable.
 */
(function () {

  /* ── Build the overlay DOM ─────────────────────────────────────── */
  const overlay = document.createElement('div');
  overlay.id = 'lb-overlay';
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-label', 'Media viewer');
  overlay.innerHTML = `
    <button id="lb-close" aria-label="Close">&times;</button>
    <div id="lb-media-wrap"></div>
    <p id="lb-caption"></p>
  `;
  document.body.appendChild(overlay);

  /* ── Inject styles ─────────────────────────────────────────────── */
  const style = document.createElement('style');
  style.textContent = `
    #lb-overlay {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 8000;
      background: rgba(0, 0, 0, 0.88);
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: 14px;
      padding: 32px;
      cursor: zoom-out;
      animation: lb-fade-in 0.18s ease;
    }
    #lb-overlay.lb-active { display: flex; }

    @keyframes lb-fade-in {
      from { opacity: 0; }
      to   { opacity: 1; }
    }

    #lb-close {
      position: fixed;
      top: 20px;
      right: 26px;
      background: none;
      border: none;
      color: rgba(255,255,255,0.7);
      font-size: 36px;
      line-height: 1;
      cursor: pointer;
      z-index: 8001;
      transition: color 0.15s;
      font-family: sans-serif;
    }
    #lb-close:hover { color: #fff; }

    #lb-media-wrap {
      max-width: 92vw;
      max-height: 88vh;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: default;
    }

    #lb-media-wrap img {
      max-width: 92vw;
      max-height: 84vh;
      object-fit: contain;
      display: block;
      box-shadow: 0 8px 48px rgba(0,0,0,0.6);
      animation: lb-scale-in 0.18s ease;
    }

    #lb-media-wrap video {
      max-width: 92vw;
      max-height: 84vh;
      display: block;
      box-shadow: 0 8px 48px rgba(0,0,0,0.6);
      animation: lb-scale-in 0.18s ease;
      cursor: default;
    }

    @keyframes lb-scale-in {
      from { transform: scale(0.95); opacity: 0; }
      to   { transform: scale(1);    opacity: 1; }
    }

    #lb-caption {
      font-family: "Neue Haas Grotesk", "Haas Grot Text", "Helvetica Neue", Arial, sans-serif;
      font-size: 11px;
      letter-spacing: 0.06em;
      color: rgba(255, 255, 255, 0.5);
      text-align: center;
      max-width: 680px;
      line-height: 1.5;
      margin: 0;
    }

    /* Cursor hint on clickable media */
    .lb-trigger {
      cursor: zoom-in;
      transition: opacity 0.2s;
    }
    .lb-trigger:hover { opacity: 0.88; }
  `;
  document.head.appendChild(style);

  const mediaWrap = document.getElementById('lb-media-wrap');
  const caption   = document.getElementById('lb-caption');
  let   activeVideo = null;

  /* ── Open ──────────────────────────────────────────────────────── */
  function openLightbox(el) {
    mediaWrap.innerHTML = '';
    caption.textContent = '';

    if (el.tagName === 'IMG') {
      const img = document.createElement('img');
      img.src = el.src;
      img.alt = el.alt || '';
      mediaWrap.appendChild(img);

      // Caption: look for sibling .image-caption
      const cap = findCaption(el);
      if (cap) caption.textContent = cap;

    } else if (el.tagName === 'VIDEO') {
      const vid = document.createElement('video');
      // Copy all <source> children
      Array.from(el.querySelectorAll('source')).forEach(s => {
        const ns = document.createElement('source');
        ns.src  = s.src;
        ns.type = s.type;
        vid.appendChild(ns);
      });
      vid.controls    = true;
      vid.autoplay    = true;
      vid.loop        = el.loop;
      vid.muted       = false;      // unmute in lightbox so user can hear
      vid.playsInline = true;
      vid.style.cursor = 'default';
      vid.addEventListener('click', e => e.stopPropagation());
      mediaWrap.appendChild(vid);
      activeVideo = vid;

      const cap = findCaption(el);
      if (cap) caption.textContent = cap;
    }

    overlay.classList.add('lb-active');
    document.body.style.overflow = 'hidden';
  }

  /* ── Close ─────────────────────────────────────────────────────── */
  function closeLightbox() {
    overlay.classList.remove('lb-active');
    document.body.style.overflow = '';
    if (activeVideo) {
      activeVideo.pause();
      activeVideo = null;
    }
    // Short delay before clearing so fade-out doesn't flash
    setTimeout(() => { mediaWrap.innerHTML = ''; caption.textContent = ''; }, 180);
  }

  /* ── Caption helper ────────────────────────────────────────────── */
  function findCaption(el) {
    // Look for .image-caption in the same parent container
    let node = el.parentElement;
    for (let i = 0; i < 4; i++) {
      if (!node) break;
      const cap = node.querySelector('.image-caption') ||
                  node.nextElementSibling;
      if (cap && cap.classList && cap.classList.contains('image-caption')) {
        return cap.textContent.trim();
      }
      if (cap && cap.tagName === 'P' && cap.classList.contains('image-caption')) {
        return cap.textContent.trim();
      }
      node = node.parentElement;
    }
    return '';
  }

  /* ── Wire up clicks ────────────────────────────────────────────── */
  function attachTriggers() {
    const selectors = [
      '.main-content .image-slot img',
      '.main-content .image-gallery img',
      '.main-content .comparison-panel img',
      '.main-content .video-block img',
      '.main-content .workflow-slot img',
      '.main-content .video-block video',
      '.main-content .video-grid-item video',
      '.main-content .hero video',
      '.hero video',
      '.hero img',
    ].join(', ');

    document.querySelectorAll(selectors).forEach(el => {
      if (el.dataset.lbBound) return;   // don't double-bind
      el.dataset.lbBound = '1';
      el.classList.add('lb-trigger');
      el.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        openLightbox(this);
      });
    });
  }

  /* ── Event listeners ───────────────────────────────────────────── */
  document.getElementById('lb-close').addEventListener('click', closeLightbox);

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeLightbox();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay.classList.contains('lb-active')) {
      closeLightbox();
    }
  });

  /* ── Init ──────────────────────────────────────────────────────── */
  // Run after DOM is fully rendered
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachTriggers);
  } else {
    attachTriggers();
  }

})();
