const fs=require('fs');const path=require('path');const {PNG}=require('pngjs');
const png=PNG.sync.read(fs.readFileSync('C:/Users/eminb/Projects/investhome-os/apps/web/public/brand/logos/investhome-logo-color.png'));
const {width,height,data}=png; const A=16;
let minX=width,minY=height,maxX=-1,maxY=-1;
for(let y=0;y<height;y++)for(let x=0;x<=1130;x++){
  const a=data[(width*y+x)*4+3]; if(a>A){if(x<minX)minX=x;if(y<minY)minY=y;if(x>maxX)maxX=x;if(y>maxY)maxY=y;}
}
console.log('tight icon', {minX,minY,maxX,maxY, w:maxX-minX+1,h:maxY-minY+1});
console.log('pct', {left:minX/width*100,top:minY/height*100,right:(maxX+1)/width*100,bottom:(maxY+1)/height*100});
