const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const [preview, playwrightModule, chrome, output] = process.argv.slice(2);
const {chromium} = require(playwrightModule);
const localOrigin = 'http://localhost:9887';
const mediaTypes = {'.html':'text/html','.js':'text/javascript','.json':'application/json','.png':'image/png','.svg':'image/svg+xml'};
const animationPath = '/nara-v14/lottie/success.json';
const malformed = Buffer.from('{"layers": [');
const nonUtf8 = Buffer.from([0xff, 0xff]);
const digest = content => createHash('sha256').update(content).digest('hex');
async function run(browser, scenario) {
  const context = await browser.newContext({reducedMotion:scenario.reduced ? 'reduce':'no-preference', viewport:{width:390,height:840}});
  const errors = [];
  let served = 0;
  try {
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== localOrigin) return route.abort();
      const requestPath = url.pathname === '/' ? '/index.html' : url.pathname;
      const absolute = path.resolve(preview, '.' + requestPath);
      if (path.relative(preview, absolute).startsWith('..')) return route.abort();
      let body;
      try {body = await fs.readFile(absolute);} catch {return route.fulfill({status:404,body:''});}
      if (requestPath === '/index.html' && scenario.matchBadDigest) {
        body = body.toString().replace(/(data-mood="success" data-sha256=")[a-f0-9]+/, (_, start) => start + digest(scenario.bytes));
      }
      if (requestPath.endsWith('/lottie-light-5.13.0.min.js') && (scenario.playerError || scenario.playerSilent)) {
        const fault = scenario.playerSilent
          ? 'animation.addEventListener = () => {};'
          : 'const add = animation.addEventListener.bind(animation); animation.addEventListener = (name, fn) => { if (name === "error") queueMicrotask(fn); else add(name, fn); };';
        body = body.toString() + `;{
          const load = lottie.loadAnimation.bind(lottie);
          lottie.loadAnimation = options => {
            const animation = load(options);
            if (options.animationData.nm.includes("success")) { ${fault} }
            return animation;
          };
        }`;
      }
      const broken = (scenario.all || requestPath === animationPath) && requestPath.endsWith('.json') && !!scenario.bytes;
      if (broken) served++;
      await route.fulfill({
        status: broken && scenario.httpStatus ? scenario.httpStatus : 200,
        contentType:mediaTypes[path.extname(absolute)] || 'application/octet-stream',
        body:broken ? scenario.bytes : body
      });
    });
    await page.goto(localOrigin, {waitUntil:'domcontentloaded'});
    await page.waitForFunction(() => document.querySelectorAll('[data-mood][data-loaded],[data-mood][data-failed]').length === 9);
    const ready = await page.locator('[data-mood][data-loaded]').count();
    const failed = await page.locator('[data-mood][data-failed] img.poster').count();
    assert.equal(ready, scenario.ready);
    assert.equal(failed, 9-scenario.ready);
    assert.equal(served, scenario.bytes ? 9-scenario.ready : 0);
    assert.deepEqual(errors, []);
    const play = page.locator('#play');
    if (scenario.reduced) {
      assert(await play.isDisabled());
      const still = await page.locator('[data-mood="success"] .actor svg').innerHTML();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert.equal(await page.locator('[data-mood="success"] .actor svg').innerHTML(), still);
      await page.emulateMedia({reducedMotion:'no-preference'});
      await page.waitForFunction(() => !document.querySelector('#play').disabled);
    } else {
      assert.equal(await play.isDisabled(), ready === 0);
    }
    if (scenario.save) {
      const card = page.locator('[data-mood="success"]');
      assert(await card.locator('img.poster').evaluate(img => img.complete && img.naturalWidth > 0));
      await card.screenshot({path:path.join(output,'lottie-fallback.png')});
    }
    if (ready === 9 && !scenario.reduced) {
      const actor = page.locator('[data-mood="success"] .actor svg');
      const still = await actor.innerHTML();
      await play.click();
      await page.waitForFunction(initial => document.querySelector('[data-mood="success"] .actor svg').innerHTML !== initial, still);
      await page.locator('#reduce').click();
      assert(await play.isDisabled());
      assert.equal(await actor.innerHTML(), still);
      await page.locator('#reduce').click();
      assert(await play.isEnabled());
    }
    console.log(JSON.stringify({scenario:scenario.name,ready,failed,served,pageErrors:errors.length}));
  } finally {
    await context.close();
  }
}
(async () => {
  assert(preview && playwrightModule && chrome && output, 'Pass absolute preview, Playwright module, Chrome and output paths.');
  await fs.mkdir(output, {recursive:true});
  const browser = await chromium.launch({headless:true,executablePath:chrome});
  try {
    for (const scenario of [
      {name:'valid and manual motion toggle',ready:9},
      {name:'valid with system reduced motion',ready:9,reduced:true},
      {name:'tampered valid JSON',ready:8,bytes:Buffer.from('{}')},
      {name:'truncated bytes',ready:8,bytes:malformed,save:true},
      {name:'truncated with matching digest',ready:8,bytes:malformed,matchBadDigest:true},
      {name:'invalid UTF-8 with matching digest',ready:8,bytes:nonUtf8,matchBadDigest:true},
      {name:'player reports startup error',ready:8,playerError:true},
      {name:'player never reports startup',ready:8,playerSilent:true},
      {name:'missing asset',ready:8,bytes:Buffer.from(''),httpStatus:404},
      {name:'all assets unavailable',ready:0,bytes:Buffer.from(''),httpStatus:503,all:true}
    ]) await run(browser, scenario);
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
