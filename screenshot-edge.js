const { chromium } = require('playwright');

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
  await page.waitForTimeout(1500);

  const dest = 'C:/Users/五颜六色/stock-analysis-app-main/video-ad-screenshot.png';
  await page.screenshot({ path: dest, type: 'png', fullPage: false });
  console.log('✅ Saved: video-ad-screenshot.png (1080x1920 @2x)');
  await browser.close();
})();
