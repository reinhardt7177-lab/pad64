const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
function extract(name) {
  const start = html.indexOf('  function ' + name + '(');
  assert(start >= 0, name);
  const end = html.indexOf('\n  }', start);
  return html.slice(start, end + 4);
}
function context(names, values) {
  const ctx = vm.createContext(values);
  vm.runInContext(names.map(extract).join('\n'), ctx);
  return ctx;
}
function clock(time = 0) {
  return {ctx:{currentTime:time}, quantOn:false, quantSteps:1, bpm:120,
    tempoSegments:[{at:0,anchor:1,bpm:120}], nextTime:1, playing:false,
    absStep:0, step:0, visQ:[], gridAnchor:1, bpmEl:{},bpmV:{},bpmChip:{}};
}
test('production JavaScript parses', () => new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]));
test('one-shots have no default quantization wait', () => {
  const c=context(['qTime','tempoAt'],clock(1.001));
  assert.equal(c.qTime(),1.001);
});
test('manual hits share the tempo boundary, including repeated changes', () => {
  const c=context(['qTime','tempoAt','spb','setTempo','tick'], {...clock(5.01),playing:true,nextTime:5.125,absStep:33,scheduleStep(){}});
  c.quantOn=true; c.setTempo(130);
  assert.equal(c.qTime(),5.125);
  const firstBoundary=c.tempoSegments.at(-1).at;
  c.ctx.currentTime=firstBoundary+.001;
  const firstNext=firstBoundary+60/130/4;
  assert(Math.abs(c.qTime()-firstNext)<1e-7);
  c.setTempo(150);
  c.ctx.currentTime=c.tempoSegments.at(-1).at+.001;
  assert(Math.abs(c.qTime()-(c.tempoSegments.at(-1).at+60/150/4))<1e-7);
});
test('1/8 quantization crosses a tempo change on an odd 16th step',()=>{
  const c=context(['qTime','tempoAt'], {...clock(1.49),quantOn:true,quantSteps:2,
    tempoSegments:[{at:0,anchor:1,bpm:120},{at:1.625,anchor:1.625-5*(60/130/4),bpm:130}]});
  assert.equal(c.qTime(),1.5);
  c.ctx.currentTime=1.51;
  assert(Math.abs(c.qTime()-(1.625+60/130/4))<1e-7);
});
test('one-second scheduler stall skips old notes without a burst', () => {
  const calls=[];
  const c=context(['tick','spb','tempoAt'],{...clock(2),playing:true,scheduleStep:(s,t)=>calls.push(t)});
  c.tick(); assert.deepEqual(calls,[2]); assert.equal(c.absStep,9);
});
test('long stalls across a tempo boundary remain phase-aligned',()=>{
  const calls=[];
  const c=context(['tick','spb','tempoAt'], {...clock(600),playing:true,
    tempoSegments:[{at:0,anchor:1,bpm:120},{at:2,anchor:1.2,bpm:150}],
    scheduleStep:(s,t)=>calls.push(t)});
  c.tick(); assert(calls.length<=2); assert(calls.every(t=>t>=599.995));
});
function inputs() {
  const heldInputs=new Map(), rollHolds=new Map();
  let stopped=0;
  const c=context(['releaseInput','releaseAllInputs','refreshRoll','setDJMode'], {
    heldInputs,rollHolds,rollLayer:-1,rollStep:4,touchMap:new Map(),pads:[],
    padAt:()=>null,releaseVoice:()=>stopped++,stopRec(){},paintPads(){},ctx:{currentTime:2},voices:new Map()});
  return {c,heldInputs,rollHolds,stopped:()=>stopped};
}
test('releasing one roll restores another held roll', () => {
  const {c,heldInputs,rollHolds}=inputs();
  heldInputs.set('a',{r:0,c:0}); heldInputs.set('b',{r:1,c:1});
  rollHolds.set('a',{row:0,step:1});rollHolds.set('b',{row:1,step:2});
  c.refreshRoll(); assert.equal(c.rollLayer,1);
  c.releaseInput('b');assert.equal(c.rollLayer,0);
  c.releaseInput('a');assert.equal(c.rollLayer,-1);
});
test('mode changes clear rolls and held notes before keyup',()=>{
  const {c,heldInputs,rollHolds,stopped}=inputs();
  heldInputs.set('a',{r:0,c:0,gated:true,voice:{}});rollHolds.set('a',{row:0,step:1});
  c.setDJMode(2); c.releaseInput('a');
  assert.equal(c.rollLayer,-1);assert.equal(heldInputs.size,0);assert.equal(stopped(),1);
});
test('pack note release uses captured voice, not the new chain or replacement voice',()=>{
  const {c,heldInputs}=inputs();let stops=0;
  const oldVoice={inf:true,src:{stop(){stops++;}}}, replacement={};
  heldInputs.set('a',{r:0,c:0,packKey:'1:1:1',packVoice:oldVoice});
  c.voices.set('1:1:1',replacement);c.releaseInput('a');
  assert.equal(stops,1);assert.equal(c.voices.get('1:1:1'),replacement);
});
test('Shift+Digit1 triggers row 5 and keyup is independent of current Shift',()=>{
  const handlers={},hits=[],releases=[];
  const start=html.indexOf('  var KEYMAP = {};'),end=html.indexOf('  window.addEventListener("resize", fitGrid);',start);
  const c=vm.createContext({document:{addEventListener:(n,f)=>handlers[n]=f},window:{addEventListener(){}},
    mode:'synth',ROWS_N:8,COLS:8,padAt:()=>null,press:(...a)=>hits.push(a),releaseInput:id=>releases.push(id),
    releaseAllInputs(){},sheet:{classList:{contains:()=>false}},edEl:{hidden:true}});
  vm.runInContext(html.slice(start,end),c);
  handlers.keydown({code:'Digit1',key:'!',shiftKey:true,target:{tagName:'BODY'},preventDefault(){}});
  handlers.keyup({code:'ShiftLeft',shiftKey:false});
  handlers.keyup({code:'Digit1',key:'1',shiftKey:false});
  assert.deepEqual(hits[0],[4,0,1,'key:Digit1']);assert(releases.includes('key:Digit1'));
  handlers.keydown({code:'KeyQ',ctrlKey:true,target:{tagName:'BODY'}}); assert.equal(hits.length,1);
});
test('source beat grid uses source BPM and downbeat, clamping to duration',()=>{
  const fields={sourcebpm:{value:100},sourcebeat:{value:.3}};
  const c=context(['snapT','sourceTempo','sourceAnchor'],{snapEl:{checked:true},edBuf:{duration:2},bpm:140,$:id=>fields[id]});
  assert(Math.abs(c.snapT(.94)-.9)<1e-9);assert.equal(c.snapT(2.4),2);
});
test('trim fade removes boundary discontinuity while preserving the interior',()=>{
  const make=(n,len,sr)=>({sampleRate:sr,length:len,numberOfChannels:n,data:Array.from({length:n},()=>new Float32Array(len)),getChannelData(c){return this.data[c];}});
  const c=context(['trimBuffer'],{ctx:{createBuffer:make}});
  const original=make(2,1000,1000); original.data.forEach(d=>d.fill(.8));
  const faded=c.trimBuffer(original,0,1,true), raw=c.trimBuffer(original,0,1,false);
  assert.equal(faded.data[0][0],0);assert.equal(faded.data[1][999],0);
  assert.equal(faded.data[0][100],original.data[0][100]);assert.equal(raw.data[0][0],original.data[0][0]);
  assert.equal(c.trimBuffer(original,100,101,true).length,1);
});
