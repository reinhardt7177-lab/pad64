// Only exposes the app and test harness, never .env or repository metadata.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..');
const port=Number(process.env.PAD64_TEST_PORT||8877);
const server=http.createServer((req,res)=>{
  if(req.method==='POST'&&req.url==='/results'){
    let text=''; req.on('data',chunk=>{text+=chunk;if(text.length>100000)req.destroy();});
    req.on('end',()=>{try{const data=JSON.parse(text);fs.mkdirSync(path.join(__dirname,'artifacts'),{recursive:true});fs.writeFileSync(path.join(__dirname,'artifacts/results.json'),JSON.stringify(data,null,2));res.end('saved');}catch(e){res.writeHead(400);res.end('invalid');}});return;
  }
  if(req.method!=='GET'||!['/','/tests'].includes(req.url)){res.writeHead(404);res.end();return;}
  let html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  if(req.url==='/tests'){
    const test=fs.readFileSync(path.join(__dirname,'performance.browser.js'),'utf8');
    html=html.replace('\n})();', '\n'+test+'\n})();');
  }
  res.setHeader('Content-Type','text/html; charset=utf-8');res.setHeader('Cache-Control','no-store');res.end(html);
});
server.listen(port,'127.0.0.1',()=>console.log(`App http://127.0.0.1:${port}/ — tests /tests`));
