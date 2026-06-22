const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

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

  await page.goto('https://stock-analysis-app-production-da60.up.railway.app/video-ad-cn', {
    waitUntil: 'networkidle', timeout: 20000
  });
  await page.waitForSelector('.scene.active', { timeout: 5000 });

  const total = 6;
  const destDir = path.join(__dirname, 'screenshots-cn');
  if (!fs.existsSync(destDir)) fs.mkdirSync(destDir);

  for (let i = 0; i < total; i++) {
    await page.evaluate((idx) => {
      var scenes = document.querySelectorAll('.scene');
      scenes.forEach(function(s) { s.classList.remove('active'); });
      scenes[idx].classList.add('active');
    }, i);
    await page.waitForTimeout(800);

    // Get scene id for naming
    const sceneId = await page.evaluate((idx) => {
      return document.querySelectorAll('.scene')[idx].id || ('s' + (idx + 1));
    }, i);

    const destFile = path.join(destDir, sceneId + '.png');
    await page.screenshot({ path: destFile, type: 'png', fullPage: false });
    console.log(`✅ [${i + 1}/${total}] ${sceneId}.png`);
  }

  await browser.close();
  console.log(`\n🎉 全部 ${total} 张截图保存至: ${destDir}`);
  console.log('   格式: 2160x3840 (9:16 @2x)');
})();
