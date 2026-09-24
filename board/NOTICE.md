# Third-party code

## KaTeX

`web/katex/` is a vendored copy of [KaTeX](https://katex.org) 0.16.11 — `katex.min.css`,
`katex.min.js`, `contrib/auto-render.min.js`, and the woff2 subset of its fonts. It is included
rather than loaded from a CDN so the board works without internet access and so the installed
iPad app has something to cache.

KaTeX is MIT licensed. Its licence is at `web/katex/LICENSE` and applies to those files.

Nothing else in this repository is third-party beyond what is listed below. The server, the
command line, and the pages are Python and browser JavaScript with no dependencies: no pip, no npm
at run time, no framework, no build step. `node` is used only to run the tests.

## math.js

`web/mathjs/math.js` is the browser bundle of [math.js](https://mathjs.org) 15.2.0, unmodified,
used by the calculator (`web/calc.js`). It is Apache-2.0 licensed; its licence and notice are at
`web/mathjs/LICENSE` and `web/mathjs/NOTICE`. The bundle carries complex.js, decimal.js,
fraction.js, typed-function, seedrandom, tiny-emitter, escape-latex, javascript-natural-sort and
@babel/runtime helpers, all MIT licensed; their licences are at `web/mathjs/LICENSE-bundled`.

## OpenDyslexic

`web/fonts/opendyslexic-*.woff2` is OpenDyslexic by Abbie Gonzalez, taken from the
`@fontsource/opendyslexic` package. It is licensed under the SIL Open Font License 1.1; the licence
is at `web/fonts/LICENSE-OpenDyslexic`.

## Atkinson Hyperlegible

`web/fonts/atkinson-hyperlegible-*.woff2` is Atkinson Hyperlegible by the Braille Institute of
America, taken from the `@fontsource/atkinson-hyperlegible` package. It is licensed under the SIL
Open Font License 1.1; the licence is at `web/fonts/LICENSE-AtkinsonHyperlegible`.

## Things this expects to find, but does not ship

- **TeX** — any LaTeX installation with `latex`, `pdflatex`, and `dvisvgm`, plus the `standalone`,
  `varwidth`, `preview`, and `needspace` packages. TinyTeX is the small option.
- **Tailscale** — optional, and only to reach the board from a device on another network. The
  static binaries are downloaded from Tailscale and are not redistributed here.
