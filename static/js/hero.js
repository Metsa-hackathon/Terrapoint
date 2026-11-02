/* Hero scroll parallax — a row of tree "barrier posts" lifts up and
   away on scroll. Each tree gets its own eased progress with a wave
   stagger (left leads, right trails) so the row ripples like a line
   of feathers instead of moving in lockstep. */
(function () {
  var hero = document.getElementById('landing');
  if (!hero) return;
  var trees = hero.querySelectorAll('.hero-tree');
  if (!trees.length) return;

  function clamp(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function easeInOutCubic(t) {
    return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3) / 2;
  }
  function smoothstep(a, b, t) {
    var x = clamp((t - a) / (b - a));
    return x * x * (3 - 2*x);
  }

  var ticking = false;
  function update() {
    var rect = hero.getBoundingClientRect();
    var h = rect.height || 1;
    var t = clamp((-rect.top) / h);

    // Wave stagger across the row: phase from +0.12 (leftmost leads)
    // to -0.12 (rightmost trails). Total spread = 0.24.
    var n = trees.length;
    for (var i = 0; i < n; i++) {
      var phase = (0.5 - i / Math.max(1, n - 1)) * 0.24;
      var s = easeInOutCubic(clamp(t + phase));
      trees[i].style.setProperty('--s', s);
    }

    // Opacity (shared): hold solid while lifting, then smooth fade out.
    var sOp = 1 - smoothstep(0.15, 0.95, t);
    // Content: faster fade so the text clears the stage early.
    var sContent = easeInOutCubic(clamp(t * 1.6));

    hero.style.setProperty('--s-op',      sOp);
    hero.style.setProperty('--s-content', sContent);
    ticking = false;
  }
  function onScroll() {
    if (!ticking) { requestAnimationFrame(update); ticking = true; }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
})();
