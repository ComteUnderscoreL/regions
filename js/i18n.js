/* Shared language, navigation and help for both static pages. */
(() => {
  const supported = ['fr', 'en'];
  const queryLanguage = new URLSearchParams(location.search).get('lang');
  let savedLanguage;
  try { savedLanguage = localStorage.getItem('nme-language'); } catch { /* Storage may be disabled. */ }
  const lang = supported.includes(queryLanguage) ? queryLanguage
    : supported.includes(savedLanguage) ? savedLanguage : 'fr';
  const locale = lang === 'fr' ? 'fr-FR' : 'en-US';
  const messages = {
    fr: {
      subtitle: 'Explorez des pays, territoires et régions à travers des challenges GeoGuessr pinpointables.',
      medals: 'Médailles', player: 'Joueur', playerHint: 'Cliquez sur un pseudo pour découvrir son globe',
      played: 'Joués', total: 'Total', loading: 'Chargement…', noScores: 'Aucun score pour le moment',
      scoresError: 'Impossible de charger les scores. Réessayez plus tard.',
      globeError: 'Impossible de charger le globe. Réessayez plus tard.',
      playHint: 'Cliquez pour jouer au challenge actuel', progress: 'Progression de l’explorateur',
      region: 'Territoire', bestScore: 'Meilleur score', time: 'Temps', medal: 'Médaille', challenge: 'Challenge',
      back: '← Globe', open: 'Ouvrir', regionsPlayed: 'territoires joués', perfects: 'scores parfaits',
      notPlayed: 'Pas encore joué', noMedal: 'Sans médaille', noScore: 'Aucun score',
      netherite: 'Netherite', emerald: 'Émeraude', diamond: 'Diamant', gold: 'Or', iron: 'Fer', copper: 'Cuivre',
      language: 'Langue', info: 'Comment jouer ?', close: 'Fermer', helpTitle: 'Bienvenue sur No Move Explorer',
      conceptTitle: "Le principe",
      concept: "Le <strong>No Move Explorer</strong> est une collection de challenges sur des pays, régions et îles, positionnés autour d’un globe. Certains territoires ont peu, voire pas de Street View officiel.",
      pinpoint: "Les points sont tous pensés pour être <strong>5kables</strong> en <strong>no move</strong>, grâce aux indices ou au paysage.",
      playTitle: "Les challenges",
      play: "Cliquez sur un territoire du globe pour ouvrir son challenge. Vous disposez d’<strong>une seule</strong> tentative par challenge pendant la saison d’<strong>automne</strong>. Les scores sont mis à jour automatiquement et régulièrement.",
      timing: "Chaque challenge comporte <strong>cinq manches</strong>, avec un maximum de <strong>5 minutes</strong> par point. Pour les médailles, le temps correspond au <strong>total</strong> des cinq manches.",
      medalsTitle: "Les médailles",
      medalsIntro: "Chaque challenge vous permet d’obtenir une médaille selon votre score et votre temps. La médaille la plus élevée correspondant à votre résultat est retenue.",
      netheriteRule: "25 000 points en moins de 5 minutes",
      emeraldRule: "25 000 points en moins de 10 minutes",
      diamondRule: "25 000 points",
      goldRule: "Au moins 22 500 points",
      ironRule: "Au moins 15 000 points",
      copperRule: "Au moins 5 000 points",
      limits: "En dessous de 5 000 points : aucune médaille. À exactement 5 minutes : Émeraude ; à exactement 10 minutes : Diamant.",
      personalTitle: "Votre globe personnel",
      personal: "Une fois qu’un de vos scores est enregistré sur le site, vous pouvez <strong>cliquer</strong> sur votre <strong>pseudo</strong> pour découvrir votre globe personnel, vos scores et vos médailles.",
      weekly: "Un nouveau territoire sera ajouté chaque semaine durant tout l’automne.",
      imageryTitle: "Photosphères et orientation",
      imagery: "Certains points sont des photosphères non officielles, normalement <strong>orientées vers le nord dans la vue de départ</strong>. Leur boussole peut être inexacte : appuyez sur la touche <strong>R</strong> pour retrouver la position initiale.",
    },
    en: {
      subtitle: 'Explore countries, territories and regions through pinpointable GeoGuessr challenges.',
      medals: 'Medals', player: 'Player', playerHint: 'Click a player name to explore their globe',
      played: 'Played', total: 'Total', loading: 'Loading…', noScores: 'No scores yet',
      scoresError: 'Could not load scores. Please try again later.', globeError: 'Could not load the globe. Please try again later.',
      playHint: 'Click to play the current challenge', progress: 'Explorer progress', region: 'Territory',
      bestScore: 'Best score', time: 'Time', medal: 'Medal', challenge: 'Challenge', back: '← Globe', open: 'Open',
      regionsPlayed: 'territories played', perfects: 'perfect scores', notPlayed: 'Not played yet', noMedal: 'No medal', noScore: 'No score yet',
      netherite: 'Netherite', emerald: 'Emerald', diamond: 'Diamond', gold: 'Gold', iron: 'Iron', copper: 'Copper',
      language: 'Language', info: 'How to play', close: 'Close', helpTitle: 'Welcome to No Move Explorer',
      conceptTitle: "The idea",
      concept: "<strong>No Move Explorer</strong> is a collection of challenges featuring countries, regions and islands, placed around a globe. Some territories have little or no official Street View coverage.",
      pinpoint: "Every location is designed to be <strong>pinpointable for 5,000 points</strong> in <strong>no move</strong>, using clues or the landscape.",
      playTitle: "The challenges",
      play: "Click a territory on the globe to open its challenge. You get <strong>one attempt</strong> per challenge during the <strong>autumn</strong> season. Scores are updated automatically at regular intervals.",
      timing: "Each challenge has <strong>five rounds</strong>, with a maximum of <strong>5 minutes</strong> per location. Medal times refer to the <strong>combined time</strong> of all five rounds.",
      medalsTitle: "Medals",
      medalsIntro: "Each challenge can earn you a medal based on your score and time. You receive the highest medal tier your result qualifies for.",
      netheriteRule: "25,000 points in under 5 minutes",
      emeraldRule: "25,000 points in under 10 minutes",
      diamondRule: "25,000 points",
      goldRule: "At least 22,500 points",
      ironRule: "At least 15,000 points",
      copperRule: "At least 5,000 points",
      limits: "Below 5,000 points: no medal. Exactly 5 minutes earns Emerald; exactly 10 minutes earns Diamond.",
      personalTitle: "Your personal globe",
      personal: "Once one of your scores has been recorded on the site, <strong>click</strong> your <strong>username</strong> to discover your personal globe, scores and medals.",
      weekly: "A new territory will be added every week throughout autumn.",
      imageryTitle: "Photospheres and orientation",
      imagery: "Some locations are unofficial photospheres, normally <strong>facing north in the starting view</strong>. Their compass may be inaccurate: press <strong>R</strong> to return to the starting position.",
    }
  };
  function t(key) { return messages[lang][key] ?? messages.fr[key] ?? key; }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
  }
  // Keep native names. Translate only display names, never region IDs or score data.
  const names = {
    en: {'Pays basque':'Basque Country', 'Cornouailles':'Cornwall', 'Vallée d’Aoste':'Aosta Valley',
      'Savoie':'Savoy', 'Kabylie':'Kabylia', 'Îles Sorlingues':'Isles of Scilly', 'Cap-Vert':'Cape Verde',
      'Kurdistan irakien':'Iraqi Kurdistan', 'Nakhitchevan':'Nakhchivan', 'Adjarie':'Adjara',
      'Bretagne':'Brittany', 'Macédoine du Pirin':'Pirin Macedonia', 'Macédoine du Nord':'North Macedonia'},
    fr: {'Montenegro':'Monténégro', 'Isle of Wight':'Île de Wight'}
  };
  function regionName(region) {
    const value = region['name_' + lang] || region.name || region.id;
    const parts = String(value).split(/<br\s*\/?\s*>/i).map(part => names[lang][part.trim()] || part.trim());
    return [...new Set(parts)].map(escapeHtml).join('<br>');
  }
  function pageUrl(path) {
    const url = new URL(path, location.href);
    url.searchParams.set('lang', lang);
    return url.href;
  }
  window.I18n = {lang, locale, t, regionName, escapeHtml, pageUrl};
  document.documentElement.lang = lang;
  try { localStorage.setItem('nme-language', lang); } catch { /* Optional preference. */ }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-local-link]').forEach(el => { el.href = pageUrl(el.getAttribute('href')); });
    document.querySelectorAll('[data-medal-label]').forEach(el => {
      el.alt = t(el.dataset.medalLabel);
      el.title = t(el.dataset.medalLabel);
    });
    const controls = document.createElement('nav');
    controls.className = 'site-controls';
    controls.setAttribute('aria-label', t('language') + ' / ' + t('info'));
    controls.innerHTML = `<div class="language-switch" role="group" aria-label="${t('language')}">
      <button type="button" lang="fr" data-language="fr" aria-label="Français" aria-pressed="${lang === 'fr'}">FR</button>
      <button type="button" lang="en" data-language="en" aria-label="English" aria-pressed="${lang === 'en'}">EN</button>
      </div><button type="button" class="info-button" aria-label="${t('info')}" title="${t('info')}" aria-haspopup="dialog" aria-controls="help-dialog">i</button>`;
    document.body.prepend(controls);
    controls.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => {
      if (button.dataset.language === lang) return;
      const url = new URL(location.href);
      url.searchParams.set('lang', button.dataset.language);
      location.assign(url.href);
    }));
    const dialog = document.createElement('dialog');
    dialog.id = 'help-dialog';
    dialog.className = 'help-dialog';
    dialog.setAttribute('aria-labelledby', 'help-title');
    const section = (title, keys) => `<section><h3>${t(title)}</h3>${keys.map(key => `<p>${t(key)}</p>`).join('')}</section>`;
    const medalKeys = ['netherite', 'emerald', 'diamond', 'gold', 'iron', 'copper'];
    dialog.innerHTML = `<div class="help-heading"><h2 id="help-title">${t('helpTitle')}</h2><button type="button" class="help-close" aria-label="${t('close')}" autofocus>×</button></div>
      ${section('conceptTitle', ['concept','pinpoint'])}${section('playTitle', ['play','timing','weekly'])}
      <section><h3>${t('medalsTitle')}</h3><p>${t('medalsIntro')}</p><ul class="help-medals">${medalKeys.map(key => `<li><img src="https://raw.githubusercontent.com/ComteUnderscoreL/geostats/main/medal/${key}.svg" alt="" loading="lazy"><span><strong>${t(key)}</strong><br>${t(key + 'Rule')}</span></li>`).join('')}</ul><p>${t('limits')}</p></section>
      ${section('personalTitle', ['personal'])}
      ${section('imageryTitle', ['imagery'])}`;
    document.body.append(dialog);
    const info = controls.querySelector('.info-button');
    info.addEventListener('click', () => { dialog.showModal(); document.body.classList.add('help-open'); });
    dialog.querySelector('.help-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { document.body.classList.remove('help-open'); info.focus({preventScroll: true}); });
    let outsideStart = false;
    const outside = event => {
      const box = dialog.getBoundingClientRect();
      return event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom;
    };
    dialog.addEventListener('pointerdown', event => { outsideStart = event.target === dialog && outside(event); });
    dialog.addEventListener('click', event => { if (outsideStart && event.target === dialog && outside(event)) dialog.close(); outsideStart = false; });
  });
})();
