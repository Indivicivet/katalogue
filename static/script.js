// Katalogue: Linguistic Mode Controller & UI Enhancements

(function() {
  const STORAGE_KEY = 'katalogue_lang';
  const DEFAULT_LANG = 'ja';

  function setLanguage(lang) {
    document.body.classList.remove('lang-ja', 'lang-ja-en', 'lang-ro', 'lang-en');
    document.body.classList.add('lang-' + lang);

    document.querySelectorAll('.lang-btn').forEach(btn => {
      if (btn.dataset.lang === lang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update dynamic tooltips on terminology tokens
    document.querySelectorAll('.term').forEach(el => {
      const kanji = el.dataset.kanji || '';
      const furigana = el.dataset.furigana || '';
      const romaji = el.dataset.romaji || '';
      const en = el.dataset.en || '';

      if (lang === 'ja' || lang === 'ja-en') {
        const tooltipParts = [];
        if (romaji) tooltipParts.push(romaji);
        if (en && en !== romaji) tooltipParts.push(en);
        el.setAttribute('data-tooltip', tooltipParts.join(' • '));
      } else if (lang === 'ro') {
        el.setAttribute('data-tooltip', `${kanji} [${furigana}] • ${en}`);
      } else if (lang === 'en') {
        el.setAttribute('data-tooltip', `${kanji} [${furigana}] • ${romaji}`);
      }
    });

    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) {
      // Ignore if localStorage unavailable
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    let savedLang = DEFAULT_LANG;
    try {
      savedLang = localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
    } catch (e) {}

    setLanguage(savedLang);

    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        setLanguage(btn.dataset.lang);
      });
    });
  });
})();
