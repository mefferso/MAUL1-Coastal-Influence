const fs=require('fs');const vm=require('vm');const zlib=require('zlib');const assert=require('assert/strict');
const elements=new Map();const callbacks={};
function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',innerHTML:'',removeAllListeners(){},on(){}});return elements.get(id)}
const window={DecompressionStream:global.DecompressionStream,addEventListener:(name,callback)=>callbacks[name]=callback};
const Plotly={react:async()=>{},relayout:()=>{}};
const L={map:()=>({setView(){return this}}),tileLayer:()=>({addTo(){}}),marker:()=>({addTo(){return this},bindPopup(){}})};
const fetch=async(path)=>({ok:true,json:async()=>JSON.parse(fs.readFileSync('site/'+path,'utf8')),body:new ReadableStream({start(controller){controller.enqueue(fs.readFileSync('site/'+path));controller.close()}})});
assert.match(fs.readFileSync('site/index.html','utf8'),/Experimental event onset/);
const context=vm.createContext({DecompressionStream:global.DecompressionStream,window,document:{getElementById:element},fetch,Plotly,L,Date,Promise,Response,console});vm.runInContext(fs.readFileSync('site/app.js','utf8'),context);
callbacks.load();
setTimeout(()=>{assert.match(element('status').textContent,/Archive generated/);assert.match(element('summary').textContent,/real observations/);assert.match(element('coverage').innerHTML,/DENL1/);assert.equal(vm.runInContext("until([{time:'2020-01-01T00:00:00Z'},{time:'2020-01-01T01:00:00Z'}], '2020-01-01T00:00:00Z').length",context),1);console.log('Site loads compressed real event and renders research diagnostics')},1500);
