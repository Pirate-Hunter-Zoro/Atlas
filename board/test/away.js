// A SWITCH FROM A PAGE THAT IS NOT ON THE ADDRESS.
//
//     "I just tried to access probability ... I can't open the lesson. I just
//      get bounced back to the home screen."
//
// The front door switches by re-pointing the one HTTPS name and waiting for its
// own `/health` to answer as the workspace asked for. A page loaded off a
// board's own port -- `http://<name>:8937/` -- is not behind that name, so the
// answer never changes: 45 seconds, then a reload into the workspace being
// left. What this guards is `elsewhere` in `home.js`, which sends such a page
// to where the opened board answers instead, and leaves a page on the address
// to the ordinary wait.

const fs = require('fs');
const path = require('path');

const js = fs.readFileSync(path.join(__dirname, '..', 'web', 'home.js'), 'utf8');
const errors = [];
function check(name, ok) {
  console.log((ok ? 'ok   ' : 'FAIL ') + name);
  if (!ok) errors.push(name);
}

const at = js.indexOf('function elsewhere(');
check('home.js has elsewhere', at >= 0);
let src = js.slice(at);
src = src.slice(0, src.indexOf('\n}\n') + 2);

function run(href, res, to) {
  const u = new URL(href);
  const location = { protocol: u.protocol, hostname: u.hostname, port: u.port };
  return new Function('location', src + '\nreturn elsewhere;')(location)(res, to);
}

const NAME = 'compute-node.tail0c6c62.ts.net';
const RES = { ok: true, address: true, host: NAME, port: 8808 };

check('on the address, nothing: the ordinary wait is right',
      run('https://' + NAME + '/', RES, '/') === '');
check('on a board\'s own tailnet port, the address -- which now points at it',
      run('http://' + NAME + ':8937/', RES, '/') === 'https://' + NAME + '/');
check('and the surface asked for comes along',
      run('http://' + NAME + ':8937/', RES, '/board#x')
      === 'https://' + NAME + '/board#x');
check('on the tailnet IP, the address too',
      run('http://100.105.212.85:8937/', RES, '/') === 'https://' + NAME + '/');
check('on this machine, the opened board\'s own port',
      run('http://127.0.0.1:8937/', RES, '/library') === 'http://127.0.0.1:8808/library');
check('with no tailnet at all, on the address-less https page, nothing',
      run('https://board.test/', { ok: true, port: 8808 }, '/') === '');
check('a switch that does not name a port leaves this machine alone',
      run('http://127.0.0.1:8937/', { ok: true, host: NAME }, '/') === '');

// The server half: /switch has to say where the opened board is, and why the
// address did not move when it did not.
const routes = fs.readFileSync(path.join(__dirname, '..', 'tutorboard', 'server',
                                         'routes', 'machines.py'), 'utf8');
const sw = routes.slice(routes.indexOf('if path == "/switch"'));
check('/switch answers with the opened board\'s port and the address',
      /"port": port/.test(sw) && /"host": tailscale\.tailnet_self\(\)/.test(sw));
check('and with the reason the address did not move',
      /"address_error"/.test(sw));

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\na switch lands from whatever address the page is on');
process.exit(errors.length ? 1 : 0);
