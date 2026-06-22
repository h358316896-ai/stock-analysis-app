const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 2 });

  const filePath = 'file:///C:/Users/五颜六色/stock-analysis-app-main/video-ad.html';
  await page.goto(filePath, { waitUntil: 'networkidle0', timeout: 15000 });
  await page.waitForSelector('.scene.active', { timeout: 5000 });
  await new Promise(r => setTimeout(r, 1500));

  const dest = path.join(__dirname, 'video-ad-screenshot.png');
  await page.screenshot({ path: dest, type: 'png', fullPage: false });
  console.log('✅ Saved to video-ad-screenshot.png (1080x1920 @2x)');
  await browser.close();
})();
