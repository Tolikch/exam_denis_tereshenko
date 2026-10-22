const canvas = document.querySelector('#matrix-canvas');
const context = canvas.getContext('2d');
const glyphs = '01アイウエオカキクケコサシスセソABCDEFGHIJKLMNOPQRSTUVWXYZ';
let columns = [];
function resizeMatrix(){ canvas.width = canvas.clientWidth; canvas.height = canvas.clientHeight; columns = Array(Math.floor(canvas.width / 15)).fill(1); }
function drawMatrix(){ context.fillStyle = 'rgba(2,10,4,.13)'; context.fillRect(0,0,canvas.width,canvas.height); context.fillStyle = '#55ff82'; context.font = '13px monospace'; columns.forEach((drop,index)=>{context.fillText(glyphs[Math.floor(Math.random()*glyphs.length)],index*15,drop*15); if(drop*15>canvas.height&&Math.random()>.975)columns[index]=0; columns[index]++;}); requestAnimationFrame(drawMatrix); }
resizeMatrix(); window.addEventListener('resize',resizeMatrix); drawMatrix();
const button=document.querySelector('#boot-button'), stages=[...document.querySelectorAll('#boot-stages li')], bar=document.querySelector('#boot-progress'), percent=document.querySelector('#boot-percent');
button.onclick=()=>{button.disabled=true;button.textContent='ПОДКЛЮЧЕНИЕ АКТИВНО...';stages.forEach((stage,i)=>setTimeout(()=>{if(i)stages[i-1].classList.replace('active','done');stage.classList.add('active');const progress=(i+1)*20;bar.style.width=progress+'%';percent.textContent=String(progress).padStart(2,'0')+'%';if(i===stages.length-1)setTimeout(()=>location.href='/login',900)},i*850));};
