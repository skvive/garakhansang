(()=>{'use strict';
const $=(q)=>document.querySelector(q);const sel=$('#recipe-selector'),zone=$('#recipe-dropzone'),inp=$('#recipe-file'),old=$('#existing-image'),preview=$('#uploaded-image'),empty=$('#preview-empty'),status=$('#recipe-image-status'),save=$('#download-webp');let current=null,url=null;
const setStatus=(text)=>{status.textContent=text};
function updateOriginal(){old.src='../assets/images/recipes/'+sel.value+'.webp';if(current){current=null;preview.hidden=true;empty.hidden=false;save.disabled=true;inp.value='';setStatus('레시피를 바꾸었습니다. 새 이미지를 선택하세요.')}}
sel.addEventListener('change',updateOriginal);
zone.addEventListener('click',()=>inp.click());zone.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inp.click()}});
function setFile(file){
 if(!file){return}if(!['image/jpeg','image/png','image/webp'].includes(file.type)){setStatus('지원하지 않는 형식입니다. JPG/PNG/WebP만 사용하세요.');return}
 if(file.size>10*1024*1024||file.size<=0){setStatus('파일 크기는 10MB 이하이어야 합니다.');return}
 const img=new Image();let temp=URL.createObjectURL(file);img.onload=()=>{if(img.naturalWidth<320||img.naturalHeight<240){setStatus('이미지 크기는 최소 320×240 이상이어야 합니다.');URL.revokeObjectURL(temp);return;}if(url)URL.revokeObjectURL(url);url=temp;preview.src=url;preview.hidden=false;empty.hidden=true;current=file;save.disabled=false;setStatus(sel.options[sel.selectedIndex].text+' · '+img.naturalWidth+'×'+img.naturalHeight+' · WebP 다운로드 준비 완료');};img.onerror=()=>{URL.revokeObjectURL(temp);setStatus('파일을 이미지로 읽지 못했습니다.')};img.src=temp;
}
inp.addEventListener('change',()=>setFile(inp.files[0]));
zone.addEventListener('dragenter',e=>{e.preventDefault();zone.classList.add('is-dragover')});
zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('is-dragover');e.dataTransfer.dropEffect='copy'});
zone.addEventListener('dragleave',e=>{if(!zone.contains(e.relatedTarget))zone.classList.remove('is-dragover')});
zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('is-dragover');setFile(e.dataTransfer.files[0])});
save.addEventListener('click',()=>{if(!current||!url)return;const img=new Image();img.onload=()=>{let c=document.createElement('canvas');c.width=960;c.height=720;let ctx=c.getContext('2d');if(!ctx){setStatus('브라우저에서 이미지 변환을 지원하지 않습니다.');return;}let scale=Math.max(960/img.width,720/img.height);let w=img.width*scale,h=img.height*scale;ctx.drawImage(img,(960-w)/2,(720-h)/2,w,h);c.toBlob(blob=>{if(!blob){setStatus('변환에 실패했습니다.');return;}const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download=sel.value+'.webp';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),15000);setStatus(a.download+' 다운로드 요청 완료 · 파일을 사이트 이미지 폴더에 직접 저장해야 반영됩니다.')},'image/webp',.88)};img.onerror=()=>setStatus('변환할 이미지를 불러오지 못했습니다.');img.src=url});
window.addEventListener('pagehide',()=>{if(url)URL.revokeObjectURL(url)});
})();