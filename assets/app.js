(() => {
  'use strict';

  const state = { data: null, filter: 'all', query: '', view: 'grid' };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = (value = '') => String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const safeUrl = (value = '') => {
    try { const url = new URL(value, location.href); return ['http:', 'https:'].includes(url.protocol) ? url.href : '#'; }
    catch { return '#'; }
  };
  const dateLong = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'long', year: 'numeric', timeZone: 'Europe/Berlin' });
  const dateShort = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'short', timeZone: 'Europe/Berlin' });
  const dateTime = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Berlin' });
  const number = new Intl.NumberFormat('de-DE');
  const parseDate = value => {
    if (!value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  };
  const formatDate = (formatter, value, fallback = '–') => {
    const parsed = parseDate(value);
    return parsed ? formatter.format(parsed) : fallback;
  };

  function imageMarkup(item, lead = false) {
    const image = safeUrl(item.image || '');
    const className = lead ? 'lead-media' : 'card-media';
    if (image === '#') return `<div class="${className}"><div class="image-fallback"><span>NRW</span></div></div>`;
    let credit = '';
    if (lead && item.imageCredit) {
      const sourceUrl = safeUrl(item.imageSourceUrl);
      const licenseUrl = safeUrl(item.imageLicenseUrl);
      const creator = sourceUrl === '#'
        ? `© ${esc(item.imageCredit)}`
        : `<a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">© ${esc(item.imageCredit)}</a>`;
      const license = licenseUrl === '#'
        ? esc(item.imageLicense || 'Lizenz')
        : `<a href="${licenseUrl}" target="_blank" rel="noopener noreferrer">${esc(item.imageLicense || 'Lizenz')}</a>`;
      const provider = item.imageProvider ? ` <span>(via ${esc(item.imageProvider)})</span>` : '';
      credit = `<span class="media-credit">${creator} / ${license}${provider}</span>`;
    }
    return `<div class="${className}"><img src="${esc(image)}" alt="${esc(item.imageAlt || '')}" loading="${lead ? 'eager' : 'lazy'}" referrerpolicy="no-referrer" data-image-fallback>${lead ? '<span class="image-scrim"></span>' : ''}${credit}${!lead && item.region ? `<span class="region-flag">${esc(item.region)}</span>` : ''}</div>`;
  }

  function metaMarkup(item, priority = '') {
    return `<div class="story-meta">${priority ? `<span class="priority">${esc(priority)}</span>` : ''}<span>${esc(item.category || item.kind || 'NRW')}</span><span>${esc(item.source?.name || item.source || 'Quelle')}</span></div>`;
  }

  function renderLead(lead) {
    const root = $('#lead-story');
    root.innerHTML = `${imageMarkup(lead, true)}<div class="lead-copy">${metaMarkup(lead, lead.kicker || 'Heute wichtig')}<h2>${esc(lead.title)}</h2><p>${esc(lead.summary)}</p><p class="why-line"><strong>Warum wichtig</strong><br>${esc(lead.whyItMatters)}</p><a class="source-link" href="${safeUrl(lead.sourceUrl)}" target="_blank" rel="noopener noreferrer">Bei ${esc(lead.source?.name || lead.source || 'der Quelle')} lesen <span aria-hidden="true">↗</span></a></div>`;
    activateImageFallbacks(root);
  }

  function renderSignals(signals = []) {
    const widths = { high: 92, watch: 66, stable: 42 };
    const labels = { high: 'hohe Dynamik', watch: 'beobachten', stable: 'stabil' };
    $('#signals-list').innerHTML = signals.map(signal => `<article class="signal"><div class="signal-top"><h3>${esc(signal.title)}</h3><span class="signal-level ${esc(signal.level)}">${esc(signal.label || labels[signal.level] || signal.level)}</span></div><p>${esc(signal.detail)}</p><div class="signal-meter signal-level ${esc(signal.level)}" aria-hidden="true"><i style="width:${Number(signal.intensity) || widths[signal.level] || 50}%"></i></div></article>`).join('');
  }

  function renderTicker(items = []) {
    const labels = items.map(item => item.label || item.title).filter(Boolean);
    const doubled = [...labels, ...labels];
    $('#ticker-track').innerHTML = doubled.map(label => `<span class="ticker-item">${esc(label)}</span>`).join('');
  }

  function renderFocus(items = []) {
    const root = $('#focus-grid');
    root.innerHTML = items.map(item => {
      const image = safeUrl(item.image || '');
      const sources = Array.isArray(item.sources) ? item.sources.length : Number(item.sourceCount) || 1;
      return `<article class="focus-card reveal">${image !== '#' ? `<div class="focus-card-bg"><img src="${esc(image)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-image-fallback></div>` : ''}<div class="focus-top"><span class="status-badge">${esc(item.status || 'beobachten')}</span><span class="days-active">seit ${Number(item.daysActive) || 1} Tagen</span></div><h3>${esc(item.title)}</h3><p>${esc(item.summary)}</p><div class="focus-footer"><span>${sources} ${sources === 1 ? 'Quelle' : 'Quellen'}</span><span>${esc(item.latestUpdate || '')}</span></div></article>`;
    }).join('');
    activateImageFallbacks(root);
    observeReveals();
  }

  function cardMarkup(item) {
    const published = parseDate(item.publishedAt);
    const sourceName = item.source?.name || item.source || 'Quelle';
    return `<article class="news-card reveal" data-kind="${esc(item.kind)}" data-search="${esc([item.title,item.summary,item.region,item.category,sourceName].join(' ').toLowerCase())}">${imageMarkup(item)}<div class="card-copy">${metaMarkup(item)}<h3>${esc(item.title)}</h3><p>${esc(item.summary)}</p>${item.whyItMatters ? `<p class="card-why"><strong>Einordnung:</strong> ${esc(item.whyItMatters)}</p>` : ''}<div class="card-footer"><a href="${safeUrl(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(sourceName)} ↗</a><time datetime="${esc(item.publishedAt || '')}">${published ? dateShort.format(published) : ''}</time></div></div></article>`;
  }

  function renderStories() {
    if (!state.data) return;
    const query = state.query.trim().toLowerCase();
    const items = state.data.stories.filter(item => {
      const kindMatches = state.filter === 'all' || item.kind === state.filter;
      const haystack = [item.title,item.summary,item.whyItMatters,item.region,item.category,item.source?.name,item.source].filter(Boolean).join(' ').toLowerCase();
      return kindMatches && (!query || haystack.includes(query));
    });
    const root = $('#news-grid');
    root.classList.toggle('list-view', state.view === 'list');
    root.innerHTML = items.map(cardMarkup).join('');
    $('#empty-state').hidden = items.length > 0;
    activateImageFallbacks(root);
    observeReveals();
  }

  function renderNewsletter(item = {}) {
    $('#newsletter-summary').textContent = item.summary || 'Noch keine Ausgabe hinterlegt.';
    $('#newsletter-highlights').innerHTML = (item.highlights || []).map(text => `<li>${esc(text)}</li>`).join('');
    const link = $('#newsletter-link');
    link.href = safeUrl(item.sourceUrl);
    $('#newsletter-date').textContent = formatDate(dateLong, item.publishedAt, 'Keine gültige Ausgabe');
  }

  function renderPolling(item = {}) {
    const root = $('#polling-panel');
    if (!root || !Array.isArray(item.parties)) return;
    const parties = item.parties.map(party => {
      const value = Math.max(0, Math.min(100, Number(party.value) || 0));
      const delta = Number(party.delta) || 0;
      const trend = delta > 0 ? `+${delta}` : String(delta).replace('-', '−');
      const trendClass = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
      return `<div class="poll-row"><div class="poll-label"><strong>${esc(party.name)}</strong><span class="poll-delta ${trendClass}" aria-label="Veränderung ${trend} Prozentpunkte">${trend}</span></div><div class="poll-track" aria-hidden="true"><i class="party-${esc(party.id)}" style="--poll-value:${value}"></i></div><span class="poll-value">${value}<small>%</small></span></div>`;
    }).join('');
    root.innerHTML = `<article class="polling-card"><header class="polling-meta"><div><span class="eyebrow">${esc(item.institute)} · ${esc(item.commissionedBy)}</span><h3>${esc(item.title)}</h3><p>${esc(item.question)}</p></div><dl><div><dt>Veröffentlicht</dt><dd>${formatDate(dateLong, item.publishedAt)}</dd></div><div><dt>Feldzeit</dt><dd>${esc(item.fieldwork || '–')}</dd></div><div><dt>Befragte</dt><dd>${number.format(Number(item.sampleSize) || 0)}</dd></div></dl></header><div class="polling-body"><div class="poll-chart"><p class="chart-caption">${esc(item.comparisonLabel || '')} · Trend in Prozentpunkten</p>${parties}</div><aside class="polling-note"><span class="eyebrow">Mehrheitsbild</span><p>${esc(item.coalitionNote || '')}</p><small>${esc(item.note || '')}</small><div class="source-pair"><a href="${safeUrl(item.sourceUrl)}" target="_blank" rel="noopener noreferrer">WDR-Erhebung ↗</a><a href="${safeUrl(item.methodologyUrl)}" target="_blank" rel="noopener noreferrer">Umfrageübersicht ↗</a></div></aside></div></article>`;
  }

  function renderCriticism(item = {}) {
    const root = $('#criticism-grid');
    if (!root) return;
    $('#criticism-intro').textContent = item.intro || 'Aktuelle Kritiklinien an der Landesregierung.';
    root.innerHTML = (item.items || []).map(entry => `<article class="criticism-card reveal"><div class="criticism-top"><span>${esc(entry.topic)}</span><i class="pressure-${entry.level === 'hoch' ? 'high' : 'watch'}">${esc(entry.level || 'beobachten')}</i></div><h3>${esc(entry.title)}</h3><div class="criticism-block"><strong>Kritik von ${esc(entry.critic)}</strong><p>${esc(entry.criticism)}</p></div><div class="criticism-block response"><strong>Einordnung / Reaktion</strong><p>${esc(entry.response)}</p></div><a href="${safeUrl(entry.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(entry.source || 'Quelle')} lesen ↗</a></article>`).join('');
    observeReveals();
  }

  function renderSocial(item = {}) {
    const profiles = $('#social-profiles');
    const performance = $('#social-performance');
    if (!profiles || !performance) return;
    $('#social-summary').textContent = item.summary || 'Aktuelle öffentliche Plattformdaten.';
    profiles.innerHTML = (item.profiles || []).map(profile => `<a class="social-profile" href="${safeUrl(profile.url)}" target="_blank" rel="noopener noreferrer"><div><span class="platform-mark">${esc((profile.platform || '?').slice(0, 2).toUpperCase())}</span><span><strong>${esc(profile.platform)}</strong><small>${esc(profile.handle)}</small></span></div><span class="availability availability-${profile.status === 'vollständig' ? 'full' : 'limited'}">${esc(profile.status)}</span>${profile.followers ? `<dl><div><dt>Follower</dt><dd>${number.format(profile.followers)}</dd></div><div><dt>Videos</dt><dd>${number.format(profile.videoCount || 0)}</dd></div><div><dt>Profil-Likes</dt><dd>${number.format(profile.profileLikes || 0)}</dd></div></dl>` : ''}<p>${esc(profile.note || '')}</p></a>`).join('');

    const tiktok = item.tiktok || {};
    const posts = tiktok.posts || [];
    const maxViews = Math.max(1, ...posts.map(post => Number(post.views) || 0));
    const postRows = posts.map((post, index) => {
      const share = Math.max(3, Math.round((Number(post.views) || 0) / maxViews * 100));
      return `<article class="social-post"><span class="post-rank">${String(index + 1).padStart(2, '0')}</span><div class="post-main"><div class="post-heading"><div><time datetime="${esc(post.publishedAt)}">${formatDate(dateShort, post.publishedAt, '')}</time><h4><a href="${safeUrl(post.url)}" target="_blank" rel="noopener noreferrer">${esc(post.title)}</a></h4></div><span class="performance-badge performance-${post.performance === 'Ausreißer' ? 'breakout' : post.performance === 'stark' ? 'strong' : 'base'}">${esc(post.performance)}</span></div><div class="views-bar"><i style="width:${share}%"></i></div><div class="post-metrics"><strong>${number.format(post.views || 0)} Views</strong><span>${number.format(post.likes || 0)} Likes</span><span>${number.format(post.comments || 0)} Kommentare</span><span>${number.format(post.reposts || 0)} Reposts</span><span>${number.format(post.durationSeconds || 0)} s</span></div></div></article>`;
    }).join('');
    performance.innerHTML = `<div class="social-performance-head"><div><span class="eyebrow">TikTok · letzte ${number.format(tiktok.sampleSize || posts.length)} Videos</span><h3>Was gepostet wurde – und wie es läuft</h3></div><time datetime="${esc(item.observedAt || '')}">Snapshot ${formatDate(dateTime, item.observedAt)} Uhr</time></div><div class="metric-strip"><div><span>Views gesamt</span><strong>${number.format(tiktok.viewsTotal || 0)}</strong></div><div><span>Median</span><strong>${number.format(tiktok.viewsMedian || 0)}</strong></div><div><span>Durchschnitt</span><strong>${number.format(tiktok.viewsAverage || 0)}</strong></div><div><span>Interaktionsrate</span><strong>${number.format(tiktok.interactionRate || 0)} %</strong></div><div><span>Top-Video-Anteil</span><strong>${number.format(tiktok.topVideoShare || 0)} %</strong></div></div><div class="social-post-list">${postRows}</div><p class="method-line">${esc(tiktok.method || '')}</p>`;
    $('#social-limitations').textContent = item.limitations || '';
  }

  function activateImageFallbacks(root = document) {
    $$('[data-image-fallback]', root).forEach(image => {
      image.addEventListener('error', () => {
        const parent = image.parentElement;
        image.remove();
        const scrim = $('.image-scrim', parent);
        if (scrim) scrim.remove();
        if (!$('.image-fallback', parent)) parent.insertAdjacentHTML('afterbegin', '<div class="image-fallback"><span>NRW</span></div>');
      }, { once: true });
    });
  }

  let revealObserver;
  function observeReveals() {
    if (!('IntersectionObserver' in window)) { $$('.reveal').forEach(el => el.classList.add('visible')); return; }
    if (!revealObserver) revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); revealObserver.unobserve(entry.target); }
    }), { threshold: .06, rootMargin: '60px' });
    $$('.reveal:not(.visible)').forEach(el => revealObserver.observe(el));
  }

  function render(data) {
    state.data = data;
    const generated = parseDate(data.meta?.generatedAt);
    $('#edition-label').textContent = generated ? `Aktualisiert ${dateTime.format(generated)} Uhr` : 'Aktuelle Ausgabe';
    $('#generated-at').textContent = generated ? `${dateTime.format(generated)} Uhr` : '–';
    $('#source-count').textContent = String(data.meta?.sourceCount ?? '–');
    $('#edition-number').textContent = `Ausgabe ${esc(data.meta?.edition || '–')}`;
    $('#editorial-note').textContent = data.meta?.editorialNote || 'Einordnung statt Endlos-Feed.';
    renderLead(data.lead || {});
    renderSignals(data.signals || []);
    renderTicker(data.ticker || []);
    renderFocus(data.focusTopics || []);
    renderStories();
    renderNewsletter(data.newsletter || {});
    renderPolling(data.polling || {});
    renderCriticism(data.governmentCriticism || {});
    renderSocial(data.socialRadar || {});
  }

  function setupInteractions() {
    const searchToggle = $('#search-toggle');
    const searchPanel = $('#search-panel');
    const searchInput = $('#global-search');
    searchToggle.addEventListener('click', () => {
      const open = searchPanel.hidden;
      searchPanel.hidden = !open;
      searchToggle.setAttribute('aria-expanded', String(open));
      if (open) setTimeout(() => searchInput.focus(), 20);
    });
    searchInput.addEventListener('input', event => { state.query = event.target.value; renderStories(); });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !searchPanel.hidden) {
        searchPanel.hidden = true; searchToggle.setAttribute('aria-expanded', 'false'); searchToggle.focus();
      }
      if (event.key === '/' && document.activeElement?.tagName !== 'INPUT') { event.preventDefault(); searchToggle.click(); }
    });

    $('#filter-rail').addEventListener('click', event => {
      const button = event.target.closest('[data-filter]'); if (!button) return;
      state.filter = button.dataset.filter;
      $$('.filter-chip').forEach(chip => { const active = chip === button; chip.classList.toggle('active', active); chip.setAttribute('aria-pressed', String(active)); });
      renderStories();
    });
    $$('.view-button').forEach(button => button.addEventListener('click', () => {
      state.view = button.dataset.view;
      $$('.view-button').forEach(other => { const active = other === button; other.classList.toggle('active', active); other.setAttribute('aria-pressed', String(active)); });
      renderStories();
    }));

    const savedTheme = localStorage.getItem('nrw-theme');
    if (savedTheme === 'light' || savedTheme === 'dark') document.documentElement.dataset.theme = savedTheme;
    $('#theme-toggle').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
      document.documentElement.dataset.theme = next; localStorage.setItem('nrw-theme', next);
    });
  }

  async function init() {
    setupInteractions();
    try {
      const response = await fetch(`data/news.json?v=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) {
      console.error('Dashboard data could not be loaded:', error);
      $('#lead-story').innerHTML = '<div class="lead-copy"><span class="eyebrow">Datenfehler</span><h2>Das Lagebild konnte nicht geladen werden.</h2><p>Bitte die Seite gleich noch einmal öffnen. Der Fehler liegt im Feed, nicht in Nordrhein-Westfalen – ausnahmsweise.</p></div>';
      $('#edition-label').textContent = 'Daten nicht verfügbar';
    }
  }

  init();
})();
