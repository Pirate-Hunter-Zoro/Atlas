/* ==========================================================================
   calc-core.js -- the calculator's mathematics, with no page in it.

   Parsing, arithmetic, matrices, symbolic derivatives and number formatting
   are math.js (web/mathjs/, vendored, Apache-2.0). This file adds what a
   TI-84 has and math.js does not, under the TI's own names and argument
   orders: the distributions, fnInt, nDeriv, solve, sum/seq over a variable,
   nCr/nPr (also infix), DEG/RAD, log as base ten, Ans.

   It loads in a browser as `window.CalcCore` and in node through `require`,
   so test/calc.js checks the numbers without a DOM. `create(math)` wants the
   math.js module and returns an engine that never throws: every evaluation
   answers {ok, text} or {ok: false, error}.

   Accuracy targets are 1e-9 relative on reference values. The densities use
   Loader's saddle-point form (stirlerr / bd0, as R does) so a binomial with a
   large n does not lose its digits to lgamma; the tails are computed as tails,
   never as one minus the other side.
   ========================================================================== */

(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.CalcCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
"use strict";

/* ------------------------------------------------------------ special functions */

var LN_SQRT_2PI = 0.918938533204672741780329736406;
var SQRT_2PI = 2.506628274631000502415765284811;
var LANCZOS = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
               771.32342877765313, -176.61502916214059, 12.507343278686905,
               -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];

function lgamma(x) {
  if (x < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * x))) - lgamma(1 - x);
  if (x > 15) {
    // Stirling with its correction series: the absolute error is rounding only.
    var x2 = x * x;
    return (x - 0.5) * Math.log(x) - x + LN_SQRT_2PI
      + (1 / 12 - (1 / 360 - (1 / 1260 - (1 / 1680 - 1 / (1188 * x2)) / x2) / x2) / x2) / x;
  }
  x -= 1;
  var a = LANCZOS[0], t = x + 7.5;
  for (var i = 1; i < 9; i++) a += LANCZOS[i] / (x + i);
  return LN_SQRT_2PI + (x + 0.5) * Math.log(t) - t + Math.log(a);
}

/* lgamma(n+1) - ((n+1/2) ln n - n + ln sqrt(2 pi)) -- the part of Stirling a
   density must not compute by subtracting two large numbers. */
function stirlerr(n) {
  if (n <= 15) return lgamma(n + 1) - (n + 0.5) * Math.log(n) + n - LN_SQRT_2PI;
  var nn = n * n;
  return (1 / 12 - (1 / 360 - (1 / 1260 - (1 / 1680 - 1 / (1188 * nn)) / nn) / nn) / nn) / n;
}

/* x ln(x/np) + np - x, without the cancellation when x is near np. */
function bd0(x, np) {
  if (Math.abs(x - np) < 0.1 * (x + np)) {
    var v = (x - np) / (x + np), s = (x - np) * v, ej = 2 * x * v;
    v = v * v;
    for (var j = 1; j < 1000; j++) {
      ej *= v;
      var s1 = s + ej / (2 * j + 1);
      if (s1 === s) return s1;
      s = s1;
    }
    return s;
  }
  return x * Math.log(x / np) + np - x;
}

/* Binomial density for real x, n (Loader). q = 1 - p passed in, so a p near 1
   keeps its complement exact. */
function dbinomRaw(x, n, p, q) {
  if (p === 0) return x === 0 ? 1 : 0;
  if (q === 0) return x === n ? 1 : 0;
  if (x === 0) {
    if (n === 0) return 1;
    return Math.exp(p < 0.1 ? n * Math.log1p(-p) : n * Math.log(q));
  }
  if (x === n) return Math.exp(q < 0.1 ? n * Math.log1p(-q) : n * Math.log(p));
  if (x < 0 || x > n) return 0;
  var lc = stirlerr(n) - stirlerr(x) - stirlerr(n - x) - bd0(x, n * p) - bd0(n - x, n * q);
  var lf = Math.log(2 * Math.PI) + Math.log(x) + Math.log1p(-x / n);
  return Math.exp(lc - 0.5 * lf);
}

/* Poisson density for real x (Loader). */
function dpoisRaw(x, lambda) {
  if (lambda === 0) return x === 0 ? 1 : 0;
  if (x < 0) return 0;
  if (x === 0) return Math.exp(-lambda);
  if (!isFinite(lambda)) return 0;
  return Math.exp(-stirlerr(x) - bd0(x, lambda)) / Math.sqrt(2 * Math.PI * x);
}

/* e^-x x^a / Gamma(a): the front of both incomplete gamma expansions. */
function gammaFront(a, x) {
  if (x === 0) return 0;
  if (a < 1) return Math.exp(-x + a * Math.log(x) - lgamma(a));
  return a * dpoisRaw(a, x);
}

var TINY = 1e-300, EPS = 1e-16;

/* Regularized incomplete gamma, as {p, q}: whichever side is small is
   computed directly, so both tails are accurate. */
function incGamma(a, x) {
  if (x <= 0) return { p: 0, q: 1 };
  if (x === Infinity) return { p: 1, q: 0 };
  var front = gammaFront(a, x), v;
  if (x < a + 1) {
    var ap = a, sum = 1 / a, del = sum;
    for (var n = 0; n < 100000; n++) {
      ap += 1; del *= x / ap; sum += del;
      if (Math.abs(del) < Math.abs(sum) * EPS) break;
    }
    v = sum * front;
    return { p: v, q: 1 - v };
  }
  var b = x + 1 - a, c = 1 / TINY, d = 1 / b, h = d;
  for (var i = 1; i < 100000; i++) {
    var an = -i * (i - a);
    b += 2;
    d = an * d + b; if (Math.abs(d) < TINY) d = TINY;
    c = b + an / c; if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d;
    var dl = d * c;
    h *= dl;
    if (Math.abs(dl - 1) < EPS) break;
  }
  v = front * h;
  return { p: 1 - v, q: v };
}

function betacf(x, a, b) {
  var qab = a + b, qap = a + 1, qam = a - 1;
  var c = 1, d = 1 - qab * x / qap;
  if (Math.abs(d) < TINY) d = TINY;
  d = 1 / d;
  var h = d;
  for (var m = 1; m < 100000; m++) {
    var m2 = 2 * m;
    var aa = m * (b - m) * x / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < TINY) d = TINY;
    c = 1 + aa / c; if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d; h *= d * c;
    aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < TINY) d = TINY;
    c = 1 + aa / c; if (Math.abs(c) < TINY) c = TINY;
    d = 1 / d;
    var del = d * c;
    h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

/* Regularized incomplete beta I_x(a, b) and its complement, as {p, q}. y is
   1 - x, passed separately so a caller that knows it exactly keeps it exact. */
function incBeta(x, y, a, b) {
  if (x <= 0) return { p: 0, q: 1 };
  if (y <= 0) return { p: 1, q: 0 };
  // x^a y^b / B(a, b) is a binomial density in disguise; Loader's form keeps
  // its digits when a or b is in the millions, where three lgammas cancel.
  var front = dbinomRaw(a, a + b, x, y) * a * b / (a + b);
  var v;
  if (x < (a + 1) / (a + b + 2)) {
    v = front * betacf(x, a, b) / a;
    return { p: v, q: 1 - v };
  }
  v = front * betacf(y, b, a) / b;
  return { p: 1 - v, q: v };
}

function erfc(x) {
  if (x < 0) return 2 - erfc(-x);
  if (x > 40) return 0;
  return incGamma(0.5, x * x).q;
}

function erf(x) {
  if (x < 0) return -erf(-x);
  if (x > 10) return 1;
  return incGamma(0.5, x * x).p;
}

/* ---------------------------------------------------------------- normal */

function phi(z) {                     // lower tail
  if (z === -Infinity) return 0;
  if (z === Infinity) return 1;
  return z < 0 ? 0.5 * erfc(-z / Math.SQRT2) : 1 - 0.5 * erfc(z / Math.SQRT2);
}
function phiUpper(z) { return phi(-z); }

/* P(lo < X < hi) from a lower and an upper tail function, choosing the pair
   that never subtracts two numbers near one. */
function between(lo, hi, lower, upper, centre) {
  if (lo > hi) return -between(hi, lo, lower, upper, centre);
  if (lo >= centre) return upper(lo) - upper(hi);
  if (hi <= centre) return lower(hi) - lower(lo);
  return 1 - lower(lo) - upper(hi);
}

var ACK_A = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
var ACK_B = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01];
var ACK_C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
var ACK_D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00];

/* Standard normal quantile: Acklam's rational approximation, then Halley
   steps against the tail-accurate CDF, which takes it to machine precision. */
function normInv(p) {
  if (p > 0.5) return -normInv(1 - p);
  if (p === 0.5) return 0;
  var x, q, r;
  if (p < 0.02425) {
    q = Math.sqrt(-2 * Math.log(p));
    x = (((((ACK_C[0] * q + ACK_C[1]) * q + ACK_C[2]) * q + ACK_C[3]) * q + ACK_C[4]) * q + ACK_C[5])
      / ((((ACK_D[0] * q + ACK_D[1]) * q + ACK_D[2]) * q + ACK_D[3]) * q + 1);
  } else {
    q = p - 0.5; r = q * q;
    x = (((((ACK_A[0] * r + ACK_A[1]) * r + ACK_A[2]) * r + ACK_A[3]) * r + ACK_A[4]) * r + ACK_A[5]) * q
      / (((((ACK_B[0] * r + ACK_B[1]) * r + ACK_B[2]) * r + ACK_B[3]) * r + ACK_B[4]) * r + 1);
  }
  for (var k = 0; k < 3; k++) {
    var e = phi(x) - p;
    var u = e * SQRT_2PI * Math.exp(x * x / 2);
    var nx = x - u / (1 + x * u / 2);
    if (!isFinite(nx)) break;
    if (nx === x) break;
    x = nx;
  }
  return x;
}

/* ---------------------------------------------------------------- t */

/* Past df = 1e7 the incomplete beta loses digits to x = df/(df + t^2) being
   within rounding of 1; the t is then the normal plus its first two Edgeworth
   terms (Fisher 1925), whose remainder is O(t^11 / df^3). */
function tUpperLarge(t, df) {
  if (t > 40) return 0;                // below the smallest double either way
  var t2 = t * t, t3 = t2 * t, t5 = t3 * t2, t7 = t5 * t2;
  var d = Math.exp(-t2 / 2) / SQRT_2PI;
  return phiUpper(t) + d * ((t3 + t) / (4 * df) + (3 * t7 - 7 * t5 - 5 * t3 - 3 * t) / (96 * df * df));
}

function tUpper(t, df) {               // P(T > t), t >= 0
  if (t === Infinity) return 0;
  if (df > 1e7) return tUpperLarge(t, df);
  var t2 = t * t;
  if (!isFinite(t2)) return 0;
  var r = incBeta(df / (df + t2), t2 / (df + t2), df / 2, 0.5);
  return 0.5 * r.p;
}
function tLower(t, df) { return t >= 0 ? 1 - tUpper(t, df) : tUpper(-t, df); }
function tUpperAny(t, df) { return t >= 0 ? tUpper(t, df) : 1 - tUpper(-t, df); }

/* ln Gamma(n + 1/2) - ln Gamma(n), accurate for large n where two lgammas
   would cancel. */
function lgammaHalfRatio(n) {
  if (n < 1000) return lgamma(n + 0.5) - lgamma(n);
  var s = 1 - 1 / (8 * n) + 1 / (128 * n * n) + 5 / (1024 * n * n * n)
        - 21 / (32768 * n * n * n * n);
  return 0.5 * Math.log(n) + Math.log(s);
}

function tpdfStd(x, df) {
  if (df > 1e12) return Math.exp(-x * x / 2) / SQRT_2PI;
  return Math.exp(lgammaHalfRatio(df / 2) - 0.5 * Math.log(df * Math.PI)
                  - (df + 1) / 2 * Math.log1p(x * x / df));
}

/* Quantile by safeguarded Newton inside a bracket, on whichever tail is small. */
function tInv(p, df) {
  if (p === 0.5) return 0;
  if (p > 0.5) return -tInv(1 - p, df);
  if (df > 1e7) {                        // Cornish-Fisher, the quantile of the above
    var z = normInv(p), z3 = z * z * z;
    return z + (z3 + z) / (4 * df) + (5 * z3 * z * z + 16 * z3 + 3 * z) / (96 * df * df);
  }
  // lower tail p on t < 0: solve tUpper(u) = p for u > 0, answer -u
  var lo = 0, hi = Math.max(1, -normInv(p));
  var guard = 0;
  while (tUpper(hi, df) > p && guard++ < 2000) { lo = hi; hi *= 2; }
  var u = (lo + hi) / 2;
  for (var i = 0; i < 300; i++) {
    var f = tUpper(u, df) - p;           // decreasing in u
    if (f > 0) lo = u; else hi = u;
    var d = -tpdfStd(u, df);
    var nu = u - f / d;
    if (!(nu > lo && nu < hi) || !isFinite(nu)) nu = (lo + hi) / 2;
    if (Math.abs(nu - u) <= 1e-15 * Math.max(1, Math.abs(u))) { u = nu; break; }
    u = nu;
  }
  return -u;
}

/* ---------------------------------------------------------------- gamma family */

/* Density of Gamma(shape a, scale 1) at x. */
function dgammaStd(x, a) {
  if (x < 0) return 0;
  if (x === 0) {
    if (a < 1) return Infinity;
    return a === 1 ? 1 : 0;
  }
  if (a < 1) return dpoisRaw(a, x) * a / x;
  return dpoisRaw(a - 1, x);
}

function dF(x, m, n) {
  if (x < 0) return 0;
  if (x === 0) return m > 2 ? 0 : (m === 2 ? 1 : Infinity);
  var f = 1 / (n + x * m), q = n * f, p = x * m * f, dens;
  if (m >= 2) {
    f = m * q / 2;
    dens = dbinomRaw((m - 2) / 2, (m + n - 2) / 2, p, q);
  } else {
    f = m * m * q / (2 * p * (m + n));
    dens = dbinomRaw(m / 2, (m + n) / 2, p, q);
  }
  return f * dens;
}

/* ------------------------------------------------------------ argument checks */

function num(v, what) {
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (v && typeof v.toNumber === "function" && !v.isUnit) return v.toNumber();
  if (v && v.isFraction) return Number(v.valueOf());
  if (v && v.isComplex) {
    if (Math.abs(v.im) <= 1e-14 * Math.max(1, Math.abs(v.re))) return v.re;
    throw new Error(what + " must be a real number");
  }
  throw new Error(what + " must be a number");
}

function posNum(v, what) {
  var x = num(v, what);
  if (!(x > 0)) throw new Error(what + " must be positive");
  return x;
}

function wholeNum(v, what) {
  var x = num(v, what);
  if (!(x >= 0) || Math.floor(x) !== x) throw new Error(what + " must be a whole number");
  return x;
}

function prob(v, what) {
  var x = num(v, what);
  if (!(x >= 0 && x <= 1)) throw new Error(what + " must be between 0 and 1");
  return x;
}

function openProb(v, what) {
  var x = num(v, what);
  if (!(x > 0 && x < 1)) throw new Error(what + " must be strictly between 0 and 1");
  return x;
}

/* A TI list goes in, a list comes out: the x of a density may be a list. */
function over(x, fn) {
  if (Array.isArray(x)) return x.map(function (v) { return over(v, fn); });
  if (x && x.isMatrix) return x.map(function (v) { return fn(v); });
  return fn(x);
}

/* ------------------------------------------------------------- distributions */

var dist = {
  normalpdf: function (x, mu, sigma) {
    var m = mu === undefined ? 0 : num(mu, "μ");
    var s = sigma === undefined ? 1 : posNum(sigma, "σ");
    return over(x, function (v) {
      var z = (num(v, "x") - m) / s;
      return Math.exp(-z * z / 2) / (s * SQRT_2PI);
    });
  },
  normalcdf: function (lo, hi, mu, sigma) {
    if (hi === undefined) throw new Error("normalcdf needs a lower and an upper bound");
    var m = mu === undefined ? 0 : num(mu, "μ");
    var s = sigma === undefined ? 1 : posNum(sigma, "σ");
    return between((num(lo, "lower") - m) / s, (num(hi, "upper") - m) / s,
                   phi, phiUpper, 0);
  },
  invNorm: function (area, mu, sigma) {
    var m = mu === undefined ? 0 : num(mu, "μ");
    var s = sigma === undefined ? 1 : posNum(sigma, "σ");
    return m + s * normInv(openProb(area, "area"));
  },
  tpdf: function (x, df) {
    var d = posNum(df, "df");
    return over(x, function (v) { return tpdfStd(num(v, "x"), d); });
  },
  tcdf: function (lo, hi, df) {
    if (df === undefined) throw new Error("tcdf needs lower, upper and df");
    var d = posNum(df, "df");
    return between(num(lo, "lower"), num(hi, "upper"),
                   function (t) { return tLower(t, d); },
                   function (t) { return tUpperAny(t, d); }, 0);
  },
  invT: function (area, df) {
    if (df === undefined) throw new Error("invT needs an area and df");
    return tInv(openProb(area, "area"), posNum(df, "df"));
  },
  chi2pdf: function (x, df) {
    var k = posNum(df, "df");
    return over(x, function (v) { return 0.5 * dgammaStd(num(v, "x") / 2, k / 2); });
  },
  chi2cdf: function (lo, hi, df) {
    if (df === undefined) throw new Error("chi2cdf needs lower, upper and df");
    var k = posNum(df, "df");
    return between(Math.max(0, num(lo, "lower")), Math.max(0, num(hi, "upper")),
                   function (x) { return incGamma(k / 2, x / 2).p; },
                   function (x) { return incGamma(k / 2, x / 2).q; }, k);
  },
  Fpdf: function (x, d1, d2) {
    var m = posNum(d1, "numerator df"), n = posNum(d2, "denominator df");
    return over(x, function (v) { return dF(num(v, "x"), m, n); });
  },
  Fcdf: function (lo, hi, d1, d2) {
    if (d2 === undefined) throw new Error("Fcdf needs lower, upper, numerator df and denominator df");
    var m = posNum(d1, "numerator df"), n = posNum(d2, "denominator df");
    function pair(x) {
      if (x <= 0) return { p: 0, q: 1 };
      if (x === Infinity) return { p: 1, q: 0 };
      var mx = m * x;
      return incBeta(mx / (mx + n), n / (mx + n), m / 2, n / 2);
    }
    return between(Math.max(0, num(lo, "lower")), Math.max(0, num(hi, "upper")),
                   function (x) { return pair(x).p; },
                   function (x) { return pair(x).q; }, 1);
  },
  binompdf: function (n, p, x) {
    var N = wholeNum(n, "n"), P = prob(p, "p");
    var one = function (v) {
      var k = num(v, "x");
      if (k < 0 || k > N || Math.floor(k) !== k) return 0;
      return dbinomRaw(k, N, P, 1 - P);
    };
    if (x === undefined) {
      if (N > 100000) throw new Error("binompdf without x lists n+1 values; n is too large");
      var all = [];
      for (var i = 0; i <= N; i++) all.push(one(i));
      return all;
    }
    return over(x, one);
  },
  binomcdf: function (n, p, x) {
    var N = wholeNum(n, "n"), P = prob(p, "p");
    var one = function (v) {
      var k = Math.floor(num(v, "x"));
      if (k < 0) return 0;
      if (k >= N) return 1;
      if (N <= 5000) {
        var s = 0;
        for (var i = 0; i <= k; i++) s += dbinomRaw(i, N, P, 1 - P);
        return Math.min(1, s);
      }
      return incBeta(1 - P, P, N - k, k + 1).p;
    };
    if (x === undefined) {
      if (N > 100000) throw new Error("binomcdf without x lists n+1 values; n is too large");
      var all = [], acc = 0;
      for (var i = 0; i <= N; i++) { acc += dbinomRaw(i, N, P, 1 - P); all.push(Math.min(1, acc)); }
      return all;
    }
    return over(x, one);
  },
  poissonpdf: function (lambda, x) {
    if (x === undefined) throw new Error("poissonpdf needs λ and x");
    var L = num(lambda, "λ");
    if (!(L >= 0)) throw new Error("λ must not be negative");
    return over(x, function (v) {
      var k = num(v, "x");
      if (k < 0 || Math.floor(k) !== k) return 0;
      return dpoisRaw(k, L);
    });
  },
  poissoncdf: function (lambda, x) {
    if (x === undefined) throw new Error("poissoncdf needs λ and x");
    var L = num(lambda, "λ");
    if (!(L >= 0)) throw new Error("λ must not be negative");
    return over(x, function (v) {
      var k = Math.floor(num(v, "x"));
      if (k < 0) return 0;
      if (L === 0) return 1;
      return incGamma(k + 1, L).q;
    });
  },
  geometpdf: function (p, x) {
    if (x === undefined) throw new Error("geometpdf needs p and x");
    var P = prob(p, "p");
    if (P === 0) throw new Error("p must be positive");
    return over(x, function (v) {
      var k = num(v, "x");
      if (k < 1 || Math.floor(k) !== k) return 0;
      if (k === 1) return P;
      if (P === 1) return 0;
      return P * Math.exp((k - 1) * Math.log1p(-P));
    });
  },
  geometcdf: function (p, x) {
    if (x === undefined) throw new Error("geometcdf needs p and x");
    var P = prob(p, "p");
    if (P === 0) throw new Error("p must be positive");
    return over(x, function (v) {
      var k = Math.floor(num(v, "x"));
      if (k < 1) return 0;
      if (P === 1) return 1;
      return -Math.expm1(k * Math.log1p(-P));
    });
  },
};
dist["χ2pdf"] = dist.chi2pdf;
dist["χ2cdf"] = dist.chi2cdf;

/* ------------------------------------------------------------------- calculus */

var XGK = [0.991455371120812639206854697526329, 0.949107912342758524526189684047851,
           0.864864423359769072789712788640926, 0.741531185599394439863864773280788,
           0.586087235467691130294144845693013, 0.405845151377397166906606412076961,
           0.207784955007898467600689403773245, 0];
var WGK = [0.022935322010529224963732008058970, 0.063092092629978553290700663189204,
           0.104790010322250183839876322541518, 0.140653259715525918745189590510238,
           0.169004726639267902826583426598550, 0.190350578064785409913256402421014,
           0.204432940075298892414161999234649, 0.209482141084727828012999174891714];
var WG = [0.129484966168869693270611432679082, 0.279705391489276667901467771423780,
          0.381830050505118944950369775488975, 0.417959183673469387755102040816327];

function gk15(f, a, b) {
  var c = 0.5 * (a + b), h = 0.5 * (b - a);
  var fc = f(c);
  var k = fc * WGK[7], g = fc * WG[3];
  for (var j = 0; j < 7; j++) {
    var dx = h * XGK[j];
    var s = f(c - dx) + f(c + dx);
    k += WGK[j] * s;
    if (j % 2 === 1) g += WG[(j - 1) / 2] * s;
  }
  return { a: a, b: b, v: k * h, e: Math.abs((k - g) * h) };
}

/* Globally adaptive Gauss-Kronrod 7/15. Infinite ends are mapped onto a
   finite interval first. */
var HUGE = 1e15;

/* A bound of 1e99 is how a TI user writes infinity; quadrature over
   [0, 1e99] as a finite interval samples nothing but the far tail and returns
   about 0. So a bound past 1e15 is taken as infinite, and only if that does
   not converge (x over [0, 1e20]) is it integrated as the number it is. */
function integrate(f, a, b) {
  if (isNaN(a) || isNaN(b)) throw new Error("fnInt: a bound is not a number");
  if (a === b) return 0;
  if (a > b) return -integrate(f, b, a);
  var A = a <= -HUGE ? -Infinity : a, B = b >= HUGE ? Infinity : b;
  if (A === a && B === b) return integrateOn(f, a, b);
  try { return integrateOn(f, A, B); }
  catch (e) {
    if (!isFinite(a) || !isFinite(b)) throw e;
    return integrateOn(f, a, b);
  }
}

function integrateOn(f, a, b) {
  var g = f, lo = a, hi = b;
  if (a === -Infinity && b === Infinity) {
    g = function (t) { var d = 1 - t * t; return f(t / d) * (1 + t * t) / (d * d); };
    lo = -1; hi = 1;
  } else if (b === Infinity) {
    g = function (t) { var d = 1 - t; return f(a + t / d) / (d * d); };
    lo = 0; hi = 1;
  } else if (a === -Infinity) {
    g = function (t) { var d = 1 - t; return f(b - t / d) / (d * d); };
    lo = 0; hi = 1;
  }
  var parts = [gk15(g, lo, hi)];
  var total = parts[0].v, err = parts[0].e;
  for (var it = 0; it < 3000; it++) {
    if (err <= Math.max(1e-14, 1e-12 * Math.abs(total))) break;
    var w = 0;
    for (var i = 1; i < parts.length; i++) if (parts[i].e > parts[w].e) w = i;
    var p = parts[w], m = 0.5 * (p.a + p.b);
    if (m <= p.a || m >= p.b) break;             // no room left to split
    var l = gk15(g, p.a, m), r = gk15(g, m, p.b);
    parts[w] = l; parts.push(r);
    total = 0; err = 0;
    for (var j = 0; j < parts.length; j++) { total += parts[j].v; err += parts[j].e; }
  }
  if (!isFinite(total)) throw new Error("fnInt: the integral does not converge");
  if (err > 1e-6 * Math.max(1, Math.abs(total))) {
    throw new Error("fnInt: tolerance not met (the integral may diverge)");
  }
  return total;
}

/* Ridders' extrapolated central difference: ~1e-12 on smooth functions. */
function derivativeAt(f, x) {
  var CON = 1.4, CON2 = CON * CON, NTAB = 12, SAFE = 2;
  var hh = 0.1 * Math.max(1, Math.abs(x));
  // Near the edge of a domain (ln at 0.05) the first step would leave it:
  // shrink the step until both sides evaluate, then build the tableau.
  var both = function (h) {
    try { return isFinite(f(x + h)) && isFinite(f(x - h)); } catch (e) { return false; }
  };
  var shrunk = false;
  for (var s = 0; s < 40 && !both(hh); s++) { hh /= 2; shrunk = true; }
  // A step that only just fits is still too near the edge to extrapolate from.
  if (shrunk) hh /= 4;
  var a = [], err = Infinity, ans = NaN;
  for (var r = 0; r < NTAB; r++) a.push(new Array(NTAB));
  a[0][0] = (f(x + hh) - f(x - hh)) / (2 * hh);
  ans = a[0][0];
  for (var i = 1; i < NTAB; i++) {
    hh /= CON;
    a[0][i] = (f(x + hh) - f(x - hh)) / (2 * hh);
    var fac = CON2;
    for (var j = 1; j <= i; j++) {
      a[j][i] = (a[j - 1][i] * fac - a[j - 1][i - 1]) / (fac - 1);
      fac *= CON2;
      var errt = Math.max(Math.abs(a[j][i] - a[j - 1][i]), Math.abs(a[j][i] - a[j - 1][i - 1]));
      if (errt <= err) { err = errt; ans = a[j][i]; }
    }
    if (Math.abs(a[i][i] - a[i - 1][i - 1]) >= SAFE * err) break;
  }
  if (!isFinite(ans)) throw new Error("nDeriv: the function is not differentiable there");
  return ans;
}

/* Root nearest the guess: walk outward in both directions for a sign change,
   then bisect/secant to machine precision; fall back to Newton for a root the
   function only touches (x^2 at 0). A sign change through a pole (tan at
   pi/2, 1/x at 0) is not a root: |f| grows as the bracket closes on it, so it
   is passed over and the walk goes on. */
function findRoot(f, guess, lower, upper) {
  var lo = lower === undefined ? -Infinity : lower;
  var hi = upper === undefined ? Infinity : upper;
  var g = Math.min(hi, Math.max(lo, guess));
  var fg = f(g);
  if (fg === 0) return g;

  function refine(a, b, fa, fb) {
    if (fa === 0) return a;
    if (fb === 0) return b;
    var start = Math.min(Math.abs(fa), Math.abs(fb));
    for (var k = 0; k < 400; k++) {
      var m = (fa * b - fb * a) / (fa - fb);     // secant
      if (!(m > Math.min(a, b) && m < Math.max(a, b)) || k % 3 === 2) m = 0.5 * (a + b);
      var fm = f(m);
      if (fm === 0) return m;
      if (!isFinite(fm)) return null;
      if (fm * fa < 0) { b = m; fb = fm; } else { a = m; fa = fm; }
      if (Math.abs(b - a) <= 4e-16 * Math.max(1, Math.abs(m))) break;
    }
    var r = Math.abs(fa) < Math.abs(fb) ? a : b;
    return Math.min(Math.abs(fa), Math.abs(fb)) <= start ? r : null;
  }

  var step = 0.01 * Math.max(1, Math.abs(g));
  var left = g, right = g, fl = fg, fr = fg, root;
  for (var i = 0; i < 400; i++) {
    var found = [];
    var nr = Math.min(hi, right + step);
    if (nr > right) {
      var fnr = f(nr);
      if (isFinite(fnr) && isFinite(fr) && fnr * fr <= 0
          && (root = refine(right, nr, fr, fnr)) !== null) found.push(root);
      right = nr; fr = fnr;
    }
    var nl = Math.max(lo, left - step);
    if (nl < left) {
      var fnl = f(nl);
      if (isFinite(fnl) && isFinite(fl) && fnl * fl <= 0
          && (root = refine(nl, left, fnl, fl)) !== null) found.push(root);
      left = nl; fl = fnl;
    }
    if (found.length === 1) return found[0];
    if (found.length === 2) {
      return Math.abs(found[0] - g) <= Math.abs(found[1] - g) ? found[0] : found[1];
    }
    step *= 1.3;
    if (right >= hi && left <= lo) break;
  }
  // No sign change: a root the function only touches. Newton, accepted only
  // if it converges, so 1/x walking off to infinity is not called a root.
  var x = g, converged = false;
  for (var n = 0; n < 200; n++) {
    var fx = f(x);
    if (fx === 0) return x;
    var d;
    try { d = derivativeAt(f, x); } catch (e) { break; }
    if (d === 0 || !isFinite(d)) break;
    var nx = x - fx / d;
    if (!isFinite(nx) || nx < lo || nx > hi) break;
    if (Math.abs(nx - x) <= 1e-15 * Math.max(1, Math.abs(x))) { x = nx; converged = true; break; }
    x = nx;
  }
  if (converged && Math.abs(f(x)) <= 1e-10 * Math.max(1, Math.abs(fg))) return x;
  throw new Error("solve: no root found near the guess");
}

/* Best rational approximation with a denominator of at most maxDen, or null
   when nothing that small is within tol. */
function rational(v, maxDen, tol) {
  if (!isFinite(v) || Math.floor(v) === v) return null;
  var sign = v < 0 ? -1 : 1, x = Math.abs(v);
  var h0 = 1, h1 = 0, k0 = 0, k1 = 1, r = x;
  for (var i = 0; i < 40; i++) {
    var a = Math.floor(r);
    var h2 = a * h0 + h1, k2 = a * k0 + k1;
    if (k2 > maxDen) break;
    h1 = h0; h0 = h2; k1 = k0; k0 = k2;
    if (Math.abs(x - h0 / k0) <= tol * Math.max(1, x)) return k0 === 1 ? null : [sign * h0, k0];
    r = 1 / (r - a);
    if (!isFinite(r)) break;
  }
  return null;
}

/* ------------------------------------------------------------ text rewriting */

var OPERAND = /[A-Za-z0-9_.!]/;

function matchBack(s, close) {              // index of the "(" that closes at `close`
  var depth = 0;
  for (var i = close; i >= 0; i--) {
    if (s[i] === ")" || s[i] === "]") depth++;
    else if (s[i] === "(" || s[i] === "[") { depth--; if (!depth) return i; }
  }
  return -1;
}
function matchFwd(s, open) {
  var depth = 0;
  for (var i = open; i < s.length; i++) {
    if (s[i] === "(" || s[i] === "[") depth++;
    else if (s[i] === ")" || s[i] === "]") { depth--; if (!depth) return i; }
  }
  return -1;
}

/* "10 nCr 3" -> "nCr(10, 3)". The operand on each side is the tightest thing
   touching the keyword: a number, a name, a bracketed group, or a call. */
function infix(s) {
  for (var guard = 0; guard < 50; guard++) {
    // Infix only where something sits on its left; "nCr(10, 3)" is a call.
    var re = /\bn([CP])r\b/g, m, i, at, end;
    while ((m = re.exec(s))) {
      i = m.index - 1;
      while (i >= 0 && s[i] === " ") i--;
      if (i >= 0 && /[A-Za-z0-9_.!)\]]/.test(s[i])) break;
    }
    if (!m) return s;
    at = m.index; end = at + m[0].length;
    var lEnd = i + 1, lStart;
    if (i >= 0 && (s[i] === ")" || s[i] === "]")) {
      lStart = matchBack(s, i);
      if (lStart < 0) throw new Error("unbalanced brackets before n" + m[1] + "r");
      while (lStart > 0 && /[A-Za-z0-9_]/.test(s[lStart - 1])) lStart--;
    } else {
      lStart = i + 1;
      while (lStart > 0 && OPERAND.test(s[lStart - 1])) lStart--;
    }
    var j = end;
    while (j < s.length && s[j] === " ") j++;
    var rStart = j, rEnd;
    if (s[j] === "-" || s[j] === "+") j++;
    if (s[j] === "(" || s[j] === "[") {
      rEnd = matchFwd(s, j) + 1;
      if (rEnd <= 0) throw new Error("unbalanced brackets after n" + m[1] + "r");
    } else {
      rEnd = j;
      while (rEnd < s.length && OPERAND.test(s[rEnd])) rEnd++;
      if (s[rEnd] === "(") {
        var close = matchFwd(s, rEnd);
        if (close < 0) throw new Error("unbalanced brackets after n" + m[1] + "r");
        rEnd = close + 1;
      }
    }
    var left = s.slice(lStart, lEnd).trim(), right = s.slice(rStart, rEnd).trim();
    if (!left || !right) throw new Error("n" + m[1] + "r needs a number on each side");
    s = s.slice(0, lStart) + "n" + m[1] + "r(" + left + ", " + right + ")" + s.slice(rEnd);
  }
  return s;
}

function sqrtSign(s) {
  for (var guard = 0; guard < 50; guard++) {
    var at = s.indexOf("√");
    if (at < 0) return s;
    var j = at + 1;
    while (s[j] === " ") j++;
    if (s[j] === "(") { s = s.slice(0, at) + "sqrt" + s.slice(j); continue; }
    var e = j;
    while (e < s.length && /[A-Za-z0-9_.]/.test(s[e])) e++;
    if (e === j) throw new Error("√ needs something after it");
    s = s.slice(0, at) + "sqrt(" + s.slice(j, e) + ")" + s.slice(e);
  }
  return s;
}

/* What a person types on an iPad, into what math.js reads. */
function preprocess(src) {
  var s = String(src).trim();
  s = s.replace(/[×·∙]/g, "*").replace(/÷/g, "/").replace(/[−–]/g, "-")
       .replace(/π/g, "pi").replace(/²/g, "^2").replace(/³/g, "^3")
       .replace(/ᴇ/g, "e").replace(/∞/g, "inf").replace(/°/g, " deg")
       .replace(/Σ/g, "sum").replace(/χ²/g, "chi2").replace(/χ2/g, "chi2")
       .replace(/μ/g, "mu").replace(/σ/g, "sigma").replace(/λ/g, "lambda");
  s = sqrtSign(s);
  // TI lists {1,2,3} are math.js arrays [1,2,3].
  for (var guard = 0; guard < 50 && /\{[^{}:]*\}/.test(s); guard++) {
    s = s.replace(/\{([^{}:]*)\}/g, "[$1]");
  }
  s = infix(s);
  // A line that opens with an operator continues from the last answer.
  if (/^(\*|\/|\^|\+|mod\b(?!\s*\())/.test(s)) s = "Ans " + s;
  return s;
}

/* ------------------------------------------------------------ the engine */

var TRIG_FWD = ["sin", "cos", "tan", "sec", "csc", "cot"];
var TRIG_INV = ["asin", "acos", "atan", "asec", "acsc", "acot"];

function create(mathjs, opts) {
  if (!mathjs || typeof mathjs.create !== "function") throw new Error("math.js is not loaded");
  var M = mathjs.create(mathjs.all, { number: "number" });
  var angle = (opts && opts.angle === "deg") ? "deg" : "rad";
  var scope = new Map();
  var defs = {};                  // function name -> the line that defined it

  function real(v, what) {
    if (typeof v === "number") return v;
    return num(v, what);
  }

  /* ---- DEG/RAD, decided when the function is called, not when it is typed */
  function degTrig(name, d) {
    var r = ((d % 360) + 360) % 360;
    var s, c;
    if (r % 90 === 0) {
      var q = r / 90;
      s = [0, 1, 0, -1][q]; c = [1, 0, -1, 0][q];
    } else if (r % 30 === 0 && r % 60 !== 0 && (name === "sin" || name === "csc")) {
      s = (r === 30 || r === 150) ? 0.5 : -0.5; c = Math.cos(r * Math.PI / 180);
    } else if (r % 60 === 0 && (name === "cos" || name === "sec")) {
      c = (r === 60 || r === 300) ? 0.5 : -0.5; s = Math.sin(r * Math.PI / 180);
    } else if (r % 45 === 0 && (name === "tan" || name === "cot")) {
      var t = (r === 45 || r === 225) ? 1 : -1;
      return t;
    } else {
      s = Math.sin(r * Math.PI / 180); c = Math.cos(r * Math.PI / 180);
    }
    var v;
    switch (name) {
      case "sin": return s;
      case "cos": return c;
      case "tan": v = c === 0 ? NaN : s / c; break;
      case "sec": v = c === 0 ? NaN : 1 / c; break;
      case "csc": v = s === 0 ? NaN : 1 / s; break;
      case "cot": v = s === 0 ? NaN : c / s; break;
    }
    if (isNaN(v)) throw new Error(name + " is undefined at " + d + "°");
    return v;
  }

  function fwd(name) {
    var orig = M[name];
    var one = function (x) {
      if (x && x.isUnit) return degTrig(name, x.toNumber("deg"));
      if (typeof x === "number") {
        if (angle === "deg") return degTrig(name, x);
        var r = orig(x);
        // sin(pi) is 1.2e-16 only because pi is not exactly pi.
        if (Math.abs(x) > 1 && Math.abs(r) < 8.9e-16 * Math.abs(x)) return 0;
        return r;
      }
      if (x && (x.isMatrix || Array.isArray(x))) return M.map(x, one);
      return orig(angle === "deg" ? M.multiply(x, Math.PI / 180) : x);
    };
    return one;
  }

  /* Outside its real domain an inverse trig function is complex, and a
     complex number times 180/pi is not an angle in degrees: in DEG it is the
     TI's domain error instead. */
  var INV_DOMAIN = {
    asin: [function (x) { return Math.abs(x) <= 1; }, "-1 ≤ x ≤ 1"],
    acos: [function (x) { return Math.abs(x) <= 1; }, "-1 ≤ x ≤ 1"],
    asec: [function (x) { return Math.abs(x) >= 1; }, "|x| ≥ 1"],
    acsc: [function (x) { return Math.abs(x) >= 1; }, "|x| ≥ 1"],
  };
  function inv(name) {
    var orig = M[name];
    var one = function (x) {
      if (x && (x.isMatrix || Array.isArray(x))) return M.map(x, one);
      var dom = INV_DOMAIN[name];
      if (angle === "deg" && dom && typeof x === "number" && !dom[0](x)) {
        throw new Error(name + " is only defined for " + dom[1]);
      }
      var r = orig(x);
      return angle === "deg" ? M.multiply(r, 180 / Math.PI) : r;
    };
    return one;
  }

  /* ---- evaluating a sub-expression with one variable bound */
  function Child(parent, name, value) { this.p = parent; this.n = name; this.v = value; }
  Child.prototype.get = function (k) { return k === this.n ? this.v : this.p.get(k); };
  Child.prototype.has = function (k) { return k === this.n || this.p.has(k); };
  Child.prototype.set = function (k, v) { if (k === this.n) this.v = v; else this.p.set(k, v); return this; };
  Child.prototype["delete"] = function (k) { if (k !== this.n) return this.p["delete"](k); return false; };
  Child.prototype.keys = function () {
    var s = new Set(this.p.keys()); s.add(this.n); return s.values();
  };
  Child.prototype.clear = function () {};
  Child.prototype.forEach = function (cb) {
    var self = this;
    Array.from(this.keys()).forEach(function (k) { cb(self.get(k), k, self); });
  };
  Child.prototype.entries = function () {
    var self = this;
    return Array.from(this.keys()).map(function (k) { return [k, self.get(k)]; }).values();
  };
  Child.prototype[typeof Symbol !== "undefined" ? Symbol.iterator : "@@iterator"] = function () {
    return this.entries();
  };

  function varName(node, fn) {
    if (!node || !node.isSymbolNode) throw new Error(fn + ": the variable must be a name, like x");
    return node.name;
  }

  function realFn(node, name, sc, fn) {
    var code = node.compile();
    var child = new Child(sc, name, 0);
    return function (x) {
      child.v = x;
      var r = code.evaluate(child);
      var v;
      try { v = real(r, "the expression"); }
      catch (e) { throw new Error(fn + ": the expression is not a real number at " + name + " = " + x); }
      if (isNaN(v)) throw new Error(fn + ": the expression is undefined at " + name + " = " + x);
      return v;
    };
  }

  function evalArg(node, sc, what) { return node.compile().evaluate(sc); }

  function fnInt(args, _m, sc) {
    if (args.length === 3) args = [args[0], new M.SymbolNode("x"), args[1], args[2]];
    if (args.length !== 4) throw new Error("fnInt(expression, variable, lower, upper)");
    var v = varName(args[1], "fnInt");
    var a = real(evalArg(args[2], sc), "lower"), b = real(evalArg(args[3], sc), "upper");
    var f = realFn(args[0], v, sc, "fnInt");
    var g = function (x) {
      var y = f(x);
      if (!isFinite(y)) throw new Error("fnInt: the expression is not finite at " + v + " = " + x);
      return y;
    };
    return integrate(g, a, b);
  }
  fnInt.rawArgs = true;

  function nDeriv(args, _m, sc) {
    if (args.length === 2) args = [args[0], new M.SymbolNode("x"), args[1]];
    if (args.length !== 3 && args.length !== 4) throw new Error("nDeriv(expression, variable, value)");
    var v = varName(args[1], "nDeriv");
    var x = real(evalArg(args[2], sc), "value");
    var f = realFn(args[0], v, sc, "nDeriv");
    if (args.length === 4) {             // the TI's own symmetric difference
      var h = real(evalArg(args[3], sc), "h");
      if (!(h > 0)) throw new Error("nDeriv: h must be positive");
      return (f(x + h) - f(x - h)) / (2 * h);
    }
    return derivativeAt(f, x);
  }
  nDeriv.rawArgs = true;

  function solve(args, _m, sc) {
    if (args.length < 2 || args.length > 4) throw new Error("solve(expression, variable, guess)");
    var body = args[0];
    if (body.isOperatorNode && body.fn === "equal" && body.args.length === 2) {
      body = new M.OperatorNode("-", "subtract", [body.args[0], body.args[1]]);
    }
    var v = varName(args[1], "solve");
    var guess = args.length > 2 ? real(evalArg(args[2], sc), "guess")
                                : (sc.has(v) ? real(sc.get(v), v) : 0);
    var lo, hi;
    if (args.length === 4) {
      var bounds = evalArg(args[3], sc);
      bounds = bounds && bounds.isMatrix ? bounds.toArray() : bounds;
      if (!Array.isArray(bounds) || bounds.length !== 2) {
        throw new Error("solve: bounds are a list of two, like {0, 10}");
      }
      lo = real(bounds[0], "lower bound"); hi = real(bounds[1], "upper bound");
    }
    var f = realFn(body, v, sc, "solve");
    var safe = function (x) { try { return f(x); } catch (e) { return NaN; } };
    return findRoot(safe, guess, lo, hi);
  }
  solve.rawArgs = true;

  function iterate(args, sc, fn, each) {
    var v = varName(args[1], fn);
    var a = real(evalArg(args[2], sc), "start"), b = real(evalArg(args[3], sc), "end");
    var step = args.length > 4 ? real(evalArg(args[4], sc), "step") : 1;
    if (step === 0 || !isFinite(step)) throw new Error(fn + ": the step must be a non-zero number");
    if (!isFinite(a) || !isFinite(b)) throw new Error(fn + ": the bounds must be finite");
    var count = Math.floor((b - a) / step + 1e-9) + 1;
    if (count > 1e6) throw new Error(fn + ": more than a million terms");
    var code = args[0].compile();
    var child = new Child(sc, v, 0);
    for (var i = 0; i < count; i++) {
      child.v = a + i * step;
      each(code.evaluate(child));
    }
  }

  function sumOver(args, _m, sc) {
    var acc = 0;
    iterate(args, sc, "sum", function (r) { acc = M.add(acc, r); });
    return acc;
  }
  sumOver.rawArgs = true;

  function prodOver(args, _m, sc) {
    var acc = 1;
    iterate(args, sc, "prod", function (r) { acc = M.multiply(acc, r); });
    return acc;
  }
  prodOver.rawArgs = true;

  function seq(args, _m, sc) {
    if (args.length < 4 || args.length > 5) throw new Error("seq(expression, variable, start, end[, step])");
    var out = [];
    iterate(args, sc, "seq", function (r) {
      if (out.length >= 10000) throw new Error("seq: more than 10000 terms");
      out.push(r);
    });
    return out;
  }
  seq.rawArgs = true;

  /* The engine's own names inside an expression, back into the names a
     person and math.derivative know. */
  function toPlain(node) {
    return node.transform(function (n) {
      if (n.isFunctionNode && n.fn && n.fn.isSymbolNode && /__$/.test(n.fn.name)) {
        var base = n.fn.name.slice(0, -2);
        if (base === "pow" && n.args.length === 2) {
          return new M.OperatorNode("^", "pow", n.args.map(toPlain));
        }
        if (base === "sum" || base === "prod" || base === "derivative") return n;
        return new M.FunctionNode(new M.SymbolNode(base), n.args.map(toPlain));
      }
      return n;
    });
  }

  /* For display: natural log reads as ln, as it was typed. */
  function toShown(node) {
    return node.transform(function (n) {
      if (n.isFunctionNode && n.fn && n.fn.isSymbolNode) {
        if (n.fn.name === "log" && n.args.length === 1) {
          return new M.FunctionNode(new M.SymbolNode("ln"), n.args.map(toShown));
        }
        if (n.fn.name === "log10") {
          return new M.FunctionNode(new M.SymbolNode("log"), n.args.map(toShown));
        }
      }
      return n;
    });
  }

  function symbolicDerivative(args, _m, sc) {
    if (args.length < 2 || args.length > 3) throw new Error("derivative(expression, variable[, value])");
    var v = varName(args[1], "derivative");
    var d = M.derivative(toPlain(args[0]), v);
    if (args.length === 3) {
      var at = evalArg(args[2], sc);
      return rewrite(d).compile().evaluate(new Child(sc, v, at));
    }
    return { isShownExpression: true, node: toShown(d) };
  }
  symbolicDerivative.rawArgs = true;

  /* Names typed, into the functions that honour DEG/RAD and TI meaning. */
  function rewrite(node) {
    return node.transform(function (n) {
      if (n.isOperatorNode && n.fn === "pow" && n.args.length === 2) {
        return new M.FunctionNode(new M.SymbolNode("pow__"), n.args.map(rewrite));
      }
      if (!(n.isFunctionNode && n.fn && n.fn.isSymbolNode)) return n;
      var name = n.fn.name, args = n.args, to = null;
      if (TRIG_FWD.indexOf(name) >= 0 || TRIG_INV.indexOf(name) >= 0 || name === "atan2") to = name + "__";
      else if (name === "ln") to = "log";
      else if (name === "log" && args.length === 1) to = "log10";
      else if ((name === "sum" || name === "prod") && args.length >= 4 && args.length <= 5
               && args[1].isSymbolNode) to = name + "__";
      else if (name === "derivative" || (name === "diff" && args.length >= 2 && args[1].isSymbolNode)) {
        to = "derivative__";
      }
      if (!to) return n;
      return new M.FunctionNode(new M.SymbolNode(to), args.map(rewrite));
    });
  }

  /* math.js overflows its running product past about nCr(1000, 500), where
     the answer itself still fits a double; so on a non-finite answer the
     product is taken with division interleaved, and only a true overflow is
     reported, with its size. */
  function nCr(n, r) {
    var N = wholeNum(n, "n"), R = wholeNum(r, "r");
    if (R > N) return 0;
    var v = M.combinations(N, R);
    if (typeof v === "number" && isFinite(v)) return v;
    R = Math.min(R, N - R);
    var lg = (lgamma(N + 1) - lgamma(R + 1) - lgamma(N - R + 1)) / Math.LN10;
    if (lg > 308.2) throw new Error("nCr overflows: the answer is about 10^" + Math.floor(lg));
    if (R > 1e6) return Math.exp(lg * Math.LN10);
    v = 1;
    for (var i = 1; i <= R; i++) v = v * (N - R + i) / i;
    if (!isFinite(v)) throw new Error("nCr overflows: the answer is about 10^" + Math.floor(lg));
    return v;
  }
  function nPr(n, r) {
    var N = wholeNum(n, "n"), R = wholeNum(r, "r");
    if (R > N) return 0;
    return M.permutations(N, R);
  }

  /* (-8)^(1/3) is -2 on a TI in real mode; math.js gives the complex
     principal root. A negative real base under an exponent p/q with q odd
     takes the real root; everything else is math.js's pow. */
  function realPow(b, e) {
    if (typeof b === "number" && typeof e === "number" && b < 0 && !Number.isInteger(e)
        && isFinite(e)) {
      var r = rational(e, 1000, 1e-12);
      if (r && r[1] % 2 === 1) {
        var mag = Math.pow(-b, e);
        return Math.abs(r[0]) % 2 === 1 ? -mag : mag;
      }
    }
    return M.pow(b, e);
  }

  function frac(x) {
    var v = real(x, "frac");
    var r = rational(v, 1e6, 1e-12);
    if (!r) return v;
    return M.fraction(r[0], r[1]);
  }

  var extra = {
    nCr: nCr, nPr: nPr,
    fnInt: fnInt, nDeriv: nDeriv, solve: solve, seq: seq,
    sum__: sumOver, prod__: prodOver, derivative__: symbolicDerivative, pow__: realPow,
    stdDev: function () { return M.std.apply(null, arguments); },
    stdp: function (x) { return M.std(x, "uncorrected"); },
    varp: function (x) { return M.variance(x, "uncorrected"); },
    frac: frac,
    inf: Infinity,
    atan2__: function (y, x) {
      var r = M.atan2(y, x);
      return angle === "deg" ? M.multiply(r, 180 / Math.PI) : r;
    },
  };
  TRIG_FWD.forEach(function (n) { extra[n + "__"] = fwd(n); });
  TRIG_INV.forEach(function (n) { extra[n + "__"] = inv(n); });
  Object.keys(dist).forEach(function (k) {
    if (/^[A-Za-z0-9_]+$/.test(k)) extra[k] = dist[k];
  });
  M.import(extra);

  /* ---- showing a value */
  var FMT = { precision: 12, lowerExp: -6, upperExp: 12 };

  function show(v) {
    if (v === undefined || v === null) return "done";
    if (v && v.isShownExpression) return v.node.toString();
    if (typeof v === "function") return v.syntax ? v.syntax : "function";
    if (typeof v === "number") {
      if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
      return M.format(v, FMT).replace("e+", "e");
    }
    if (typeof v === "string") return v;
    if (v && v.isNode) return toShown(toPlain(v)).toString();
    try { return M.format(v, FMT); } catch (e) { return String(v); }
  }

  function fracHint(v) {
    if (typeof v !== "number" || !isFinite(v) || Number.isInteger(v) || Math.abs(v) > 1e9) return null;
    var r = rational(v, 10000, 1e-12);
    return r && Math.abs(r[0]) < 1e6 ? r[0] + "/" + r[1] : null;
  }

  function clean(msg) {
    msg = String(msg || "error").replace(/\s+/g, " ");
    msg = msg.replace(/\b(sin|cos|tan|sec|csc|cot|asin|acos|atan|asec|acsc|acot|atan2|sum|prod|derivative|pow)__\b/g, "$1");
    msg = msg.replace(/\blog10\b/g, "log");
    return msg.length > 200 ? msg.slice(0, 197) + "…" : msg;
  }

  function storable(v) {
    return typeof v === "number" || (v && (v.isMatrix || v.isComplex || v.isFraction
      || v.isBigNumber || v.isUnit)) || Array.isArray(v) || typeof v === "boolean"
      || typeof v === "string";
  }

  function recordDefs(parsed) {
    var nodes = parsed.isBlockNode ? parsed.blocks.map(function (b) { return b.node; }) : [parsed];
    nodes.forEach(function (n) {
      if (n.isFunctionAssignmentNode) defs[n.name] = n.toString();
      else if (n.isAssignmentNode && n.object && n.object.isSymbolNode) delete defs[n.object.name];
    });
  }

  function evaluate(text) {
    var src = String(text === undefined || text === null ? "" : text).trim();
    if (!src) return { ok: false, input: src, error: "nothing to evaluate" };
    try {
      var parsed = M.parse(preprocess(src));
      var value = rewrite(parsed).compile().evaluate(scope);
      if (value && value.isResultSet) {
        value = value.entries.length ? value.entries[value.entries.length - 1] : undefined;
      }
      recordDefs(parsed);
      if (typeof value === "number" && isNaN(value)) throw new Error("the result is not a number");
      if (storable(value)) scope.set("Ans", value);
      var last = parsed.isBlockNode ? parsed.blocks[parsed.blocks.length - 1].node : parsed;
      var text = last.isFunctionAssignmentNode ? last.toString() : show(value);
      return { ok: true, input: src, value: value, text: text, frac: fracHint(value) };
    } catch (e) {
      return { ok: false, input: src, error: clean(e && e.message) };
    }
  }

  function vars() {
    var out = [];
    scope.forEach(function (v, k) { out.push({ name: k, text: show(v) }); });
    return out;
  }

  function save() {
    var values = {};
    scope.forEach(function (v, k) {
      if (defs[k] || typeof v === "function" || !storable(v)) return;
      try { values[k] = JSON.stringify(v, M.replacer); } catch (e) { /* skip */ }
    });
    return { angle: angle, values: values, defs: Object.assign({}, defs) };
  }

  function restore(state) {
    if (!state || typeof state !== "object") return;
    if (state.angle === "deg" || state.angle === "rad") angle = state.angle;
    var values = state.values || {};
    Object.keys(values).forEach(function (k) {
      try { scope.set(k, JSON.parse(values[k], M.reviver)); } catch (e) { /* skip */ }
    });
    var d = state.defs || {};
    Object.keys(d).forEach(function (k) {
      try {
        var parsed = M.parse(d[k]);
        rewrite(parsed).compile().evaluate(scope);
        defs[k] = d[k];
      } catch (e) { /* a definition that no longer parses is dropped */ }
    });
  }

  function clearVars() { scope.clear(); defs = {}; }

  return {
    evaluate: evaluate,
    angle: function () { return angle; },
    setAngle: function (a) { angle = a === "deg" ? "deg" : "rad"; },
    vars: vars,
    clearVars: clearVars,
    save: save,
    restore: restore,
    math: M,
  };
}

return {
  create: create,
  dist: dist,
  integrate: integrate,
  derivativeAt: derivativeAt,
  findRoot: findRoot,
  preprocess: preprocess,
  rational: rational,
  special: { lgamma: lgamma, erf: erf, erfc: erfc, phi: phi, normInv: normInv,
             incGamma: incGamma, incBeta: incBeta, tInv: tInv },
};
});
