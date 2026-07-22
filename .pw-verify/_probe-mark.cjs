const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const LOGOS_DIR = path.resolve('C:/Users/eminb/Projects/investhome-os/apps/web/public/brand/logos');
const ALPHA = 16;
function loadPng(p){return PNG.sync.read(fs.readFileSync(p));}
function boundsInRegion(png, x0, x1) {
  const {width,height,data}=png;
  let minX=width,minY=height,maxX=-1,maxY=-1;
  for(let y=0;y<height;y++) for(let x=x0;x<=x1;x++){
    const a=data[(width*y+x)*4+3];
    if(a>ALPHA){ if(x<minX)minX=x;if(y<minY)minY=y;if(x>maxX)maxX=x;if(y>maxY)maxY=y;}
  }
  return {minX,minY,maxX,maxY};
}
const png=loadPng(path.join(LOGOS_DIR,'investhome-logo-color.png'));
const edge=1130;
const b=boundsInRegion(png,0,edge);
console.log('icon region bounds', b);
console.log('pct', {
  left: b.minX/png.width*100,
  top: b.minY/png.height*100,
  right: (b.maxX+1)/png.width*100,
  bottom: (b.maxY+1)/png.height*100,
});
