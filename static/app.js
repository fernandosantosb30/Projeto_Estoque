document.querySelectorAll('.sidebar nav a').forEach(a=>{if(a.pathname===location.pathname)a.classList.add('current')});
document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>window.print()));
document.querySelectorAll('[data-scan]').forEach(button=>button.addEventListener('click',async()=>{
 const box=button.closest('[data-scanner]'), input=box.querySelector('input'), status=box.querySelector('[role=status]'),video=box.querySelector('video');
 if(!window.BarcodeDetector||!navigator.mediaDevices){status.textContent='Leitura automática indisponível neste navegador. Digite o código impresso na etiqueta.';return;}
 let stream;
 try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});video.srcObject=stream;video.hidden=false;await video.play();button.disabled=true;
 const detector=new BarcodeDetector({formats:['qr_code']});let attempts=0;
 const tick=async()=>{try{const codes=await detector.detect(video);if(codes.length){input.value=codes[0].rawValue;stop();input.dispatchEvent(new Event('change'));return;}if(++attempts>120){status.textContent='Tempo encerrado. Tente novamente ou digite o código.';stop();return;}window.setTimeout(tick,250);}catch(e){stop();status.textContent='Não foi possível ler. Use o código manual.';}};
 const stop=()=>{stream.getTracks().forEach(t=>t.stop());video.hidden=true;button.disabled=false;};window.addEventListener('pagehide',stop,{once:true});tick();
 }catch(e){if(stream)stream.getTracks().forEach(t=>t.stop());status.textContent='Câmera indisponível. Use HTTPS e autorize a câmera, ou digite o código.';button.disabled=false;}
}));
document.querySelectorAll('[data-find-code]').forEach(input=>{
 const find=()=>{const raw=input.value.trim(), rows=[...document.querySelectorAll('[data-code]')];const found=rows.find(r=>r.dataset.code.toLowerCase()===raw.toLowerCase()||raw.endsWith('/equipamento/'+r.dataset.token+'/'));const status=input.closest('[data-scanner]').querySelector('[role=status]');if(found){found.open=true;found.scrollIntoView({behavior:'smooth',block:'center'});status.textContent='Item localizado. Confira a quantidade e registre a operação abaixo.';}else{status.textContent='Item não encontrado nesta lista do evento.';}};
 input.addEventListener('change',find);
 input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();find();}});
 input.closest('[data-scanner]').querySelector('[data-find-button]').addEventListener('click',find);
});
