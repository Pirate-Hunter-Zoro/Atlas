/* ==========================================================================
   mission.js -- WHAT A RUNNING MISSION HAS BEEN DOING.

   The ask, in the owner's words:

     "Whenever an agent is dispatched in some way, make it so that if I click on
      that box that says 'A Mission is still going' I can see what has been
      going on and been accomplished thus far. Be it colibri, or anything."

   The row said three words -- still going, done, failed -- and after the first
   hour that is a state nobody can act on. One mission had run five hours, taken
   a pick-up, and put nothing anywhere: no card, no file, no progress, because a
   turn's output lands at the END and this model prefills for hours.

   TWO HALVES, AND THE FIRST ONE IS TRUE OF A MISSION THAT HAS SAID NOTHING.
   Elapsed, which turn it is on, whether a client is running right now, which
   node, how long that node's allocation has left, how much of the eighteen
   hours is spent -- all of it is in the record. Cards, commits and dirty files
   are derived from the workspace. That half is drawn first, and where the
   assistant has reported nothing the panel SAYS SO rather than looking broken.

   ONE RENDERER FOR BOTH SURFACES. The front door and the board's own strip both
   carry the row, so they both carry this; a second copy is a second thing to
   keep true. `/mission` is a TAP rather than a poll -- two `git` calls -- so
   nothing here is on the four-times-a-second payload.
   ========================================================================== */

(function () {
  "use strict";

  /* Coarse on purpose. A mission is measured in hours, and "5h 29m" is the
     whole of what somebody wants; seconds on a five-hour job is noise. */
  function span(s) {
    s = Math.max(0, Math.round(s || 0));
    if (s < 60) return s + "s";
    var m = Math.round(s / 60);
    if (m < 60) return m + "m";
    var h = Math.floor(m / 60);
    return h + "h" + (m % 60 ? " " + (m % 60) + "m" : "");
  }

  function clock(at) {
    try {
      return new Date((at || 0) * 1000).toLocaleTimeString(
        [], { hour: "2-digit", minute: "2-digit" });
    } catch (e) { return ""; }
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  /* The derivable half, as one line of facts. Each clause is there only when it
     is true: a mission with no ceiling has no allocation to run out, and saying
     "0m left" about one is furniture that lies. */
  function facts(m) {
    var said = [];
    if (m.elapsed) said.push(span(m.elapsed) + " in");
    said.push(m.turns > 1 ? "turn " + m.turns + " of it" : "its first turn");
    if (m.carries) {
      said.push(m.carries === 1 ? "picked up once after the node went away"
                                : "picked up " + m.carries + " times");
    }
    if (m.stalls) {
      said.push(m.stalls + " pick-up" + (m.stalls === 1 ? "" : "s")
                + " produced nothing");
    }
    said.push(m.working ? "a turn is running right now"
                        : "nothing is mid-turn");
    if (m.host) said.push("on " + m.host);
    if (m.left) said.push(span(m.left) + " left on that allocation");
    if (m.budget) said.push(span(m.budget) + " of budget left");
    return said.join(" · ");
  }

  /* What it has MADE, which is the half of "accomplished" that no prompt can
     lie about. Counts first: "2 cards, 1 commit, 3 files" is the answer, and
     the names under it are for going and looking. */
  function made(m) {
    var said = [];
    if (m.card_count) {
      said.push(m.card_count + " card" + (m.card_count === 1 ? "" : "s"));
    }
    if (m.commits && m.commits.length) {
      said.push(m.commits.length + " commit"
                + (m.commits.length === 1 ? "" : "s"));
    }
    if (m.dirty) {
      said.push(m.dirty + " file" + (m.dirty === 1 ? "" : "s")
                + " changed and not committed");
    }
    /* A NAME UNDER A FENCE IS COUNTED AND NOT NAMED. In the one workspace that
       has a fence the filenames themselves carry participant ids, so the count
       is the honest answer -- and it is said out loud, because a name silently
       missing from a list is one somebody scrolls looking for. */
    if (m.withheld) {
      said.push(m.withheld + " more under " + ((m.fenced || []).join("/") || "a fence")
                + ", not named here");
    }
    return said.join(" · ");
  }

  /* THE HOST IS KEYED BY WHAT WAS ASKED FOR, NOT BY WHAT CAME BACK, so nothing
     here writes `dataset.mission`: `show` set it, `show` compares against it to
     drop a stale answer, and the caller's toggle reads it. A redraw re-keying
     it off the payload is how a second tap re-opens the panel it should close. */
  function draw(host, m) {
    host.textContent = "";
    host.hidden = false;

    var head = el("div", "mprog-head");
    head.appendChild(el("span", "mprog-who",
      (m.agent || "an assistant") + " in " + (m.course || m.repo || m.ws || "")));
    var shut = el("button", "quiet mprog-close", "✕");
    shut.type = "button";
    shut.title = "close";
    shut.onclick = function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      hide(host);
    };
    head.appendChild(shut);
    host.appendChild(head);

    host.appendChild(el("p", "mprog-facts", facts(m)));
    if (m.task) host.appendChild(el("p", "mprog-task", m.task));

    /* THE TRAIL. The board's own lines -- dispatched, a turn started, picked up
       -- are marked as the board's, because "picked up after the node went
       away" is the machinery working and must not read as the assistant's
       report. */
    if (m.steps && m.steps.length) {
      var list = el("ol", "mprog-steps");
      m.steps.forEach(function (s) {
        var row = el("li", "mprog-step" + (s.who === "board" ? " machine" : ""));
        row.appendChild(el("span", "mprog-when", clock(s.at)));
        row.appendChild(el("span", "mprog-said", s.said));
        list.appendChild(row);
      });
      host.appendChild(list);
    } else {
      /* NOT A BLANK. A mission that has reported nothing is the case this whole
         panel exists for, so the panel says which of two it is: still in its
         first prefill, or running and quiet. */
      host.appendChild(el("p", "mprog-quiet",
        m.state === "running"
          ? ("Nothing reported yet. On the local model the first answer of a "
             + "turn is hours of prefill; the facts above are the machine's, "
             + "not its word.")
          : "It reported nothing before it stopped."));
    }

    var count = made(m);
    if (count) host.appendChild(el("p", "mprog-made", count));

    var names = el("ul", "mprog-names");
    (m.cards || []).forEach(function (c) {
      names.appendChild(el("li", "mprog-card",
        "card " + c.id + (c.title ? " — " + c.title : "")));
    });
    (m.commits || []).forEach(function (c) {
      names.appendChild(el("li", "mprog-commit", c.subject));
    });
    (m.files || []).forEach(function (f) {
      names.appendChild(el("li", "mprog-file", f));
    });
    if (names.childNodes.length) host.appendChild(names);

    if (m.state === "failed" && m.reason) {
      host.appendChild(el("p", "mprog-why", m.reason));
    }
    if (m.ship) {
      host.appendChild(el("p", "mprog-ship", m.shipped
        ? "The diff has been handed to a tutor to push."
        : "It was told to ship itself when it finishes."));
    }
  }

  function hide(host) {
    if (!host) return;
    host.hidden = true;
    host.textContent = "";
    host.dataset.mission = "";
  }

  /* Which mission this host is showing, or "". The caller's toggle is built out
     of this rather than out of a flag it has to keep in step. */
  function shown(host) {
    return (host && !host.hidden && host.dataset.mission) || "";
  }

  function show(host, m) {
    if (!host || !m || !m.ws || !m.id) return;
    host.hidden = false;
    host.dataset.mission = m.id;
    host.textContent = "";
    host.appendChild(el("p", "mprog-facts", "reading what it has done…"));
    fetch("/mission?ws=" + encodeURIComponent(m.ws)
          + "&id=" + encodeURIComponent(m.id))
      .then(function (r) { return r.json(); })
      .then(function (got) {
        /* A second tap while the first was in flight wins. */
        if (host.dataset.mission !== m.id) return;
        if (!got || got.ok !== true) {
          host.textContent = "";
          host.appendChild(el("p", "mprog-quiet",
            "That mission's record could not be read from here."));
          return;
        }
        draw(host, Object.assign({}, m, got));
      })
      .catch(function () {
        if (host.dataset.mission !== m.id) return;
        host.textContent = "";
        host.appendChild(el("p", "mprog-quiet",
          "The board could not be reached. The mission is unaffected."));
      });
  }

  window.MissionPanel = { show: show, hide: hide, shown: shown };
})();
