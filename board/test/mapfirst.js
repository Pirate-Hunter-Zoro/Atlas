// THE MAP, STRAIGHT FROM THE FRONT DOOR.
//
//     "Right now, I have to open up a tutoring session to then press the map
//      button and go to a map of the course/project. I want to just go straight
//      to the map of a course/project, no tutoring session necessary."
//
// Two halves. The map's ✕ on a board with no sitting under it goes back to
// the door, not to a blank lesson; and `/switch` tells the server a map is
// only looking, so no assistant is started. The start screen opens sessions
// by URL and has no switch of its own (T23; test/home.js).

const fs = require('fs');
const path = require('path');

const WEB = path.join(__dirname, '..', 'web');
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

let w;
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
