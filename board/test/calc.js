// The calculator's numbers: every TI distribution, fnInt, nDeriv, solve, nCr/nPr, DEG/RAD, Ans, variables, errors.
//
// The reference values were computed with mpmath at 40 digits (the TI-84 and
// scipy agree with them to the digits they show). The bar is 1e-9 relative,
// which is what "the calculator is right" has to mean for a p-value.
//
// No DOM here: web/calc-core.js loads through require, on the vendored
// web/mathjs/math.js. test/interactive.js drives the panel in the real page.

const path = require('path');
const WEB = path.join(__dirname, '..', 'web');
const math = require(path.join(WEB, 'mathjs', 'math.js'));
const Core = require(path.join(WEB, 'calc-core.js'));

const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };

const REF = [
  ["normalcdf(-1,1)", 0.6826894921370859],
  ["normalcdf(-1e99,1.96)", 0.9750021048517795],
  ["normalcdf(2,1e99)", 0.02275013194817921],
  ["normalcdf(-40,-38)", 2.88542835e-316],
  ["normalcdf(5,6)", 2.8566498423415623e-7],
  ["normalcdf(-0.5,2.5,1,2)", 0.5467452952462636],
  ["normalcdf(1,-1)", -0.6826894921370859],
  ["normalpdf(0)", 0.3989422804014327],
  ["normalpdf(1.5,1,2)", 0.1933340584014246],
  ["normalpdf(30)", 1.4736461348785476e-196],
  ["invNorm(0.975)", 1.9599639845400538],
  ["invNorm(1e-10)", -6.361340902404057],
  ["invNorm(0.3,10,2)", 8.951198974583919],
  ["invNorm(0.999999)", 4.753424308817087],
  ["invNorm(1e-300)", -37.0470962993612],
  ["tcdf(-1e99,2.0,10)", 0.9633059826146299],
  ["tcdf(1,2,3)", 0.12583812519846374],
  ["tcdf(3,1e99,5)", 0.015049623948731286],
  ["tcdf(-1e99,-10,2.5)", 0.002220747883653712],
  ["tcdf(-2,2,1)", 0.7048327646991335],
  ["tcdf(-1e99,1.5,300)", 0.9326669834253691],
  ["tpdf(0.5,4)", 0.3222618685603871],
  ["tpdf(2,1e6)", 0.053991060997102186],
  ["tpdf(-3,1)", 0.03183098861837907],
  ["invT(0.975,10)", 2.228138851986274],
  ["invT(0.001,3)", -10.214531852407386],
  ["invT(0.9,1.5)", 2.196398417565538],
  ["invT(0.05,1)", -6.313751514675042],
  ["chi2cdf(0,3.84,1)", 0.9499564787512949],
  ["chi2cdf(10,1e99,3)", 0.018566135463043233],
  ["chi2cdf(0,0.001,5)", 1.6814877189706276e-9],
  ["chi2cdf(0,100,100)", 0.5188083154720433],
  ["chi2cdf(60,1e99,10)", 3.6243009520614882e-9],
  ["chi2pdf(2,3)", 0.20755374871029736],
  ["chi2pdf(0.5,1)", 0.4393912894677224],
  ["chi2pdf(150,120)", 0.0041065281354399135],
  ["Fcdf(0,3,2,10)", 0.904632568359375],
  ["Fcdf(1,1e99,5,7)", 0.48129391295820556],
  ["Fcdf(0,0.5,3,8)", 0.30737513305615366],
  ["Fpdf(1.2,3,8)", 0.32082934732955604],
  ["Fpdf(0.5,1,4)", 0.3950617283950617],
  ["Fpdf(2,20,30)", 0.11002009693918914],
  ["binompdf(10,0.5,3)", 0.1171875],
  ["binompdf(1000,0.3,300)", 0.027521003821268385],
  ["binompdf(50,0.01,0)", 0.6050060671375367],
  ["binompdf(20,0.7,20)", 0.0007979226629761189],
  ["binomcdf(10,0.5,3)", 0.171875],
  ["binomcdf(20000,0.4,7900)", 0.07540478474728712],
  ["binomcdf(100,0.3,20)", 0.016462853241869486],
  ["poissonpdf(3,2)", 0.22404180765538775],
  ["poissoncdf(3,2)", 0.42319008112684353],
  ["poissoncdf(100,80)", 0.02264917664225561],
  ["poissonpdf(1000,1000)", 0.012614611348721499],
  ["poissoncdf(0.5,0)", 0.6065306597126334],
  ["geometpdf(0.2,3)", 0.128],
  ["geometcdf(0.2,3)", 0.488],
  ["geometcdf(1e-9,10)", 9.999999955e-9],
  ["fnInt(x^2,x,0,3)", 9],
  ["fnInt(e^(-x^2),x,-inf,inf)", 1.772453850905516],
  ["fnInt(1/sqrt(x),x,0,1)", 2],
  ["fnInt(1/(1+x^2),x,0,inf)", 1.5707963267948966],
  ["fnInt(sin(x),x,0,pi)", 2],
  ["fnInt(x^20,x,0,1)", 0.047619047619047616],
  ["fnInt(e^x,x,-inf,0)", 1],
  ["fnInt(ln(x),x,0,1)", -1],
  ["fnInt(x^2,x,3,0)", -9],
  ["fnInt(normalpdf(x),x,-inf,1.96)", 0.9750021048517795],
  ["nDeriv(x^3,x,2)", 12],
  ["nDeriv(sin(x),x,1)", 0.5403023058681398],
  ["nDeriv(e^x,x,3)", 20.085536923187668],
  ["solve(x^2-2,x,1)", 1.4142135623730951],
  ["solve(cos(x)-x,x,0)", 0.7390851332151607],
  ["solve(x^3-2x-5,x,2)", 2.0945514815423265],
  ["gamma(5.5)", 52.34277778455352],
  ["gamma(0.5)", 1.772453850905516],
  ["erf(0.5)", 0.5204998778130465],
  // where review found the first build wrong
  ["nDeriv(ln(x),x,0.05)", 20],
  ["nDeriv(sqrt(x),x,0.01)", 5],
  ["nDeriv(asin(x),x,0.95)", 3.202563076101742],
  ["fnInt(1/(1+x^2),x,0,1e99)", 1.5707963267948966],
  ["fnInt(normalpdf(x),x,-1e99,1e99)", 1],
  ["fnInt(1/x,x,1,1e99)", 227.95592420641054],
  ["fnInt(x,x,0,1e20)", 5e39],
  ["nCr(1000,500)", 2.7028824094543655e299],
  ["geometpdf(1,1)", 1],
  ["solve(tan(x)-1,x,1.5)", 0.7853981633974483],
  ["tcdf(-1e99,1.96,1.01e7)", 0.9750020911246146],
  ["tcdf(2,1e99,9e6)", 0.022750146945670696842],
  ["tcdf(-1e99,-3,2e7)", 0.0013498996935737932898],
  ["invT(0.975,1.2e7)", 1.9599641822293430278],
  ["invT(0.975,1e9)", 1.9599639869123254686],
  ["Fcdf(1,1e99,2e6,2e6)", 0.5],
];

// ---- every reference value, to 1e-9 relative
{
  const e = Core.create(math);
  let worst = 0, n = 0;
  for (const [expr, want] of REF) {
    const r = e.evaluate(expr);
    if (!r.ok) { fail(expr + ' did not evaluate: ' + r.error); continue; }
    const got = Number(r.value);
    const rel = Math.abs(got - want) / Math.max(Math.abs(want), 1e-300);
    if (!(rel <= 1e-9)) fail(expr + ' = ' + got + ', want ' + want + ' (rel ' + rel.toExponential(2) + ')');
    else { n++; worst = Math.max(worst, rel); }
  }
  ok(n + ' of ' + REF.length + ' reference values within 1e-9 (worst ' + worst.toExponential(1) + ')');
}

// ---- the values the request named, as displayed
{
  const e = Core.create(math);
  const shown = [
    ['normalcdf(-1,1)', '0.682689492137'],
    ['invNorm(0.975)', '1.95996398454'],
    ['binompdf(10,0.5,3)', '0.1171875'],
    ['poissoncdf(3,2)', '0.423190081127'],
    ['fnInt(x^2,x,0,3)', '9'],
    ['fnInt(e^(-x^2),x,-inf,inf)', e.evaluate('sqrt(pi)').text],
    ['10 nCr 3', '120'],
    ['10 nPr 3', '720'],
    ['nCr(10,3) + 2 nCr 1', '122'],
    ['(4+1) nCr (1+1)', '10'],
    ['3 nCr 5', '0'],
    ['5!', '120'],
    ['gamma(5)', '24'],
    ['log(1000)', '3'],
    ['log(8, 2)', '3'],
    ['ln(e^2)', '2'],
    ['2^10', '1024'],
    ['2 + 3 * 4', '14'],
    ['-2^2', '-4'],
    ['√16 + √(9)', '7'],
    ['2π', '6.28318530718'],
    ['17 mod 5', '2'],
    ['abs(-3)', '3'],
    ['1.5e3', '1500'],
    ['1e99', '1e99'],
    ['{1,2,3} * 2', '[2, 4, 6]'],
    ['mean({1,2,3,4})', '2.5'],
    ['median([5,1,3])', '3'],
    ['std([1,2,3,4])', '1.29099444874'],
    ['stdp([1,2,3,4])', '1.11803398875'],
    ['variance([1,2,3,4])', '1.66666666667'],
    ['varp([1,2,3,4])', '1.25'],
    ['sum([1,2,3])', '6'],
    ['prod([1,2,3,4])', '24'],
    ['sort([3,1,2])', '[1, 2, 3]'],
    ['sum(k^2, k, 1, 10)', '385'],
    ['seq(k^2, k, 1, 4)', '[1, 4, 9, 16]'],
    ['det([1,2;3,4])', '-2'],
    ['inv([1,2;3,4])', '[[-2, 1], [1.5, -0.5]]'],
    ['transpose([1,2;3,4])', '[[1, 3], [2, 4]]'],
    ['[1,2;3,4] * [1;1]', '[[3], [7]]'],
    ['derivative(x^3, x)', '3 * x ^ 2'],
    ['derivative(ln(x), x)', '1 / x'],
    ['derivative(x^3, x, 2)', '12'],
    ['frac(0.75)', '3/4'],
    ['binompdf(3, 0.5)', '[0.125, 0.375, 0.375, 0.125]'],
    ['sin(pi)', '0'],
    ['mod(-7,3)', '2'],
    ['(-8)^(1/3)', '-2'],
    ['(-8)^(2/3)', '4'],
    ['(-32)^(1/5)', '-2'],
  ];
  for (const [expr, want] of shown) {
    const r = e.evaluate(expr);
    if (!r.ok) fail(expr + ': ' + r.error);
    else if (r.text !== want) fail(expr + ' shows "' + r.text + '", want "' + want + '"');
  }
  ok(shown.length + ' expressions display what a TI would show');
  const third = e.evaluate('1/3');
  third.frac === '1/3' ? ok('a result that is a small fraction says so beside the decimal')
                       : fail('1/3 carries no fraction hint: ' + third.frac);
}

// ---- DEG / RAD
{
  const e = Core.create(math);
  e.evaluate('sin(30)').text === '-0.988031624093'
    ? ok('radians by default') : fail('not radians by default');
  e.setAngle('deg');
  const deg = [['sin(30)', 0.5], ['cos(60)', 0.5], ['tan(45)', 1], ['sin(180)', 0],
               ['cos(90)', 0], ['asin(1)', 90], ['atan(1)', 45], ['acos(0)', 90],
               ['sin(30°)', 0.5], ['sinh(0)', 0]];
  deg.forEach(([x, want]) => {
    const r = e.evaluate(x);
    if (!r.ok || Math.abs(r.value - want) > 1e-12) fail('DEG ' + x + ' = ' + (r.ok ? r.value : r.error));
  });
  ok('degrees: exact at the special angles, inverse trig answers in degrees');
  const dom = e.evaluate('asin(2)');
  !dom.ok && /only defined/.test(dom.error) ? ok('asin(2) in degrees is a domain error, not a complex "angle"')
                                           : fail('DEG asin(2) gave ' + JSON.stringify(dom.text || dom.error));
  const t = e.evaluate('tan(90)');
  !t.ok && /undefined/.test(t.error) ? ok('tan(90°) is an error, not 1.6e16')
                                    : fail('tan(90°) gave ' + JSON.stringify(t));
  e.evaluate('g(t) = sin(t)');
  e.setAngle('rad');
  Math.abs(e.evaluate('g(pi/2)').value - 1) < 1e-15
    ? ok('a function honours the mode it is called in, not the one it was typed in')
    : fail('g(pi/2) in radians is ' + e.evaluate('g(pi/2)').text);
}

// ---- Ans and variables, and that they survive a save and restore
{
  const e = Core.create(math);
  e.evaluate('x = 3');
  e.evaluate('x^2');
  e.evaluate('Ans + 1').text === '10' ? ok('Ans is the last result') : fail('Ans is wrong');
  e.evaluate('*2').text === '20' ? ok('a line that opens with an operator continues from Ans')
                                 : fail('"*2" did not continue from Ans');
  e.evaluate('f(t) = t^2 + 1').text === 'f(t) = t ^ 2 + 1'
    ? ok('a function definition shows as itself') : fail('function definition display');
  e.evaluate('f(4)').text === '17' ? ok('and can be called') : fail('f(4) is wrong');
  e.evaluate('fnInt(x, x, 0, 2)').text === '2' && e.evaluate('x').text === '3'
    ? ok('the variable of an integral does not overwrite the one stored under its name')
    : fail('fnInt clobbered x');
  e.setAngle('deg');
  const before = e.evaluate('x + f(1) + Ans').text;
  const state = JSON.parse(JSON.stringify(e.save()));
  const e2 = Core.create(math);
  e2.restore(state);
  e2.angle() === 'deg' && e2.evaluate('Ans').text === before
    && e2.evaluate('x').text === '3' && e2.evaluate('f(1)').text === '2'
    ? ok('variables, functions, Ans and DEG/RAD come back after a reload')
    : fail('restore lost something: ' + JSON.stringify(state));
  e2.clearVars();
  !e2.evaluate('x').ok ? ok('clear forgets the variables') : fail('clear kept x');
}

// ---- errors are answers, never throws
{
  const e = Core.create(math);
  const bad = ['foo(', '1 +', 'qqq', 'normalcdf(1)', 'invNorm(1.5)', 'invNorm(0)',
               'binompdf(10, 2, 3)', 'tcdf(0, 1, -2)', 'nCr(2.5, 1)', 'sqrt(', '10 nCr',
               'fnInt(1/x, x, -1, 1)', 'solve(x^2 + 1, x, 0)', 'seq(k, k, 1, 1e9)', '',
               'solve(1/(x-2), x, 1.9)', 'solve(1/x, x, 1)', 'solve(tan(x), x, pi/2, {1.5, 1.6})',
               'nCr(2000, 1000)'];
  let thrown = 0, answered = 0;
  bad.forEach((b) => {
    try {
      const r = e.evaluate(b);
      if (!r.ok && typeof r.error === 'string' && r.error.length) answered++;
      else fail('"' + b + '" was accepted: ' + JSON.stringify(r.text));
    } catch (err) { thrown++; fail('"' + b + '" threw ' + err.message); }
  });
  thrown === 0 && answered === bad.length
    ? ok(bad.length + ' bad inputs each come back as an error message, none thrown')
    : fail('error handling: ' + thrown + ' thrown');
  const m = e.evaluate('sin(').error + e.evaluate('normalcdf(1)').error;
  !/__/.test(m) ? ok('error messages carry the names that were typed')
                : fail('an internal name leaked into an error: ' + m);
}

// ---- it is quick enough to press = on
{
  const e = Core.create(math);
  const t0 = Date.now();
  ['fnInt(1/sqrt(x),x,0,1)', 'fnInt(e^(-x^2),x,-inf,inf)', 'binomcdf(20000,0.4,7900)',
   'invT(1e-10, 1.5)', 'solve(cos(x)-x,x,0)'].forEach((x) => e.evaluate(x));
  const ms = Date.now() - t0;
  ms < 2000 ? ok('the slow cases take ' + ms + ' ms together')
            : fail('the slow cases take ' + ms + ' ms');
}

console.log(errors.length ? '\n' + errors.length + ' FAILURES' : '\nthe calculator is right');
process.exit(errors.length ? 1 : 0);
