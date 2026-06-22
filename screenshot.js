const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });

  const filePath = 'file:///' + path.resolve('video-ad.html').replace(/\\/g, '/');
  await page.goto(filePath, { waitUntil: 'networkidle' });

  // Wait for first scene to fully render
  await page.waitForSelector('.scene.active');
  await page.waitForTimeout(1000);

  await page.screenshot({
    path: path.join(__dirname, 'video-ad-screenshot.png'),
    type: 'png',
    fullPage: false
  });

  console.log('Screenshot saved to video-ad-screenshot.png (1080x1920)');
  await browser.close();
})();
