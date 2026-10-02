// THE MAP, STRAIGHT FROM THE FRONT DOOR.
//
//     "Right now, I have to open up a tutoring session to then press the map
//      button and go to a map of the course/project. I want to just go straight
//      to the map of a course/project, no tutoring session necessary."
//
// Three halves. `addrRoute` in `home.js` carries a bare workspace address to
// the board whole, which `addrGo` opens as the map. `switchTo` tells `/switch`
// a map is only looking, so no assistant is started. And the map's ✕ on a
// board with no sitting under it goes back to the door, not to a blank lesson.

const fs = require('fs');
const path = require('path');

const WEB = path.join(__dirname, '..', 'web');
const home = fs.readFileSync(path.join(WEB, 'home.js'), 'utf8');
const board = fs.readFileSync(path.join(WEB, 'board.js'), 'utf8');
const errors = [];
function check(name, ok) {
  console.log((ok ? 'ok   ' : 'FAIL ') + name);
  if (!ok) errors.push(name);
}

function fn(src, name) {
  const at = src.indexOf('function ' + name + '(');
  if (at < 0) return '';
  const rest = src.slice(at);
  return rest.slice(0, rest.indexOf('\n}\n') + 2);
}

// ------------------------------------------------------------ addrRoute
const ADDR = '#/w/courses/Probability';
function route(current, surface) {
  const went = { href: null, switched: null };
  const location = {
    hash: ADDR,
    set href(v) { went.href = v; }
  };
  const atlas = { workspaces: [{ id: 'courses/Probability',
                                 repo: 'Probability', current: current }] };
  const Address = { parse: function () {
    return { text: ADDR, ws: 'courses/Probability', surface: surface };
  } };
  const body = fn(home, 'addrNow') + fn(home, 'addrRoute')
    + '\nreturn addrRoute;';
  new Function('window', 'location', 'atlas', 'atlasSay', 'switchTo',
               'addrDone', body)(
    { Address: Address, location: location }, location, atlas,
    function () {},
    function (repo, addr, page, mapOnly) {
      went.switched = { repo: repo, addr: addr, page: page, mapOnly: mapOnly };
    }, '')();
  return went;
}

check('home.js has addrRoute', fn(home, 'addrRoute') !== '');
let w = route(true, 'workspace');
check('a workspace already served lands on the board WITH its address',
      w.href === '/board' + ADDR);
w = route(false, 'workspace');
check('a workspace not served is switched to with its address intact',
      w.switched && w.switched.repo === 'Probability' && w.switched.addr === ADDR);
check('and the switch is map-only', w.switched && w.switched.mapOnly === true);
w = route(false, 'card');
check('an address naming a card still starts the assistant',
      w.switched && w.switched.addr === ADDR && !w.switched.mapOnly);

// ------------------------------------------------------------- switchTo
function asked(mapOnly) {
  let sent = null;
  const body = fn(home, 'switchTo') + '\nreturn switchTo;';
  const fetch = function (url, opts) {
    sent = JSON.parse(opts.body);
    return new Promise(function () {});
  };
  new Function('fetch', 'moving', 'showBusy', body)(fetch, null,
                                                     function () {})(
    'Probability', ADDR, '', mapOnly);
  return sent;
}
check('a map-only switch asks /switch not to start an assistant',
      asked(true).agent === false);
check('an ordinary switch asks nothing of the kind',
      !('agent' in asked(false)));

// --------------------------------------------------------- the ✕ on the map
function leave(live, reading) {
  const went = { href: null, closed: false };
  const body = fn(board, 'mapNoSitting') + fn(board, 'mapLeave')
    + '\nreturn mapLeave;';
  new Function('window', 'reading', 'lastLive', 'closeMap', body)(
    { location: { set href(v) { went.href = v; } } }, reading, live,
    function () { went.closed = true; })();
  return went;
}
check('board.js has mapLeave', fn(board, 'mapLeave') !== '');
w = leave({ cards: [], turns: [] }, null);
check('✕ with no sitting goes to the front door',
      w.href === '/' && !w.closed);
w = leave({ cards: [{ id: '0001' }], turns: [] }, null);
check('✕ with a lesson open goes back to the lesson', w.closed && w.href === null);
w = leave({ cards: [], turns: [{ id: 't1' }] }, null);
check('and one turn in it is already a lesson', w.closed && w.href === null);
w = leave(null, null);
check('before the payload has arrived, nothing leaves the board', w.closed);
check('the ✕ and Escape both go through mapLeave',
      /els\.mapClose\.onclick = mapLeave;/.test(board)
      && /if \(els\.map && !els\.map\.hidden\) mapLeave\(\);/.test(board));

// ------------------------------------------------------------- the server
const routes = fs.readFileSync(path.join(__dirname, '..', 'tutorboard', 'server',
                                         'routes', 'machines.py'), 'utf8');
const sw = routes.slice(routes.indexOf('if path == "/switch"'));
check('/switch reads the agent flag before starting one',
      /payload\.get\("agent", True\) is not False/.test(sw));

// ------------------------------------------- learn, coach, build from the door
function openAs(current, kind) {
  const went = { href: null, switched: null };
  const location = { set href(v) { went.href = v; } };
  new Function('location', 'switchTo', fn(home, 'openAs') + '\nreturn openAs;')(
    location, function (repo, addr, page, mapOnly) {
      went.switched = { repo: repo, addr: addr, page: page, mapOnly: mapOnly };
    })({ repo: 'Algo-Solutions', current: current }, kind);
  return went;
}
w = openAs(false, 'coach');
check('Coach on the sheet switches the board and lands on the lesson as coach',
      w.switched && w.switched.repo === 'Algo-Solutions'
      && w.switched.page === '/board?kind=coach' && !w.switched.mapOnly);
w = openAs(true, 'build');
check('and on the workspace already served it goes straight there',
      w.href === '/board?kind=build' && !w.switched);

function kindAsked(search) {
  const replaced = [];
  const window = { location: { search: search, pathname: '/board', hash: '#x' },
                   history: { replaceState: function (a, b, u) { replaced.push(u); } } };
  const got = new Function('window', fn(board, 'kindAsked') + '\nreturn kindAsked;')(
    window)();
  return { got: got, replaced: replaced };
}
let k = kindAsked('?kind=coach');
check('the board reads the kind once and takes it out of the address',
      k.got === 'coach' && k.replaced[0] === '/board#x');
k = kindAsked('?map=1&kind=learn');
check('leaving anything else in the address alone',
      k.got === 'learn' && k.replaced[0] === '/board?map=1#x');
check('a word that is not a kind is not read as one',
      kindAsked('?kind=rm').got === '');
check('and the board sets it as the sitting\'s aim, on the lesson',
      /var kindWanted = kindAsked\(\);\s*if \(kindWanted\) \{ setAim\(KIND_AIMS\[kindWanted\]\); return; \}/
        .test(board)
      && board.indexOf('var kindWanted') < board.indexOf('if (mapAsked()) { openMap(); return; }'));

console.log(errors.length ? '\n' + errors.length + ' FAILURES'
                          : '\nthe front door opens a workspace on its map');
process.exit(errors.length ? 1 : 0);
