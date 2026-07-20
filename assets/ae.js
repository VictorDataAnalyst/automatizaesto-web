/* ============================================================
   AUTOMATIZAESTO — movimiento del sistema Ion
   Lenis (scroll) + GSAP/ScrollTrigger (narrativa).
   Degrada con elegancia: sin CDN o con movimiento reducido,
   la página funciona completa en estático.
   ============================================================ */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
