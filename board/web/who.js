/* ==========================================================================
   who.js -- WHICH ASSISTANT, and the rules every surface draws it by.

   There is one provider setting, the MACHINE's, and every session's next turn
   goes to it (or to its fallback when it cannot). Both surfaces that draw the
   choice -- the front door's Tutor chooser and the board's tutor chip -- set
   that one setting through `POST /default-agent`, and both ask the same three
   things: which recipes can this machine actually run, which of them can be
   tapped, and what does a dimmed one say about itself. A button reads the
   recipe's `label`; what is sent is its `name`.

   ONE COPY, for the reason in the registry comment in `agents/recipes.py`:
   two lists go out of step the first time a recipe grows a flag, and a flag
   on a recipe is exactly how a provider is added.

   What a recipe says about itself, and none of it is decided here:

     missing    the executable is not on the path -- not offered at all
     unkeyed    the key it names is not in the key file -- offered, dimmed,
                and the title says which line to put where. A provider is a
                recipe plus a key, so this is the whole of its setup
                instructions and they belong on the glass
     exclusive  one sitting at a time, machine-wide, in the recipe's own words
     private    an in-fence model: only it reads phi, and it never takes a
                turn here. `unavailable` says so, and `/default-agent` refuses it
     unavailable why it could not take a turn RIGHT NOW, in the launcher's own
                sentence -- an allowance that has run out, a hostname this
                machine cannot open. Offered, dimmed, and the tap says so. It is
                the only one of these that moves while the board is up, which is
                why `assistants.TTL` is a minute
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

  /* And the ones a tap can actually land on. A provider that is merely
     unavailable is still one of them: the stand-down expires, the allowance
     comes back, and a sitting opened now is taught by whoever can take the turn
     when it arrives. What must not happen is it being drawn as though nothing
     were wrong. */
  function choosable(assistants) {
    return offerable(assistants).filter(function (a) {
      return !a.unkeyed;
    });
  }

  /* Why this one cannot be tapped, in words a person can act on, or "". */
  function blocked(a) {
    if (!a) return "";
    if (a.unkeyed) {
      return "needs " + a.unkeyed + " in " + (a.keys || "the key file")
           + " — one " + a.unkeyed + "=… line and it is here";
    }
    /* Not a setup problem and not permanent: the launcher's own sentence,
       which already names the host and the hour it will be asked again. */
    return a.unavailable || "";
  }

  /* What the button says about itself when it is held. */
  function title(a) {
    return blocked(a)
        || (a.exclusive ? "one sitting at a time — " + a.exclusive : a.cmd);
  }

  /* Draw the buttons into `host`, each reading its recipe's `label` (its
     `name` when it has none). `now` is the NAME of the lit one. `opts.dim(a)`
     is the surface's own extra reason to grey one out, and `opts.pick(a)` is
     what a tap does, given the recipe whose `name` is what the server takes.
     A blocked one is drawn and does nothing, which is the point of drawing it. */
  function draw(host, agents, now, opts) {
    opts = opts || {};
    host.innerHTML = "";
    agents.forEach(function (a) {
      var b = host.ownerDocument.createElement("button");
      b.type = "button";
      b.textContent = a.label || a.name;
      b.setAttribute("data-name", a.name);
      b.title = title(a);
      if (a.name === now) b.className = "on" + (a.exclusive ? " local" : "");
      if (a.unkeyed || a.unavailable || (opts.dim && opts.dim(a))) {
        b.classList.add("away");
      }
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
