/* ==========================================================================
   inkkeep.js -- ink on a reader's pages that says it is kept.

   ONE SAVE PATH, made by the one reader (`reader.js`) for every page that
   reads a PDF. Two copies are how one of them ends up cleaning a page on a
   500 and never trying it again.

   What it keeps:

     1. A FAILED SAVE STAYS OWED. `owed` is this page's own copy of every body
        not yet confirmed on disk, because the pen's `unsaved` list is dropped
        when a reader closes (`Annotate.forget`). A failed page is tried again
        on a timer that backs off, when the network comes back (`online`), and
        when the page is looked at again (`visibilitychange` to visible).
     2. THE LID SHUTTING. `visibilitychange` to hidden is the event iOS fires
        then, and `pagehide` is not reliably fired in a home-screen app, so
        both flush everything owed with `fetch(..., {keepalive: true})`.
        Keepalive bodies share a 60000-byte budget per flush, because browsers
        reject keepalive requests past about 64 KB; a heavier page goes as an
        ordinary request, which still finishes while the page is only hidden.
     3. ONE SAVE OF A KEY IN THE AIR AT A TIME. Two can land in either order,
        and the older landing last leaves disk behind the glass while both said
        yes. A save waits on the ones already in flight, so a caller that needs
        the ink on disk is not answered before it lands.
     4. ONLY WHAT WENT IS CLEAN. A stroke drawn while the save was in the air
        is still owed.
     5. INK KNOWS ITS BUILD. The reader says which build is on the glass for a
        key (`opts.build`), and it rides on every save of freshly drawn ink,
        with anything else the reader stamps on it (`opts.stamp`).
     6. INK FOR A PAGE THAT IS GONE IS LET GO. A save the board answers with
        `gone` was drawn on something that is no longer there, and retrying it
        forever would write it onto whatever replaced it.

   `send` is NEVER set from here. Each reader decides what its ink becomes,
   and neither makes a turn per ring drawn.

   `InkKeep.make(opts)` takes:
     build(id)   the `{digest, at, pages}` the key was drawn on, or null
     stamp(id)   more fields for a fresh body of the key, or null
     paint()     repaint whatever says where the ink is
     saved(done) after a round, `done` = [{id, ok, gone}]
     url         where a body is POSTed (default `/annotate/save`): the
                 reader's session or subject route
   and answers `{save, queue, flush, settle, owed, failed}`. `InkKeep.words`
   is the one sentence both status lines say.
   ========================================================================== */
(function () {
"use strict";

var KEEPALIVE_BUDGET = 60000;

function words(owed, failed, marked) {
  if (owed && failed) return { text: "not saved — retrying", cls: "bad" };
  if (owed) return { text: "saving…", cls: "busy" };
  if (marked) {
    return { text: "saved · " + marked + (marked === 1 ? " page" : " pages")
             + " marked", cls: "" };
  }
  return { text: "", cls: "" };
}

function make(opts) {
  opts = opts || {};
  var A = function () { return window.Annotate; };
  var owed = Object.create(null);      /* key -> the body last sent, unconfirmed */
  var flying = Object.create(null);    /* key -> a save of it is in the air */
  var failed = false;
  var retryTimer = null;
  var retryWait = 0;
  var penTimer = null;

  function paint() { if (opts.paint) opts.paint(); }

  function bodyFor(id) {
    var dirty = A().unsaved().indexOf(id) >= 0;
    var body = dirty ? A().payload(id, false) : owed[id];
    if (!body) return null;
    /* WHICH BUILD IT WAS DRAWN ON -- only for ink drawn now: an owed body
       keeps whatever it was sent with. */
    var build = dirty && opts.build ? opts.build(id) : null;
    if (build) body.build = build;
    var more = dirty && opts.stamp ? opts.stamp(id) : null;
    if (more) Object.keys(more).forEach(function (k) { body[k] = more[k]; });
    return body;
  }

  function inkOwed() {
    if (!A()) return false;
    return A().unsaved().length > 0 || Object.keys(owed).length > 0;
  }

  function save(o) {
    if (!A()) return Promise.resolve([]);
    var keep = !!(o && o.keepalive);
    var budget = KEEPALIVE_BUDGET;
    var ids = A().unsaved().slice();
    Object.keys(owed).forEach(function (id) { if (ids.indexOf(id) < 0) ids.push(id); });
    ids = ids.filter(function (id) { return !flying[id]; });
    var pending = Object.keys(flying).map(function (id) { return flying[id]; });
    if (!ids.length && !pending.length) { paint(); return Promise.resolve([]); }
    var jobs = ids.map(function (id) {
      var body = bodyFor(id);
      if (!body) return Promise.resolve({ id: id, ok: true });
      var sentInk = JSON.stringify(body.strokes || []);
      owed[id] = body;
      var init = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body)
      };
      if (keep && init.body.length <= budget) {
        init.keepalive = true;
        budget -= init.body.length;
      }
      var job = fetch(opts.url || "/annotate/save", init).then(function (r) {
        var read = r && r.json ? r.json().catch(function () { return {}; })
                               : Promise.resolve({});
        return read.then(function (got) {
          if (got && got.gone) return got;
          if (r && r.ok === false) throw new Error("the board answered " + r.status);
          return got;
        });
      }).then(function (got) {
        if (got && got.gone) {
          /* What it was drawn on is gone: let it go, not try it again. */
          if (A().unsaved().indexOf(id) >= 0) A().clean(id);
          if (owed[id] === body) delete owed[id];
          return { id: id, ok: true, gone: true };
        }
        if (got && got.ok === false) throw new Error(got.error || "refused");
        var now = A().unsaved().indexOf(id) >= 0
          ? JSON.stringify(A().payload(id, false).strokes || [])
          : sentInk;
        if (now === sentInk) A().clean(id);
        if (owed[id] === body) delete owed[id];
        return { id: id, ok: true };
      }).catch(function () {
        return { id: id, ok: false };
      }).then(function (res) {
        if (flying[id] === job) delete flying[id];
        return res;
      });
      flying[id] = job;
      return job;
    });
    paint();
    return Promise.all(jobs.concat(pending)).then(function (done) {
      failed = done.some(function (d) { return !d.ok; });
      if (failed) {
        scheduleRetry();
      } else {
        retryWait = 0;
        if (retryTimer) { clearTimeout(retryTimer); retryTimer = null; }
        /* Drawn on while the save was in the air: that goes next. */
        if (A().unsaved().length) queue();
      }
      paint();
      if (opts.saved) opts.saved(done);
      return done;
    });
  }

  /* Backing off, and never giving up: the ink is somebody's work and the board
     being unreachable for an hour is a train through a tunnel, not a verdict. */
  function scheduleRetry() {
    if (retryTimer) return;
    var first = window.INK_RETRY_MS || 5000;
    retryWait = Math.min(retryWait ? retryWait * 2 : first, Math.max(first, 60000));
    retryTimer = setTimeout(function () {
      retryTimer = null;
      save();
    }, retryWait);
  }

  /* Saved shortly after the pen lifts, never mid-stroke: serialising a
     well-marked page is real main-thread time, and it lands by construction in
     the middle of the next stroke. */
  function queue() {
    if (penTimer) clearTimeout(penTimer);
    penTimer = setTimeout(function () {
      penTimer = null;
      /* Not under a moving nib. Deferred, not dropped. */
      if (A().busy()) { queue(); return; }
      save();
    }, 900);
  }

  /* Everything owed, now, marked to outlive the page. Not under the 900 ms
     timer: there may be no next tick. */
  function flush() {
    if (penTimer) { clearTimeout(penTimer); penTimer = null; }
    return save({ keepalive: true });
  }

  /* On disk before anything reads it back: a save already in the air is
     waited on, and a stroke drawn while it was goes in a second round. */
  function settle() {
    if (penTimer) { clearTimeout(penTimer); penTimer = null; }
    return save().then(function () {
      return inkOwed() && !failed ? save() : null;
    });
  }

  if (A()) {
    window.addEventListener("pagehide", function () { flush(); });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") { flush(); return; }
      if (inkOwed()) save();
    });
    window.addEventListener("online", function () {
      if (inkOwed()) save();
    });
  }

  return {
    save: save, queue: queue, flush: flush, settle: settle,
    owed: inkOwed,
    failed: function () { return failed; }
  };
}

window.InkKeep = { make: make, words: words };
})();
