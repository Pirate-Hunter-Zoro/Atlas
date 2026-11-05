// A bare session board follows the document the session was last reading
// (`resumeDoc` in board.js), but only one its own subject holds: a `doc` whose
// `subject` is another one (the session bound elsewhere since) names an id
// this board would read in the wrong library, so it is left alone. A
// session's own upload is in no subject and always resumes.
//
// No browser: `resumeDoc` is lifted out of board.js and run against stubs.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const errors = [];
const ok = (m) => console.log('ok   ' + m);
const fail = (m) => { errors.push(m); console.log('FAIL ' + m); };
const check = (m, cond, detail) => (cond ? ok(m) : fail(m + (detail ? '\n       ' + detail : '')));

const src = fs.readFileSync(path.join(__dirname, '..', 'web', 'board.js'), 'utf8');
const start = src.indexOf('function resumeDoc() {');
const end = src.indexOf('\n}\n', start);
if (start < 0 || end < 0) {
  console.log('FAIL resumeDoc is in board.js');
  process.exit(1);
}
const body = src.slice(start, end + 2);

// What the board would open for a payload whose state is `state`, or null.
function resumes(state) {
  const went = [];
  const ctx = {
    window: { location: { hash: '', pathname: '/s/20261102-144106/board', search: '' },
              history: { replaceState: () => {} } },
    lastLive: { state: state },
    paperName: '',
    spell: (spec) => '#/s/20261102-144106/doc/' + spec.doc + (spec.page ? '/p' + spec.page : ''),
    addrParse: (text) => ({ text: text }),
    addrGo: (a) => { went.push(a.text); },
    String: String, Number: Number,
  };
  vm.createContext(ctx);
  vm.runInContext(body + '\nresumeDoc();', ctx);
  return went.length ? went[0] : null;
}

check('a doc with no subject resumes on the board',
  resumes({ subject: 'courses/Probability',
            doc: { id: 'materials-module-2', page: 7, name: 'Module-2.pdf' } })
    === '#/s/20261102-144106/doc/materials-module-2/p7');
check('a doc naming the board\'s own subject resumes',
  resumes({ subject: 'courses/Probability',
            doc: { id: 'materials-module-2', page: 3, name: 'Module-2.pdf',
                   subject: 'courses/Probability' } })
    === '#/s/20261102-144106/doc/materials-module-2/p3');
check('a doc in another subject is not opened in this board\'s library',
  resumes({ subject: 'courses/Probability',
            doc: { id: 'materials-birth-death-urgent-care', page: 13,
                   name: 'birth_death_urgent_care.pdf', subject: 'courses/Random' } })
    === null);
check('the session\'s own upload resumes whatever subject it names',
  resumes({ subject: 'courses/Random',
            doc: { id: 'uploads-slides', page: 2, name: 'slides.pdf',
                   subject: 'courses/Probability' } })
    === '#/s/20261102-144106/doc/uploads-slides/p2');
check('no doc, nothing opened', resumes({ subject: 'courses/Probability', doc: null }) === null);

if (errors.length) {
  console.log('\n' + errors.length + ' failed');
  process.exit(1);
}
console.log('\nall passed');
