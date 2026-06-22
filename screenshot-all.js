const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: 'msedge',
    args: ['--no-sandbox', '--disable-gpu']
  });
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1920 },
    deviceScaleFactor: 2
  });
  const page = await context.newPage();

  const filePath = 'file:///C:/Users/五颜六色/stock-analysis-app-main/video-ad.html';
  await page.goto(filePath, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForSelector('.scene.active', { timeout: 5000 });

  const totalScenes = 6;
  const sceneNames = [
    's1-buy-hold-sell',
    's2-daily-action-plan',
    's3-virtual-portfolio',
    's4-risk-warning',
    's5-data-vs-decision',
    's6-quant-is-poison'
  ];

  const destDir = path.join(__dirname, 'screenshots');
  const fs = require('fs');
  if (!fs.existsSync(destDir)) fs.mkdirSync(destDir);

  for (let i = 0; i < totalScenes; i++) {
    // Switch to scene i
    await page.evaluate((idx) => {
      var scenes = document.querySelectorAll('.scene');
      scenes.forEach(function(s) { s.classList.remove('active'); });
      scenes[idx].classList.add('active');
    }, i);
    await page.waitForTimeout(800); // wait for fadeUp animation

    const destFile = path.join(destDir, sceneNames[i] + '.png');
    await page.screenshot({ path: destFile, type: 'png', fullPage: false });
    console.log(`✅ [${i + 1}/${totalScenes}] ${sceneNames[i]}.png`);
  }

  await browser.close();
  console.log(`\n🎉 All ${totalScenes} screenshots saved to: ${destDir}`);
  console.log('   Format: 2160x3840 (9:16 @2x Retina)');
})();
