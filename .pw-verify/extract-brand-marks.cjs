const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const LOGOS_DIR = path.resolve('C:/Users/eminb/Projects/investhome-os/apps/web/public/brand/logos');
const ALPHA_THRESHOLD = 16;
function loadPng(p){return PNG.sync.read(fs.readFileSync(p));}
function findIconRightEdge(png){
  const {width,height,data}=png; const scanTo=Math.floor(width*0.25);
  let runStart=null,best={start:0,len:0},runLen=0;
  for(let x=150;x<scanTo;x++){
    let fill=0; for(let y=0;y<height;y++) if(data[(width*y+x)*4+3]>ALPHA_THRESHOLD) fill++;
    const ratio=fill/height;
    if(ratio<0.008){ if(runStart==null) runStart=x; runLen++; }
    else { if(runLen>best.len) best={start:runStart,len:runLen}; runStart=null; runLen=0; }
  }
  if(runLen>best.len) best={start:runStart,len:runLen};
  return best.len>=8?best.start-1:Math.floor(width*0.12);
}
function iconBounds(png,rightEdge){
  const {width,height,data}=png; let minX=width,minY=height,maxX=-1,maxY=-1;
  for(let y=0;y<height;y++)for(let x=0;x<=rightEdge;x++){
    const a=data[(width*y+x)*4+3]; if(a>ALPHA_THRESHOLD){ if(x<minX)minX=x;if(y<minY)minY=y;if(x>maxX)maxX=x;if(y>maxY)maxY=y; }
  }
  return {minX,minY,maxX,maxY};
}
function squareCropForIcon(png, icon, paddingRatio=0.06){
  const markW=icon.maxX-icon.minX+1; const markH=icon.maxY-icon.minY+1;
  const base=markW; // width-limited square (icon column before wordmark)
  const pad=Math.max(2,Math.round(base*paddingRatio));
  const size=base+pad*2;
  const cx=(icon.minX+icon.maxX)/2; const cy=(icon.minY+icon.maxY)/2;
  let left=Math.round(cx-size/2); let top=Math.round(cy-size/2);
  left=Math.max(0,left); top=Math.max(0,top);
  if(left+size>png.width) left=Math.max(0,png.width-size);
  if(top+size>png.height) top=Math.max(0,png.height-size);
  return {left,top,size};
}
function extractCrop(png,crop){
  const out=new PNG({width:crop.size,height:crop.size});
  for(let y=0;y<crop.size;y++)for(let x=0;x<crop.size;x++){
    const sx=crop.left+x,sy=crop.top+y,si=(png.width*sy+sx)<<2,di=(crop.size*y+x)<<2;
    if(sx<png.width&&sy<png.height){out.data[di]=png.data[si];out.data[di+1]=png.data[si+1];out.data[di+2]=png.data[si+2];out.data[di+3]=png.data[si+3];}
  }
  return out;
}
const variants=[
 ['investhome-logo-color.png','investhome-mark-color.png'],
 ['investhome-logo-black.png','investhome-mark-black.png'],
 ['investhome-logo-white.png','investhome-mark-white.png'],
];
for(const [srcName,outName] of variants){
  const src=loadPng(path.join(LOGOS_DIR,srcName));
  const edge=findIconRightEdge(src); const icon=iconBounds(src,edge); const crop=squareCropForIcon(src,icon);
  fs.writeFileSync(path.join(LOGOS_DIR,outName),PNG.sync.write(extractCrop(src,crop)));
  console.log(outName, crop, 'edge', edge);
}
