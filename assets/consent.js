/*
 * automatizaesto — Consentimiento de cookies + Google Analytics 4
 *
 * GA4 solo se carga DESPUÉS de que el visitante acepta (cumplimiento RGPD/LGPD).
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
    return /\/(blog|servicios|agrofield|forecast|portafolio)\//.test(location.pathname) ? '../' : '';
  }

  function showBanner() {
    var style = document.createElement('style');
    style.textContent =
      '.ae-cookie-banner{position:fixed;bottom:20px;left:20px;right:20px;max-width:480px;margin:0 auto;' +
      'background:#15151a;border:1px solid #3a3a45;border-radius:18px;padding:20px 22px;z-index:9999;' +
      'box-shadow:0 12px 40px rgba(0,0,0,.55);font-family:\'Inter Tight\',-apple-system,sans-serif;' +
      'color:#f2f0ea;animation:ae-cb-in .35s ease both}' +
      '@keyframes ae-cb-in{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}' +
      '.ae-cookie-banner p{margin:0 0 14px;font-size:.88rem;line-height:1.55;color:#8a8a94}' +
      '.ae-cookie-banner p strong{color:#f2f0ea;font-weight:600}' +
      '.ae-cookie-banner a{color:#7c5cff;text-decoration:none}' +
      '.ae-cookie-banner .ae-cb-actions{display:flex;gap:10px;flex-wrap:wrap}' +
      '.ae-cookie-banner button{cursor:pointer;border-radius:10px;padding:9px 18px;font-size:.85rem;' +
      'font-weight:600;font-family:inherit;transition:opacity .2s,background .2s}' +
      '.ae-cb-accept{background:#7c5cff;border:1px solid #7c5cff;color:#0a0a0b}' +
      '.ae-cb-accept:hover{opacity:.85}' +
      '.ae-cb-reject{background:transparent;border:1px solid #3a3a45;color:#8a8a94}' +
      '.ae-cb-reject:hover{background:#1c1c22;color:#f2f0ea}';
    document.head.appendChild(style);

    var banner = document.createElement('div');
    banner.className = 'ae-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Aviso de cookies');
    banner.innerHTML =
      '<p><strong>🍪 Usamos cookies de análisis</strong><br>' +
      'Nos ayudan a entender qué contenido te resulta útil. No usamos cookies de publicidad. ' +
      'Más detalles en nuestra <a href="' + rootPath() + 'legal.html">política de privacidad</a>.</p>' +
      '<div class="ae-cb-actions">' +
      '<button type="button" class="ae-cb-accept">Aceptar</button>' +
      '<button type="button" class="ae-cb-reject">Rechazar</button>' +
      '</div>';

    banner.querySelector('.ae-cb-accept').addEventListener('click', function () {
      saveConsent('accepted');
      banner.remove();
      loadAnalytics();
    });
    banner.querySelector('.ae-cb-reject').addEventListener('click', function () {
      saveConsent('rejected');
      banner.remove();
    });

    document.body.appendChild(banner);
  }

  function init() {
    var consent = consentGiven();
    if (consent === 'accepted') {
      loadAnalytics();
    } else if (consent === null) {
      showBanner();
    }
    // 'rejected' → no banner, no analytics
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
