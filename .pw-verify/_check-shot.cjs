const fs=require('fs');const {PNG}=require('pngjs');
const p='C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/brand-hotfix/sidebar-collapsed.png';
const png=PNG.sync.read(fs.readFileSync(p));
// sample top-left 80x80 where brand sits
let nonTransparent=0;
for(let y=8;y<48;y++)for(let x=8;x<48;x++){
  if(png.data[(png.width*y+x)*4+3]>20) nonTransparent++;
}
console.log('screenshot', png.width+'x'+png.height, 'brand area opaque px sample', nonTransparent);
