/* Hoia päise otsing nähtaval ainult siis, kui tulemuste vaade on avatud. */
(function () {
  var landing = document.getElementById('landing');
  var navSearch = document.getElementById('nav-search');
  if (!landing || !navSearch) return;

  function syncSearchLocation() {
    navSearch.hidden = !landing.hidden;
  }

  syncSearchLocation();
  new MutationObserver(syncSearchLocation).observe(landing, {
    attributes: true,
    attributeFilter: ['hidden'],
  });
})();
