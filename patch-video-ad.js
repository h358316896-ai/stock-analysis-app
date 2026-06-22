const fs = require('fs');
const path = require('path');

function patchFile(filePath, isCN) {
  let content = fs.readFileSync(filePath, 'utf8');

  // 1. Add nav CSS after body line
  const bodyCss = "body { background:#0a0c14; color:#c8c8d4; font-family:'SF Pro Display','Inter','Helvetica Neue',sans-serif; overflow:hidden; height:100vh; -webkit-font-smoothing:antialiased; }";
  const navCss = bodyCss + `

/* Top nav */
.ad-nav { position:fixed; top:0; left:0; right:0; z-index:100; display:flex; align-items:center; justify-content:space-between; padding:16px 24px; pointer-events:none; }
.ad-nav a { color:rgba(255,255,255,0.35); text-decoration:none; font-size:13px; font-weight:500; letter-spacing:0.04em; transition:color .2s; pointer-events:auto; }
.ad-nav a:hover { color:rgba(255,255,255,0.85); }
.ad-logo { display:flex; align-items:center; gap:8px; }
.ad-logo .dot { width:7px; height:7px; border-radius:50%; background:#d4a853; }`;
  content = content.replace(bodyCss, navCss);

  // 2. Add nav HTML after <body>
  const brand = isCN ? 'StockAI' : 'StockAI';
  const terminalText = isCN ? '行情终端 →' : 'Terminal →';
  const navHtml = `<body>
<div class="ad-nav">
  <a href="/" class="ad-logo"><span class="dot"></span>${brand}</a>
  <a href="/stock">${terminalText}</a>
</div>`;
  content = content.replace('<body>', navHtml);

  // 3. Make url-foot clickable
  const replacements = [
    ['StockAI · One Answer, Not a Hundred Indicators', '/'],
    ['StockAI · Defense, Not Another Blade', '/'],
    ['Risk-Free Practice · Real Market Data', '/stock'],
    ['Not Hindsight. Real-Time Risk Detection.', '/stock'],
    ["You Don't Need 100 Indicators. You Need 1 Answer.", '/stock'],
    ['Log in · Add Watchlist · Every Morning', '/stock'],
    ['StockAI · 一个决策，胜过一百个指标', '/'],
    ['StockAI · 防御，而非另一把刀', '/'],
    ['零风险练手 · 真实行情驱动', '/stock'],
    ['不是马后炮。实时风险检测。', '/stock'],
    ['你不需要一百个指标。你只需要一个答案。', '/stock'],
    ['登录 · 添加自选 · 每天清晨', '/stock'],
  ];

  for (const [text, href] of replacements) {
    const link = `<a href="${href}" style="color:#4a4a60;text-decoration:none;transition:color .2s" onmouseover="this.style.color='#8a8a9e'" onmouseout="this.style.color='#4a4a60'">${text}</a>`;
    // Match the text inside url-foot div: >text<
    content = content.replace('>' + text + '<', '>' + link + '<');
  }

  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Patched:', path.basename(filePath));
}

// Patch all copies
const baseDir = 'C:/Users/五颜六色/stock-analysis-app-main';
patchFile(path.join(baseDir, 'video-ad.html'), false);
patchFile(path.join(baseDir, 'video-ad-cn.html'), true);
patchFile(path.join(baseDir, 'static', 'video-ad-cn.html'), true);

// Also patch cdn-deploy and docs if they exist
const cdnFile = path.join(baseDir, 'cdn-deploy', 'video-ad.html');
const cdnFileCN = path.join(baseDir, 'cdn-deploy', 'video-ad-cn.html');
const docsFile = path.join(baseDir, 'docs', 'video-ad.html');
const docsFileCN = path.join(baseDir, 'docs', 'video-ad-cn.html');
if (fs.existsSync(cdnFile)) patchFile(cdnFile, false);
if (fs.existsSync(cdnFileCN)) patchFile(cdnFileCN, true);
if (fs.existsSync(docsFile)) patchFile(docsFile, false);
if (fs.existsSync(docsFileCN)) patchFile(docsFileCN, true);

console.log('\nAll copies patched.');
