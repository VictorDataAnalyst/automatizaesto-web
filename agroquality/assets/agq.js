/* ============================================================
   AGROQUALITY — interacción y movimiento
   ------------------------------------------------------------
   Stack: Lenis (scroll suave) + GSAP/ScrollTrigger (narrativa).
   Todo degrada con elegancia: si un CDN falla o el usuario
   prefiere movimiento reducido, la página funciona igual.
   ============================================================ */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 1. Navegación: fondo al hacer scroll ---------- */
  var nav = document.querySelector('.nav');
  var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 24); };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- 2. Revelado de secciones (sin dependencias) ---------- */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.rv, .rv-blur').forEach(function (el) { io.observe(el); });
  /* escalonado declarativo: data-stagger asigna --i a los hijos */
  document.querySelectorAll('[data-stagger]').forEach(function (grupo) {
    Array.prototype.forEach.call(grupo.children, function (hijo, i) { hijo.style.setProperty('--i', i); });
  });

  /* ---------- 3. Contadores del bloque de resultados ---------- */
  function contar(el) {
    var fin = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0);
    var pre = el.dataset.pre || '', suf = el.dataset.suf || '';
    var t0 = performance.now(), dur = 1600;
    function paso(t) {
      var p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - p, 4);
      el.textContent = pre + (fin * e).toFixed(dec).replace('.', ',') + suf;
      if (p < 1) requestAnimationFrame(paso);
    }
    requestAnimationFrame(paso);
  }
  var ioNum = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { contar(e.target); ioNum.unobserve(e.target); }
    });
  }, { threshold: 0.6 });
  document.querySelectorAll('[data-count]').forEach(function (el) {
    if (reduce) { contar(el); } else { ioNum.observe(el); }
  });

  /* ---------- 4. Heatmap del dashboard (14×5, determinista) ---------- */
  var hm = document.querySelector('.heatmap');
  if (hm) {
    for (var i = 0; i < 70; i++) {
      var celda = document.createElement('i');
      /* pseudo-aleatorio estable: la misma "campaña" en cada visita */
      var v = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
      celda.style.opacity = (0.06 + v * 0.85).toFixed(2);
      hm.appendChild(celda);
    }
  }

  /* ---------- 5. Curva del gráfico principal ---------- */
  var linea = document.getElementById('curva');
  var area = document.getElementById('curva-area');
  if (linea && area) {
    var pts = [72, 74, 70, 76, 79, 75, 81, 84, 80, 86, 88, 85, 90, 92];
    var W = 640, H = 210, paso2 = W / (pts.length - 1), d = '';
    pts.forEach(function (p, idx) {
      var x = idx * paso2, y = H - ((p - 60) / 40) * H;
      d += (idx === 0 ? 'M' : ' L') + x.toFixed(1) + ' ' + y.toFixed(1);
    });
    linea.setAttribute('d', d);
    area.setAttribute('d', d + ' L' + W + ' ' + H + ' L0 ' + H + ' Z');
  }

  /* ---------- 6. Movimiento premium (GSAP + Lenis, si cargaron) ---------- */
  if (reduce || typeof gsap === 'undefined') return;

  var lenis = null;
  if (typeof Lenis !== 'undefined') {
    lenis = new Lenis({ duration: 1.15, smoothWheel: true });
    function raf(t) { lenis.raf(t); requestAnimationFrame(raf); }
    requestAnimationFrame(raf);
    /* anclas internas a través de Lenis */
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        var destino = document.querySelector(a.getAttribute('href'));
        if (destino) { ev.preventDefault(); lenis.scrollTo(destino, { offset: -70 }); }
      });
    });
  }

  if (typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    if (lenis) { lenis.on('scroll', ScrollTrigger.update); }

    /* hero: la fotografía respira y se aleja al hacer scroll */
    gsap.to('.hero-bg', {
      yPercent: 12, scale: 1.06, ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true }
    });
    gsap.to('.hero .container', {
      yPercent: -8, opacity: 0.35, ease: 'none',
      scrollTrigger: { trigger: '.hero', start: '40% top', end: 'bottom top', scrub: true }
    });

    /* dispositivos: entran con profundidad y flotan con el scroll */
    gsap.from('.macbook', {
      y: 110, rotateX: 16, opacity: 0, duration: 1.4, ease: 'power4.out',
      scrollTrigger: { trigger: '.escena', start: 'top 75%' }
    });
    gsap.to('.tablet', { y: -46, ease: 'none', scrollTrigger: { trigger: '.escena', start: 'top bottom', end: 'bottom top', scrub: 1 } });
    gsap.to('.phone', { y: -70, ease: 'none', scrollTrigger: { trigger: '.escena', start: 'top bottom', end: 'bottom top', scrub: 1.4 } });

    /* fondos editoriales: parallax sutil en cada capítulo */
    ['.problema-bg', '.ai-bg', '.final-bg'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) {
        gsap.fromTo(el, { yPercent: -7 }, {
          yPercent: 7, ease: 'none',
          scrollTrigger: { trigger: el.parentElement, start: 'top bottom', end: 'bottom top', scrub: true }
        });
      }
    });

    /* frase puente: se enciende palabra por palabra */
    document.querySelectorAll('.puente p').forEach(function (p) {
      var palabras = p.textContent.trim().split(/\s+/);
      p.innerHTML = palabras.map(function (w) { return '<span style="opacity:.18">' + w + '</span>'; }).join(' ');
      gsap.to(p.querySelectorAll('span'), {
        opacity: 1, stagger: 0.06, ease: 'none',
        scrollTrigger: { trigger: p, start: 'top 78%', end: 'top 30%', scrub: true }
      });
    });
  }
})();
