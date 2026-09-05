// Injected into the app's closure ONLY by tests/serve.cjs at /tests.
// Uses real browser Web Audio offline rendering. No microphone or audio output.
(async function runPerformanceChecks() {
  var results = [];
  var runtimeErrors = [];
  window.addEventListener('error', function (e) { runtimeErrors.push(e.message); });
  window.addEventListener('unhandledrejection', function (e) { runtimeErrors.push(String(e.reason)); });
  // Offline contexts start with startRendering(), not the live user-gesture resume.
  // Only that live activation boundary is bypassed; synthesis and routing are real.
  var liveWake = wake;
  wake = function () { if (!(ctx instanceof OfflineAudioContext)) liveWake(); };
  var output = document.createElement('pre');
  output.id = 'test-results';
  output.style.cssText = 'position:fixed;inset:0;overflow:auto;z-index:100;background:#10151c;color:white;padding:20px;white-space:pre-wrap;user-select:text';
  document.body.appendChild(output);
  function assert(value, message) { if (!value) throw new Error(message); }
  async function check(name, fn) {
    try { var metrics = await fn(); results.push({name:name,pass:true,metrics:metrics||null}); }
    catch (e) { results.push({name:name,pass:false,error:e.stack||String(e)}); }
    output.textContent = JSON.stringify(results, null, 2);
  }
  function offline(seconds) {
    playing=false;clearInterval(timer);clearInterval(apTimer);apOn=false;
    releaseAllInputs(); sourceNodes=new Set(); voices.clear();
    ctx=new OfflineAudioContext(2,Math.ceil(44100*seconds),44100);
    outGain=ctx.createGain(); outGain.gain.value=.8*OUTPUT_HEADROOM;outGain.connect(ctx.destination);
    buildMixGraph();
    noiseBuf=ctx.createBuffer(1,88200,44100);
    var data=noiseBuf.getChannelData(0),seed=7;
    for(var i=0;i<data.length;i++){seed=(Math.imul(seed,1664525)+1013904223)|0;data[i]=seed/2147483648;}
    tempoSegments=[{at:0,anchor:0,bpm:120}];bpm=120;quantOn=false;visQ=[];
    pending=[];pendingScene=null;active=[null,null,null,null,null,null,null,null];
    mode='synth'; bankIdx=0;COLS=8;ROWS_N=8;djMode=0;rollLayer=-1;
    return ctx;
  }
  function metrics(buf,start,end) {
    var sum=0,peak=0,n=0;
    for(var c=0;c<buf.numberOfChannels;c++){
      var data=buf.getChannelData(c),from=Math.floor((start||0)*buf.sampleRate),to=Math.min(data.length,Math.ceil((end||buf.duration)*buf.sampleRate));
      for(var i=from;i<to;i++){assert(Number.isFinite(data[i]),'non-finite audio');peak=Math.max(peak,Math.abs(data[i]));sum+=data[i]*data[i];n++;}
    }
    return {peak:peak,rms:Math.sqrt(sum/Math.max(1,n)),peakDbfs:peak?20*Math.log10(peak):null};
  }
  await check('DJ modes, labels, stop color, and all eight loop slots',function(){
    offline(1);setBank(2);
    assert(pads.length===25,'DJ pad count');
    setDJMode(2);assert(padAt(1,0).getAttribute('aria-label')==='타악기 열린햇','sample label');
    assert(padAt(4,4).getAttribute('aria-label')==='모든 소리 정지','stop label');
    assert(getComputedStyle(document.documentElement).getPropertyValue('--f-stop').trim()!=='','stop color');
    setDJMode(0);djPage=1;paintPads();assert(capFor(0,0)==='빌드','pattern 5 visible');
    playing=true;press(0,0,1,'test:loop');releaseInput('test:loop');
    assert(pending[0].col===4,'pattern 5 selectable');playing=false;pending=[];
    return {pads:pads.length,fifthPattern:capFor(0,0)};
  });
  await check('held rolls clear on mode switch and panic/restart',function(){
    offline(1);setBank(2);setDJMode(1);playing=true;
    press(0,0,1,'test:a');press(1,1,1,'test:b');assert(rollLayer===1,'last held');
    releaseInput('test:b');assert(rollLayer===0,'previous held restored');
    setDJMode(2);releaseInput('test:a');assert(rollLayer===-1,'mode change release');
    setDJMode(1);press(0,0,1,'test:c');panicAll();
    assert(rollLayer===-1&&heldInputs.size===0,'panic release');
    start();assert(rollLayer===-1,'no roll on restart');stopSeq();
  });
  await check('DOM keyboard events: shifted number and early Shift release',function(){
    offline(1);setBank(0);
    document.dispatchEvent(new KeyboardEvent('keydown',{code:'Digit1',key:'!',shiftKey:true,bubbles:true}));
    assert(heldInputs.has('key:Digit1'),'Shift+1 captured');assert(sourceNodes.size>0,'drum scheduled');
    document.dispatchEvent(new KeyboardEvent('keyup',{code:'ShiftLeft',key:'Shift',bubbles:true}));
    document.dispatchEvent(new KeyboardEvent('keyup',{code:'Digit1',key:'1',bubbles:true}));
    assert(!heldInputs.has('key:Digit1'),'release despite modifier change');
    silenceAudio();
  });
  await check('scene changes all four layers on a bar boundary',function(){
    offline(1);setBank(2);playing=true;queueScene(3);
    scheduleStep(15,.1,15);assert(active[0]===null,'no early scene');
    scheduleStep(16,.2,16);assert(active.slice(0,4).join(',')==='0,0,0,1','scene layers');
    assert(pendingScene===null,'scene consumed');playing=false;
  });
  await check('panic silences current sound, reverb, and future sources',async function(){
    var ac=offline(1.5);
    playSound('chords',1,function(){superChord([57,60,64],.03,1,1);});
    playSound('fx',1,function(){airHorn(.8);});
    var paused=ac.suspend(.25).then(function(){panicAll();return ac.resume();});
    var rendered=ac.startRendering();await paused;var buf=await rendered;
    var before=metrics(buf,.08,.2),after=metrics(buf,.29,1.5);
    assert(before.peak>.001,'audio existed before stop');assert(after.peak<1e-6,'audio remains after panic');
    return {before:before,after:after};
  });
  await check('new notes after panic do not revive old reverb',async function(){
    var ac=offline(1.5);
    playSound('chords',1,function(){superChord([57,60,64],.02,1,1);});
    var paused=ac.suspend(.25).then(function(){panicAll();playSound('drums',1,function(){kick(.8,1);});return ac.resume();});
    var render=ac.startRendering();await paused;var buf=await render;
    var gap=metrics(buf,.3,.7),restart=metrics(buf,.8,1.1);
    assert(gap.peak<1e-6,'old tail revived');assert(restart.peak>.001,'new graph silent');return {gap:gap,restart:restart};
  });
  await check('note mode gate releases before its sustained duration',async function(){
    var ac=offline(1);setBank(2);setDJMode(3);gateNotes=true;press(0,0,1,'test:gate');
    var paused=ac.suspend(.2).then(function(){releaseInput('test:gate');return ac.resume();});
    var render=ac.startRendering();await paused;var buf=await render;
    var head=metrics(buf,.04,.15),tail=metrics(buf,.7,1);
    assert(head.peak>.001,'held note silent');assert(tail.rms<head.rms*.2,'held note did not release');
    return {head:head,tail:tail};
  });
  await check('velocity controls synthesized output strength',async function(){
    var ac=offline(1);playSound('bass',.2,function(){sub808(33,.05,.3,1);});var quiet=metrics(await ac.startRendering(),.05,.4);
    ac=offline(1);playSound('bass',1,function(){sub808(33,.05,.3,1);});var loud=metrics(await ac.startRendering(),.05,.4);
    assert(loud.rms>quiet.rms*1.3,'velocity ignored');return {quiet:quiet,loud:loud};
  });
  await check('part mute includes wet signal',async function(){
    mixSettings.chords.level=0;var ac=offline(1);
    playSound('chords',1,function(){superChord([57,60,64],.1,.4,1);});
    var m=metrics(await ac.startRendering());mixSettings.chords.level=.75;
    assert(m.peak<1e-7,'muted part leaks into output');return m;
  });
  await check('full DJ arrangement plus repeated FX stays finite below full scale',async function(){
    var ac=offline(5);setBank(2);active=[0,0,0,0,null];pumpAmt=.75;
    for(var s=0;s<32;s++)scheduleStep(s,.05+s*.125,s);
    for(var f=0;f<6;f++)playSound('fx',1,function(){airHorn(.05+f*.35);});
    var m=metrics(await ac.startRendering());assert(m.peak<1,'output exceeds sample full scale');return m;
  });
  await check('editor source grid and stereo boundary fade',function(){
    offline(1);var b=ctx.createBuffer(2,44100,44100);b.getChannelData(0).fill(.5);b.getChannelData(1).fill(-.5);
    openEditor(b,'fixture.wav',{r:0,c:0});$('sourcebpm').value=120;$('sourcebeat').value=.1;
    assert(Math.abs(snapT(.59)-.6)<1e-7,'source grid');
    var cut=trimBuffer(b,.1,.6,true);
    assert(cut.length===22050,'trim length');assert(cut.getChannelData(0)[0]===0,'fade in');
    assert(cut.getChannelData(1)[cut.length-1]===0,'fade out');
    closeEditor();
  });
  playing=false;clearInterval(timer);clearInterval(apTimer);releaseAllInputs();
  await new Promise(function(resolve){setTimeout(resolve,0);});
  if (runtimeErrors.length) results.push({name:'uncaught browser errors',pass:false,error:runtimeErrors.join('\n')});
  var report={passed:results.filter(function(r){return r.pass;}).length,total:results.length,results:results};
  output.textContent=JSON.stringify(report,null,2);output.dataset.complete='true';
  document.title=report.passed===report.total?'PASS · 패드64 검증':'FAIL · 패드64 검증';
  await fetch('/results',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report)});
})();
