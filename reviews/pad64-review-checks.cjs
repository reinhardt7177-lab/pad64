// Focused source-level reproductions. No browser/audio device is emulated.
// These checks confirm current defects; passing means reproduced, not fixed.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
// The original report describes this immutable pre-fix revision.
const html = require('node:child_process').execFileSync('git', ['show', '17b32b3:index.html'], {cwd:path.join(__dirname, '..'),encoding:'utf8'});
function fn(name) {
  const start = html.indexOf('  function ' + name + '(');
  assert(start >= 0, name);
  const end = html.indexOf('\n  }', start);
  return html.slice(start, end + 4);
}
function run(names, state, code) {
  const context = vm.createContext(state);
  vm.runInContext(names.map(fn).join('\n'), context);
  return vm.runInContext(code, context);
}
const results = [];
const delay = run(['qTime'], {ctx:{currentTime:1.001}, quantOn:true, gridAnchor:1, bpm:102}, 'qTime() - ctx.currentTime');
assert(delay > .14);
results.push({check:'One-shot grid delay at 102 BPM', observedMs:delay * 1000});
const phase = run(['qTime'], {ctx:{currentTime:5.01}, quantOn:true, gridAnchor:1, bpm:130, nextTime:5.125}, 'nextTime - qTime()');
assert(Math.abs(phase) > .08);
results.push({check:'After 120 -> 130 BPM, retained sequencer boundary vs recalculated manual grid', differenceMs:phase * 1000});
const roll = run(['release'], {armed:false, mode:'synth', bank:()=>({modeCol:true}), djMode:2, rollLayer:0, COLS:5}, 'release(0,0); rollLayer');
assert.equal(roll, 0);
results.push({check:'Release roll after changing to sample mode', remainingRollLayer:roll});
const panic = run(['panicAll'], {active:[0,0,0,0], pending:[], rollLayer:0, stopSeq(){}, syncLights(){}}, 'panicAll(); rollLayer');
assert.equal(panic,0);
results.push({check:'Panic retains roll state', remainingRollLayer:panic});
const scheduled = [];
run(['tick','spb'], {playing:true, nextTime:1, ctx:{currentTime:2}, bpm:120, step:0, absStep:0, scheduleStep:(st,t)=>scheduled.push(t)}, 'tick()');
assert.equal(scheduled.filter(t=>t<2).length,8);
results.push({check:'Scheduler after a 1-second gap', pastEvents:scheduled.filter(t=>t<2).length, totalEvents:scheduled.length});
const keyStart = html.indexOf('  var KEYROWS = [');
const keyEnd = html.indexOf('\n  ];',keyStart)+5;
const listenerStart = html.indexOf('  var KEYMAP = {};');
const listenerEnd = html.indexOf('\n  window.addEventListener("resize"',listenerStart);
const handlers = {}, pressed = [];
const keyContext = vm.createContext({document:{addEventListener:(name,cb)=>handlers[name]=cb}, ROWS_N:8, COLS:8, mode:'synth', padAt:()=>null, press:(r,c)=>pressed.push([r,c]), release(){}});
vm.runInContext(html.slice(keyStart,keyEnd)+'\n'+html.slice(listenerStart,listenerEnd),keyContext);
handlers.keydown({repeat:false,target:{tagName:'BODY'},code:'Digit1',key:'!',shiftKey:true,preventDefault(){}});
assert.equal(pressed.length,0);
handlers.keydown({repeat:false,target:{tagName:'BODY'},code:'Digit1',key:'1',shiftKey:false,preventDefault(){}});
assert.equal(pressed.length,1);
results.push({check:'Standard Shift+1 key=! misses percussion mapping; unshifted 1 works', shiftedHits:0, unshiftedHits:1});
console.log(JSON.stringify({scope:'Extracted production functions with mocked surrounding state; no acoustic measurements', reproduced:results},null,2));
