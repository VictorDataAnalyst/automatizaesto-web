/*
 * automatizaesto — Consentimiento de cookies + Google Analytics 4
 *
 * Modal centrado y bloqueante (estilo enterprise) que aparece antes de navegar.
 * GA4 solo se carga DESPUÉS de que el visitante acepta la analítica (RGPD/LGPD).
 *
 * El sitio solo usa cookies de analítica (Google Analytics). No hay cookies de
 * publicidad ni de orientación, por eso el panel de preferencias es honesto:
 * una categoría necesaria (siempre activa) y una de análisis (opcional).
 */
(function () {
  'use strict';

  var GA_MEASUREMENT_ID = 'G-8M7KKRZY2V';
  var STORAGE_KEY = 'ae-cookie-consent';  // 'accepted' | 'rejected'

  function loadAnalytics() {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_MEASUREMENT_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', GA_MEASUREMENT_ID, { anonymize_ip: true });
  }

  function consentGiven() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function saveConsent(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) { /* navegación privada */ }
  }

  function rootPath() {
    // legal.html está en la raíz; desde subcarpetas (/blog, /servicios...) hay que subir un nivel
    return /\/(blog|servicios|agrofield|forecast|portafolio|roadmap|casos)\//.test(location.pathname) ? '../' : '';
  }

  function lockScroll(on) {
    document.documentElement.style.overflow = on ? 'hidden' : '';
    document.body.style.overflow = on ? 'hidden' : '';
  }

  function injectStyles() {
    if (document.getElementById('ae-cookie-style')) return;
    var style = document.createElement('style');
    style.id = 'ae-cookie-style';
    style.textContent =
      '.ae-cc-overlay{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;' +
      'padding:20px;background:rgba(8,8,12,.62);backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px);' +
      'animation:ae-cc-fade .25s ease both;overflow-y:auto}' +
      '@keyframes ae-cc-fade{from{opacity:0}to{opacity:1}}' +
      '@keyframes ae-cc-pop{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}' +
      '.ae-cc-modal{width:100%;max-width:540px;background:#15151a;border:1px solid #2c2c34;border-radius:20px;' +
      'padding:34px 34px 30px;box-shadow:0 24px 70px rgba(0,0,0,.6);' +
      'font-family:\'Inter Tight\',Inter,-apple-system,BlinkMacSystemFont,sans-serif;color:#f2f0ea;' +
      'animation:ae-cc-pop .3s ease both;max-height:calc(100vh - 40px);overflow-y:auto}' +
      '.ae-cc-modal h2{margin:0 0 14px;font-size:1.5rem;font-weight:600;text-align:center;letter-spacing:-.01em;color:#fff}' +
      '.ae-cc-modal p{margin:0 0 22px;font-size:.9rem;line-height:1.6;color:#a7a7b0;text-align:center}' +
      '.ae-cc-modal p.left{text-align:left;margin-bottom:18px}' +
      '.ae-cc-modal a{color:#9b82ff;text-decoration:none}.ae-cc-modal a:hover{text-decoration:underline}' +
      '.ae-cc-actions{display:flex;flex-direction:column;gap:11px}' +
      '.ae-cc-btn{cursor:pointer;border-radius:30px;padding:13px 22px;font-size:.92rem;font-weight:600;' +
      'font-family:inherit;transition:opacity .2s,background .2s,border-color .2s;text-align:center;width:100%}' +
      '.ae-cc-primary{background:#7c5cff;border:1px solid #7c5cff;color:#fff}.ae-cc-primary:hover{opacity:.88}' +
      '.ae-cc-secondary{background:transparent;border:1px solid #3a3a45;color:#f2f0ea}' +
      '.ae-cc-secondary:hover{background:#1d1d24;border-color:#4a4a57}' +
      '.ae-cc-link{background:none;border:none;color:#9b82ff;font-weight:600;font-family:inherit;font-size:.9rem;' +
      'cursor:pointer;padding:8px;margin-top:2px}.ae-cc-link:hover{text-decoration:underline}' +
      '.ae-cc-prefs{display:none;text-align:left;margin-bottom:8px}' +
      '.ae-cc-cat{display:flex;align-items:flex-start;gap:14px;padding:15px 0;border-top:1px solid #26262e}' +
      '.ae-cc-cat:first-child{border-top:none}' +
      '.ae-cc-cat-txt h4{margin:0 0 3px;font-size:.92rem;font-weight:600;color:#f2f0ea}' +
      '.ae-cc-cat-txt span{font-size:.8rem;line-height:1.5;color:#8a8a94}' +
      '.ae-cc-sw{position:relative;flex-shrink:0;width:42px;height:24px;margin-top:2px}' +
      '.ae-cc-sw input{opacity:0;width:0;height:0;position:absolute}' +
      '.ae-cc-sl{position:absolute;inset:0;background:#3a3a45;border-radius:30px;transition:background .2s;cursor:pointer}' +
      '.ae-cc-sl::before{content:"";position:absolute;height:18px;width:18px;left:3px;top:3px;background:#f2f0ea;' +
      'border-radius:50%;transition:transform .2s}' +
      '.ae-cc-sw input:checked + .ae-cc-sl{background:#7c5cff}' +
      '.ae-cc-sw input:checked + .ae-cc-sl::before{transform:translateX(18px)}' +
      '.ae-cc-sw input:disabled + .ae-cc-sl{background:#7c5cff;opacity:.45;cursor:not-allowed}' +
      '.ae-cc-note{font-size:.78rem;color:#6f6f78;margin:12px 0 0;text-align:left}' +
      '@media(max-width:560px){.ae-cc-modal{padding:26px 22px}.ae-cc-modal h2{font-size:1.3rem}}';
    document.head.appendChild(style);
  }

  function showModal() {
    injectStyles();
    lockScroll(true);

    var overlay = document.createElement('div');
    overlay.className = 'ae-cc-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Manejo de cookies');

    var legal = rootPath() + 'legal.html#cookies';
    overlay.innerHTML =
      '<div class="ae-cc-modal">' +
        '<h2>Manejo de Cookies</h2>' +
        '<p id="ae-cc-intro">Usamos cookies para entender qué contenido te resulta útil y mejorar tu ' +
          'experiencia. Solo usamos cookies de <strong>análisis</strong> — <strong>no</strong> de publicidad ni ' +
          'de orientación. Más información en el <a href="' + legal + '">Aviso de Manejo de Cookies</a>.</p>' +

        // Vista de preferencias (oculta por defecto)
        '<div class="ae-cc-prefs" id="ae-cc-prefs">' +
          '<div class="ae-cc-cat">' +
            '<div class="ae-cc-cat-txt"><h4>Estrictamente necesarias</h4>' +
              '<span>Permiten el funcionamiento básico (recordar tu elección de cookies y el tema claro/oscuro). ' +
              'Siempre activas.</span></div>' +
            '<label class="ae-cc-sw"><input type="checkbox" checked disabled aria-label="Necesarias (siempre activas)"><span class="ae-cc-sl"></span></label>' +
          '</div>' +
          '<div class="ae-cc-cat">' +
            '<div class="ae-cc-cat-txt"><h4>Análisis y rendimiento</h4>' +
              '<span>Google Analytics (IP anonimizada) para saber qué páginas se visitan. Puedes desactivarlas.</span></div>' +
            '<label class="ae-cc-sw"><input type="checkbox" id="ae-cc-analytics" aria-label="Análisis y rendimiento"><span class="ae-cc-sl"></span></label>' +
          '</div>' +
          '<p class="ae-cc-note">No utilizamos cookies de publicidad ni de orientación.</p>' +
        '</div>' +

        '<div class="ae-cc-actions" id="ae-cc-main">' +
          '<button type="button" class="ae-cc-btn ae-cc-primary" id="ae-cc-accept">Aceptar todas las cookies opcionales</button>' +
          '<button type="button" class="ae-cc-btn ae-cc-secondary" id="ae-cc-reject">Rechazar todas las cookies opcionales</button>' +
          '<button type="button" class="ae-cc-link" id="ae-cc-config">Configure sus preferencias de cookies</button>' +
        '</div>' +

        '<div class="ae-cc-actions" id="ae-cc-save" style="display:none">' +
          '<button type="button" class="ae-cc-btn ae-cc-primary" id="ae-cc-savebtn">Guardar preferencias</button>' +
          '<button type="button" class="ae-cc-link" id="ae-cc-back">← Volver</button>' +
        '</div>' +
      '</div>';

    function close() { lockScroll(false); overlay.remove(); }
    function accept() { saveConsent('accepted'); close(); loadAnalytics(); }
    function reject() { saveConsent('rejected'); close(); }

    overlay.querySelector('#ae-cc-accept').addEventListener('click', accept);
    overlay.querySelector('#ae-cc-reject').addEventListener('click', reject);

    overlay.querySelector('#ae-cc-config').addEventListener('click', function () {
      overlay.querySelector('#ae-cc-prefs').style.display = 'block';
      overlay.querySelector('#ae-cc-main').style.display = 'none';
      overlay.querySelector('#ae-cc-save').style.display = 'flex';
      overlay.querySelector('#ae-cc-intro').textContent =
        'Elige qué cookies opcionales permites. Las necesarias no se pueden desactivar.';
    });
    overlay.querySelector('#ae-cc-back').addEventListener('click', function () {
      overlay.querySelector('#ae-cc-prefs').style.display = 'none';
      overlay.querySelector('#ae-cc-main').style.display = 'flex';
      overlay.querySelector('#ae-cc-save').style.display = 'none';
    });
    overlay.querySelector('#ae-cc-savebtn').addEventListener('click', function () {
      overlay.querySelector('#ae-cc-analytics').checked ? accept() : reject();
    });

    document.body.appendChild(overlay);
    overlay.querySelector('#ae-cc-accept').focus();
  }

  function init() {
    var consent = consentGiven();
    if (consent === 'accepted') {
      loadAnalytics();
    } else if (consent === null) {
      showModal();
    }
    // 'rejected' → sin modal, sin analytics
  }

  // Permite reabrir el panel desde un enlace: <a href="#" data-cookie-prefs>
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-cookie-prefs]');
    if (t) { e.preventDefault(); showModal(); }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
