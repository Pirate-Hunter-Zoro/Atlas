/* ==========================================================================
   who.js -- WHICH ASSISTANT, and the rules both surfaces draw it by.

   The board picks one for a SITTING; the front door picks the one this MACHINE
   falls back to. Two different answers to one question, and the question is the
   same shape on both: which recipes can this machine actually run, which of
   them can be tapped, and what does a dimmed one say about itself.

   ONE COPY, because the alternative was measured in the registry comment in
   `bin/tutor`: two lists go out of step the first time a recipe grows a flag,
   and a flag on a recipe is exactly how a provider is added. `unkeyed` was the
   third such flag and it arrived after both surfaces existed.

   What a recipe says about itself, and none of it is decided here:

     missing    the executable is not on the path -- not offered at all
     unkeyed    the key it names is not in the key file -- offered, dimmed,
                and the title says which line to put where. A provider is a
                recipe plus a key, so this is the whole of its setup
                instructions and they belong on the glass
     exclusive  one sitting at a time, machine-wide, in the recipe's own words
     private    the fenced reader. Never a machine default, because its cards
                must not be pushed
   ========================================================================== */

(function () {
  "use strict";

  /* Every recipe this machine could run: installed, and able to take a turn
     without a terminal. An unkeyed one IS here -- dimmed rather than hidden,
     because "deepseek is one line in a file away" is worth saying and a name
     that silently is not there says nothing at all. */
  function offerable(assistants) {
    return ((assistants && assistants.agents) || []).filter(function (a) {
      return a.headless && !a.missing;
    });
  }

  /* And the ones a tap can actually land on. */
  function choosable(assistants) {
    return offerable(assistants).filter(function (a) { return !a.unkeyed; });
  }

  /* Why this one cannot be tapped, in words a person can act on, or "". */
  function blocked(a) {
    if (!a || !a.unkeyed) return "";
    return "needs " + a.unkeyed + " in " + (a.keys || "the key file")
         + " — one " + a.unkeyed + "=… line and it is here";
  }

  /* What the button says about itself when it is held. */
  function title(a) {
    return blocked(a)
        || (a.exclusive ? "one sitting at a time — " + a.exclusive : a.cmd);
  }

  /* Draw the buttons into `host`. `opts.dim(a)` is the surface's own extra
     reason to grey one out -- the local model with no server, on the board --
     and `opts.pick(a)` is what a tap does. A blocked one is drawn and does
     nothing, which is the point of drawing it. */
  function draw(host, agents, now, opts) {
    opts = opts || {};
    host.innerHTML = "";
    agents.forEach(function (a) {
      var b = host.ownerDocument.createElement("button");
      b.type = "button";
      b.textContent = a.name;
      b.title = title(a);
      if (a.name === now) b.className = "on" + (a.exclusive ? " local" : "");
      if (a.unkeyed || (opts.dim && opts.dim(a))) b.classList.add("away");
      b.onclick = function () {
        if (a.unkeyed) {
          if (opts.say) opts.say(blocked(a));
          return;
        }
        if (opts.pick) opts.pick(a);
      };
      host.appendChild(b);
    });
  }

  window.WhoChoice = { offerable: offerable, choosable: choosable,
                       blocked: blocked, title: title, draw: draw };
}());
