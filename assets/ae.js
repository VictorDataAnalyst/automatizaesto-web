/* ============================================================
   AUTOMATIZAESTO — movimiento del sistema Ion
   Lenis (scroll) + GSAP/ScrollTrigger (narrativa).
   Degrada con elegancia: sin CDN o con movimiento reducido,
   la página funciona completa en estático.
   ============================================================ */
/* ------------------------------------------------------------
   REDES SOCIALES — único lugar donde se configuran.
   Deja la URL vacía ('') y el botón se oculta solo, sin romper
   el diseño. Igual para los LinkedIn del equipo (data-linkedin).
   ------------------------------------------------------------ */
window.AE_SOCIAL = {
  linkedin:  'https://www.linkedin.com/company/automatizaesto',
  facebook:  '',
  instagram: '',
  youtube:   '',
  x:         '',
  tiktok:    ''
};

(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* redes sociales: activa solo las que tienen URL */
  document.querySelectorAll('.social-row a[data-red]').forEach(function (a) {
    var url = (window.AE_SOCIAL || {})[a.dataset.red];
    if (url) { a.href = url; a.classList.add('on'); }
  });
  /* LinkedIn por persona: el botón aparece solo si hay URL */
  document.querySelectorAll('.btn-li[data-linkedin]').forEach(function (a) {
    if (a.dataset.linkedin) { a.href = a.dataset.linkedin; a.classList.add('on'); }
  });

  /* nav: fondo al hacer scroll */
  var nav = document.querySelector('.nav');
  var onScroll = function () { nav && nav.classList.toggle('scrolled', window.scrollY > 24); };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* revelado de capítulos */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.rv, .rv-blur').forEach(function (el) { io.observe(el); });
  document.querySelectorAll('[data-stagger]').forEach(function (g) {
    Array.prototype.forEach.call(g.children, function (h, i) { h.style.setProperty('--i', i); });
  });

  /* año del footer */
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

  /* ----------------------------------------------------------
     Filtros + búsqueda (portafolio, blog).
     Declarativo: los elementos filtrables llevan data-cat y,
     opcionalmente, data-buscar con el texto indexable.
     ---------------------------------------------------------- */
  (function filtros() {
    var grupo = document.querySelector('[data-filtros]');
    if (!grupo) return;
    var items = Array.prototype.slice.call(document.querySelectorAll('.filtrable'));
    var buscador = document.querySelector('[data-buscador]');
    var vacio = document.querySelector('[data-vacio]');
    var cat = 'todos';

    function aplicar() {
      var q = (buscador && buscador.value || '').trim().toLowerCase();
      var visibles = 0;
      items.forEach(function (el) {
        var okCat = cat === 'todos' || (el.dataset.cat || '').split(' ').indexOf(cat) !== -1;
        var texto = (el.dataset.buscar || el.textContent || '').toLowerCase();
        var okQ = !q || texto.indexOf(q) !== -1;
        var ver = okCat && okQ;
        el.hidden = !ver;
        if (ver) visibles++;
      });
      if (vacio) vacio.hidden = visibles > 0;
    }

    grupo.addEventListener('click', function (ev) {
      var b = ev.target.closest('.filtro');
      if (!b) return;
      cat = b.dataset.cat || 'todos';
      grupo.querySelectorAll('.filtro').forEach(function (o) {
        o.setAttribute('aria-pressed', String(o === b));
      });
      aplicar();
    });
    if (buscador) buscador.addEventListener('input', aplicar);
    aplicar();
  })();

  /* ----------------------------------------------------------
     Calculadora de ROI (página AI). Estimación transparente:
     el ahorro asume una reducción conservadora del 50 % del
     tiempo de documentación — se declara en la nota al pie.
     ---------------------------------------------------------- */
  (function roi() {
    var campos = ['roi_vol', 'roi_min', 'roi_costo'].map(function (id) { return document.getElementById(id); });
    if (campos.some(function (c) { return !c; })) return;
    var outH = document.getElementById('roi_horas'), outS = document.getElementById('roi_ahorro');
    var fmt = function (n) { return Math.round(n).toLocaleString('es-PE'); };
    function calcular() {
      var vol = +campos[0].value || 0, min = +campos[1].value || 0, costo = +campos[2].value || 0;
      var horas = vol * min / 60 * 0.5;
      outH.textContent = fmt(horas) + ' h';
      outS.textContent = 'S/ ' + fmt(horas * costo);
    }
    campos.forEach(function (c) { c.addEventListener('input', calcular); });
    calcular();
  })();

  /* movimiento premium */
  if (reduce || typeof gsap === 'undefined') return;

  var lenis = null;
  if (typeof Lenis !== 'undefined') {
    lenis = new Lenis({ duration: 0.8, smoothWheel: true });
    (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        var d = document.querySelector(a.getAttribute('href'));
        if (d) { ev.preventDefault(); lenis.scrollTo(d, { offset: -70 }); }
      });
    });
  }

  if (typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    if (lenis) lenis.on('scroll', ScrollTrigger.update);

    gsap.to('.hero-bg', { yPercent: 12, scale: 1.06, ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
    gsap.to('.hero .container', { yPercent: -8, opacity: .35, ease: 'none',
      scrollTrigger: { trigger: '.hero', start: '40% top', end: 'bottom top', scrub: true } });

    ['.problema-bg', '.ai-bg', '.final-bg'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) gsap.fromTo(el, { yPercent: -7 }, { yPercent: 7, ease: 'none',
        scrollTrigger: { trigger: el.parentElement, start: 'top bottom', end: 'bottom top', scrub: true } });
    });

    /* frases puente y manifiesto: se encienden palabra por palabra */
    document.querySelectorAll('.puente p, .manifiesto p.frase').forEach(function (p) {
      if (p.querySelector('em')) return; /* conserva las frases con énfasis de color */
      var palabras = p.textContent.trim().split(/\s+/);
      p.innerHTML = palabras.map(function (w) { return '<span style="opacity:.18">' + w + '</span>'; }).join(' ');
      gsap.to(p.querySelectorAll('span'), { opacity: 1, stagger: .05, ease: 'none',
        scrollTrigger: { trigger: p, start: 'top 80%', end: 'top 35%', scrub: true } });
    });
  }
})();
