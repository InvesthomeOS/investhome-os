const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const LOGOS_DIR = path.resolve('C:/Users/eminb/Projects/investhome-os/apps/web/public/brand/logos');
const ALPHA = 16;
const png = PNG.sync.read(fs.readFileSync(path.join(LOGOS_DIR,'investhome-logo-color.png')));
const {width,height,data}=png;
const cols=[];
for(let x=0;x<Math.floor(width*0.25);x++){
  let c=0; for(let y=0;y<height;y++) if(data[(width*y+x)*4+3]>ALPHA) c++;
  cols.push({x, fill: c/height});
}
// print low-fill columns
const lows = cols.filter(c=>c.fill<0.01).slice(0,30);
console.log('first empty-ish columns', lows.slice(0,15));
// find widest run of low columns after x>200
let bestRun={start:0,len:0,curStart:null,curLen:0};
for(const c of cols){
  if(c.x<150) continue;
  if(c.fill<0.008){
    if(c.curStart==null) { /* */ }
  }
}
let runStart=null, runLen=0, best={start:0,len:0};
for(const c of cols){
  if(c.x<150){runStart=null;runLen=0;continue;}
  if(c.fill<0.008){
    if(runStart==null) runStart=c.x;
    runLen++;
  } else {
    if(runLen>best.len) best={start:runStart,len:runLen};
    runStart=null; runLen=0;
  }
}
if(runLen>best.len) best={start:runStart,len:runLen};
console.log('best low-fill run after x150', best);
console.log('sample cols 900-1200', cols.filter(c=>c.x>=900&&c.x<=1200).map(c=>`${c.x}:${c.fill.toFixed(3)}`).join(' '));
