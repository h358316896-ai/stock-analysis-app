const fs = require('fs');
const path = require('path');

const bodyCssCN = "body { background:#0a0c14; color:#c8c8d4; font-family:'PingFang SC','Noto Sans SC','Microsoft YaHei','Helvetica Neue',sans-serif; overflow:hidden; height:100vh; -webkit-font-smoothing:antialiased; }";
const navCss = bodyCssCN + `

/* Top nav */
.ad-nav { position:fixed; top:0; left:0; right:0; z-index:100; display:flex; align-items:center; justify-content:space-between; padding:16px 24px; pointer-events:none; }
.ad-nav a { color:rgba(255,255,255,0.35); text-decoration:none; font-size:13px; font-weight:500; letter-spacing:0.04em; transition:color .2s; pointer-events:auto; }
.ad-nav a:hover { color:rgba(255,255,255,0.85); }
.ad-logo { display:flex; align-items:center; gap:8px; }
.ad-logo .dot { width:7px; height:7px; border-radius:50%; background:#d4a853; }`;

const cnFiles = [
  'C:/Users/五颜六色/stock-analysis-app-main/video-ad-cn.html',
  'C:/Users/五颜六色/stock-analysis-app-main/static/video-ad-cn.html',
  'C:/Users/五颜六色/stock-analysis-app-main/cdn-deploy/video-ad-cn.html',
  'C:/Users/五颜六色/stock-analysis-app-main/docs/video-ad-cn.html',
];

for (const f of cnFiles) {
  if (!fs.existsSync(f)) { console.log('SKIP (not found):', f); continue; }
  let content = fs.readFileSync(f, 'utf8');
  if (content.includes('.ad-nav {')) { console.log('SKIP (already patched):', path.basename(f)); continue; }
  content = content.replace(bodyCssCN, navCss);
  fs.writeFileSync(f, content, 'utf8');
  console.log('PATCHED:', path.basename(f));
}
