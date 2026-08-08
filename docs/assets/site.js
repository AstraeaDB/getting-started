/* Track switcher. Roughly forty lines of vanilla JavaScript, no framework.
 *
 * With JavaScript disabled the sidebar shows both tracks and every link still
 * resolves, which is the point: GitHub Pages readers include people behind
 * restrictive browsers (DESIGN.md 3.3). Everything here is progressive
 * enhancement over a site that already works without it. */
(function () {
  "use strict";

  var KEY = "astraeaTrack";
  var VALID = ["py", "r", "both"];

  function stored() {
    try {
      var v = window.localStorage.getItem(KEY);
      return VALID.indexOf(v) === -1 ? null : v;
    } catch (e) {
      return null; // private mode, or storage disabled
    }
  }

  function remember(track) {
    try {
      window.localStorage.setItem(KEY, track);
    } catch (e) {
      /* not fatal: the page just will not remember next time */
    }
  }

  /* Hide the other track's entries. A lesson marked "both" always shows, and
   * so does the page the reader is currently on, so choosing a track can never
   * hide the thing you are looking at. */
  function apply(track) {
    var current = document.body.getAttribute("data-lesson");
    document.querySelectorAll("[data-track]").forEach(function (el) {
      var t = el.getAttribute("data-track");
      if (el.tagName === "BUTTON" || el.tagName === "LINK") return;
      var isCurrent = current && el.querySelector('a[href*="' + current + '"]');
      var show = track === "both" || t === "both" || t === track || isCurrent;
      el.hidden = !show;
    });
    document.querySelectorAll("[data-set-track]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-track") === track));
    });
  }

  /* When the current page has a sibling in the chosen track, go to it. A
   * reader who switches to R on lesson two lands on lesson two in R, not back
   * at the landing page. The sibling comes from a <link rel="alternate">
   * written by build.py; we never guess it from the filename. */
  function siblingFor(track) {
    var link = document.querySelector('link[rel="alternate"][data-track="' + track + '"]');
    return link ? link.getAttribute("href") : null;
  }

  function choose(track) {
    remember(track);
    var href = track === "both" ? null : siblingFor(track);
    if (href) {
      window.location.href = href;
      return;
    }
    apply(track);
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-set-track]");
    if (!btn) return;
    ev.preventDefault();
    choose(btn.getAttribute("data-set-track"));
  });

  apply(stored() || "both");
})();
