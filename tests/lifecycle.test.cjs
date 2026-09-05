const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
function extract(name){
  let start=html.indexOf('  function '+name+'(');
  if(start<0)start=html.indexOf('  async function '+name+'(');
  assert(start>=0,name);
  return html.slice(start,html.indexOf('\n  }',start)+4);
}
function context(names,state){const c=vm.createContext(state);vm.runInContext(names.map(extract).join('\n'),c);return c;}
test('gliding from an FX pad across the DJ stop column never activates stop',()=>{
  const hits=[];let move;
  const prev={dataset:{r:'4',c:'3'}},stop={dataset:{r:'4',c:'4'},classList:{add(){}}};
  const a=html.indexOf('  window.addEventListener("pointermove"',html.indexOf('  var touchMap'));
  const b=html.indexOf('  function endPointer',a);
  const c=vm.createContext({window:{addEventListener:(name,cb)=>move=cb},touchMap:new Map([[1,prev]]),
    padFromPoint:()=>stop,release(){},glideEl:{checked:true},armed:false,mode:'synth',bank:()=>({modeCol:true}),
    COLS:5,djMode:2,press:(r,col)=>hits.push([r,col])});
  if(html.includes('  function canGlide('))vm.runInContext(extract('canGlide'),c);
  vm.runInContext(html.slice(a,b),c);move({pointerId:1,clientX:0,clientY:0});
  assert.deepEqual(hits,[]);
});
test('old preview completion cannot stop a newly restarted preview',()=>{
  const sources=[];let click;
  const c=context(['stopPreview'],{edSrc:null,edBuf:{},ctx:{currentTime:0},edA:0,edB:1,
    $:id=>id==='editplay'?{dataset:{},addEventListener:(n,f)=>click=f}:{checked:true},
    initAudio:()=>true,wake(){},bufferSource:()=>{const s={start(){},stop(){s.stopped=true;}};sources.push(s);return s;},
    trimBuffer:()=>({}),playSound:(p,v,f)=>f(),connectVoice(){}});
  const a=html.indexOf('  $("editplay").addEventListener');
  const b=html.indexOf('  function trimBuffer',a);
  vm.runInContext(html.slice(a,b),c);
  click();click();click();sources[0].onended();
  assert.equal(sources[1].stopped,undefined);assert.equal(c.edSrc,sources[1]);
});
test('stopping a wormhole sample does not change pages; natural completion still does',()=>{
  const srcs=[],changes=[];
  const c=context(['packTrigger','stopVoiceAt'],{pack:{map:new Map([['1:1:1',{i:0,items:[{path:'a',loop:1,worm:2}]}]])},
    mode:'pack',decoded:new Map([['a',{}]]),voices:new Map(),ctx:{createGain:()=>({gain:{setTargetAtTime(){}},connect(){}})},
    bufferSource:()=>{const s={start(){},stop(){},connect(){}};srcs.push(s);return s;},connectVoice(){},setChain:n=>changes.push(n)});
  c.packTrigger(1,1,1,0);c.stopVoiceAt('1:1:1',.1);srcs[0].onended();assert.deepEqual(changes,[]);
  c.packTrigger(1,1,1,1);srcs[1].onended();assert.deepEqual(changes,[2]);
});
function board(){return {title:'Fixture',producer:'Test',x:8,y:8,chains:2,map:new Map(),
  auto:null,leds:new Map([['1:1:1',{loop:2,ev:[{at:0,k:'on',x:1,y:1,color:'#FF0000'},{at:100,k:'off',x:1,y:1}]}]])};}
test('board snapshots preserve lightshow data independently of future edits',()=>{
  const p=board(),c=context(['snapshot'],{pack:p,userBlobs:new Map(),packZipBlob:null,flipY:false});
  const saved=c.snapshot('fixture','Fixture');
  assert(saved.leds,'lightshow missing in snapshot');
  p.leds.get('1:1:1').ev[0].color='#000000';
  assert.equal(saved.leds[0][1].ev[0].color,'#FF0000');
});
test('opening another board clears undo history and restores LEDs',async()=>{
  const p=board(),rec={name:'B',zip:null,user:[],map:[],meta:p,auto:null,leds:Array.from(p.leds)};
  const c=context(['restore','clearBoardHistory'],{initAudio:()=>true,stopAll(){},autoStop(){},stopAllLights(){},releaseAllInputs(){},
    decoded:new Map(),userBlobs:new Map(),undoStack:[['old board']],undoBtn:{disabled:false},
    $:()=>({}),setMode(){},showMeta(){},predecode(){},packnote:{dataset:{}},logLines:[],readPackLights:async()=>new Map(),pack:null});
  await c.restore(rec);
  assert.equal(c.undoStack.length,0);assert.equal(c.undoBtn.disabled,true);
  assert.equal(c.pack.leds.get('1:1:1').ev[0].color,'#FF0000');
});

test('failed board restore preserves the current audio cache and user recordings',async()=>{
  const cache=new Map([['a',{}]]),blobs=new Map([['a',{}]]),p=board();
  const c=context(['restore'],{initAudio:()=>true,stopAll(){},autoStop(){},readZip(){},pack:p,decoded:cache,userBlobs:blobs});
  await assert.rejects(c.restore({zip:{arrayBuffer:async()=>{throw new Error('unreadable ZIP');}}}),/unreadable ZIP/);
  assert.equal(c.pack,p);assert.equal(c.decoded,cache);assert.equal(c.userBlobs,blobs);
});
test('decode completion from an old board cannot contaminate the new cache',async()=>{
  let finish,started;const began=new Promise(r=>started=r);const oldPack={};const oldCache=new Map();
  const c=context(['decodeOne'],{pack:oldPack,decoded:oldCache,userBlobs:new Map([['a',{arrayBuffer:async()=>new ArrayBuffer(4)}]]),
    ctx:{decodeAudioData:()=>new Promise(r=>{finish=r;started();})},logLines:[],renderLog(){}});
  const result=c.decodeOne('a');await began;
  const next=new Map();c.pack={};c.decoded=next;finish({name:'old audio'});await result;
  assert.equal(next.has('a'),false);
});

test('old decoder pump cannot consume a new queue or replace its progress',async()=>{
  let finish;const c=context(['pumpDecode'],{initAudio:()=>true,pack:{},decodeQueue:['old'],decoding:true,
    decodeOne:()=>new Promise(r=>finish=r),decnote:{textContent:'new progress'}});
  const pending=c.pumpDecode(),next=['new'];c.pack={};c.decodeQueue=next;finish();await pending;
  assert.deepEqual(next,['new']);assert.equal(c.decnote.textContent,'new progress');assert.equal(c.decoding,true);
});

test('file assignment finishing after a board switch cannot write into the new board',async()=>{
  let finish,started;const began=new Promise(r=>started=r);
  const c=context(['assignFiles'],{initAudio:()=>true,mode:'pack',pack:board(),chain:1,flipY:false,
    pushUndo(){},COLS:8,ROWS_N:8,ctx:{decodeAudioData:()=>new Promise(r=>{finish=r;started();})},
    decoded:new Map(),userBlobs:new Map(),recNote(){},logLines:[],renderLog(){}});
  const pending=c.assignFiles([{name:'a.wav',type:'audio/wav',arrayBuffer:async()=>new ArrayBuffer(4)}],0,0);
  await began;c.pack=board();finish({});await pending;
  assert.equal(c.pack.map.size,0);assert.equal(c.decoded.size,0);assert.equal(c.userBlobs.size,0);
});
