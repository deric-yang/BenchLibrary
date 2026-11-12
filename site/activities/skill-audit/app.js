'use strict';
let active='all';
const search=document.querySelector('#case-search');
const rows=[...document.querySelectorAll('.case-row')];
function applyFilter(){const q=search.value.trim().toLowerCase();let count=0;for(const r of rows){const show=(active==='all'||r.dataset.owner===active)&&r.dataset.search.toLowerCase().includes(q);r.hidden=!show;if(show)count++;}document.querySelector('#result-count').textContent=count+' 条';document.querySelector('#empty').hidden=count>0;document.querySelectorAll('[data-filter]').forEach(b=>{const on=b.dataset.filter===active;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));});}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.filter;applyFilter();}));
document.querySelectorAll('[data-owner-filter]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.ownerFilter;search.value='';applyFilter();document.querySelector('#catalog').scrollIntoView();}));
search.addEventListener('input',applyFilter);
document.querySelectorAll('[data-open-example]').forEach(a=>a.addEventListener('click',()=>{document.getElementById(a.dataset.openExample).open=true;}));
const themeButton=document.querySelector('#theme-toggle');
function theme(mode){document.documentElement.dataset.theme=mode;themeButton.textContent=mode==='dark'?'浅色':'深色';themeButton.setAttribute('aria-label',mode==='dark'?'切换浅色模式':'切换深色模式');}
let saved=null;try{saved=localStorage.getItem('benchlibrary-audit-theme')}catch{}
theme(saved==='dark'?'dark':'light');
themeButton.addEventListener('click',()=>{const mode=document.documentElement.dataset.theme==='dark'?'light':'dark';theme(mode);try{localStorage.setItem('benchlibrary-audit-theme',mode)}catch{}});
if(location.hash.startsWith('#example-')){const target=document.getElementById(location.hash.slice(1));if(target&&target.tagName==='DETAILS')target.open=true;}
