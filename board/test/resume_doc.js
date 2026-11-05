// A bare session board follows the document the session was last reading
// (`resumeDoc` in board.js), in whichever subject that document is in: a
// `doc` whose `subject` is not the session's (bound elsewhere since, as the
// real 20261102-144106 was) is opened there, and every read and write of it
// names that subject (`docSubject`, `inSubject`, `seenDoc`). A session's own
// upload is in no subject and always its own.
//
// No browser: the functions are lifted out of board.js and run against stubs.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (m, cond, detail) => (cond ? ok(m) : fail(m + (detail ? '\n       ' + detail : '')));

const src = fs.readFileSync(path.join(__dirname, '..', 'web', 'board.js'), 'utf8');

function lift(head) {
  const start = src.indexOf(head);
  const end = src.indexOf('\n}\n', start);
  if (start < 0 || end < 0) {
    console.log('FAIL ' + head + ' is in board.js');
    process.exit(1);
  }
  return src.slice(start, end + 2);
}

const body = ['function resumeDoc() {', 'function docSubject(id) {',
              'function inSubject(path, subject) {', 'function seenDoc() {']
  .map(lift).join('\n');

const SID = '20261102-144106';

function board(state, extra) {
  const went = [];
  const ctx = Object.assign({
    window: { location: { hash: '', pathname: '/s/' + SID + '/board', search: '' },
              history: { replaceState: () => {} } },
    lastLive: { state: state },
    paperName: '', paperOpen: null, paperSubject: '', reader: null,
    spell: (spec) => '#/s/' + SID + '/doc/' + spec.doc + (spec.page ? '/p' + spec.page : ''),
    addrParse: (text) => ({ text: text }),
    addrGo: (a) => { went.push(a.text); },
    paperIdent: (kind) => kind.slice(4),
    paperTitle: () => 'this document',
    String: String, Number: Number, encodeURIComponent: encodeURIComponent,
  }, extra || {});
  vm.createContext(ctx);
  vm.runInContext(body, ctx);
  ctx.went = went;
  return ctx;
}

function resumes(state) {
  const b = board(state);
  vm.runInContext('resumeDoc();', b);
  return b.went.length ? b.went[0] : null;
}

const RANDOM_DOC = { id: 'materials-birth-death-urgent-care', page: 13,
                     name: 'birth_death_urgent_care.pdf', subject: 'courses/Random' };

check('a doc with no subject resumes on the board',
  resumes({ subject: 'courses/Probability',
            doc: { id: 'materials-module-2', page: 7, name: 'Module-2.pdf' } })
    === '#/s/' + SID + '/doc/materials-module-2/p7');
check('a doc naming the board\'s own subject resumes',
  resumes({ subject: 'courses/Probability',
            doc: { id: 'materials-module-2', page: 3, name: 'Module-2.pdf',
                   subject: 'courses/Probability' } })
    === '#/s/' + SID + '/doc/materials-module-2/p3');
check('a doc in another subject resumes too (the real 20261102-144106)',
  resumes({ subject: 'courses/Probability', doc: RANDOM_DOC })
    === '#/s/' + SID + '/doc/materials-birth-death-urgent-care/p13');
check('the session\'s own upload resumes whatever subject it names',
  resumes({ subject: 'courses/Random',
            doc: { id: 'uploads-slides', page: 2, name: 'slides.pdf',
                   subject: 'courses/Probability' } })
    === '#/s/' + SID + '/doc/uploads-slides/p2');
check('no doc, nothing opened', resumes({ subject: 'courses/Probability', doc: null }) === null);
check('an address already in the bar is not overridden', (() => {
  const b = board({ subject: 'courses/Probability', doc: RANDOM_DOC });
  b.window.location.hash = '#/s/' + SID + '/card/0003';
  vm.runInContext('resumeDoc();', b);
  return b.went.length === 0;
})());

// ---- which subject a document is read in ----------------------------------
const foreign = board({ subject: 'courses/Probability', doc: RANDOM_DOC });
const subjectOf = (b, id) => vm.runInContext('docSubject(' + JSON.stringify(id) + ')', b);
check('the stored doc in another subject is read there',
  subjectOf(foreign, RANDOM_DOC.id) === 'courses/Random');
check('another id is read in the board\'s own subject',
  subjectOf(foreign, 'materials-module-2') === '');
check('a doc naming the board\'s own subject is read in it',
  subjectOf(board({ subject: 'courses/Random', doc: RANDOM_DOC }), RANDOM_DOC.id) === '');
check('a doc naming no subject is read in the board\'s',
  subjectOf(board({ subject: 'courses/Probability',
                    doc: { id: 'materials-x', page: 1 } }), 'materials-x') === '');
check('an upload is the session\'s whatever its doc names',
  subjectOf(board({ subject: 'courses/Probability',
                    doc: { id: 'uploads-x', page: 1, subject: 'courses/Random' } }),
            'uploads-x') === '');
check('no payload yet, no subject', subjectOf(board(null), RANDOM_DOC.id) === '');

const url = (p, s) => vm.runInContext('inSubject(' + JSON.stringify(p) + ', '
                                      + JSON.stringify(s) + ')', foreign);
check('a path with no subject is left as it is',
  url('/s/x/view/doc/a', '') === '/s/x/view/doc/a');
check('a subject rides as ?subject=, encoded',
  url('/s/x/view/doc/a', 'courses/Random') === '/s/x/view/doc/a?subject=courses%2FRandom');
check('after a query already there, as &subject=',
  url('/s/x/marked/doc/a/b.pdf?x=1', 'courses/Random')
    === '/s/x/marked/doc/a/b.pdf?x=1&subject=courses%2FRandom');

// ---- what `/seen` is told ---------------------------------------------------
function seen(subject) {
  const b = board({ subject: 'courses/Probability', doc: RANDOM_DOC },
                  { paperOpen: 'doc/' + RANDOM_DOC.id, paperSubject: subject,
                    paperName: RANDOM_DOC.name,
                    reader: { pageInView: () => 4 } });
  return vm.runInContext('seenDoc()', b);
}
const told = seen('courses/Random');
check('/seen names the subject a document in another one is in',
  told && told.id === RANDOM_DOC.id && told.page === 4
    && told.subject === 'courses/Random', JSON.stringify(told));
check('/seen names "" for a document in the board\'s own subject',
  seen('').subject === '');

// ---- every read and write of the open document names its subject -----------
const wired = [
  ['the pages', 'pagesUrl: inSubject(paperViewUrl(kind), paperSubject)'],
  ['the ink saves', 'get url() { return inSubject(BASE + "/annotate/save", inkSubject); }'],
  ['the marked copy', 'return BASE + (doc ? inSubject(path, paperSubject) : path);'],
  ['opening a document', 'paperSubject = kind.indexOf("doc/") === 0 ? docSubject(paperIdent(kind)) : "";'],
];
wired.forEach(([what, line]) => check(what + ' name the document\'s subject',
                                      src.indexOf(line) >= 0, line));

if (errors.length) {
  console.log('\n' + errors.length + ' failed');
  process.exit(1);
}
console.log('\nall passed');
