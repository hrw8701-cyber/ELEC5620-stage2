import {chromium} from 'playwright';
const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage();
page.on('request',r=>{if(r.url().includes('/api/state'))console.log('request',r.headers()['x-demo-role'])});
page.on('response',r=>{if(r.url().includes('/api/state'))console.log('response',r.status())});
page.on('pageerror',e=>console.log('PAGE_ERROR',e.message));
try{
const s=await page.request.get('http://127.0.0.1:8001/api/state').then(r=>r.json());const o=s.orders.find(o=>o.requests.length);
for(const route of ['#/property-confirm/'+o.requests[0].token,'#/buyer/orders/'+o.id,'#/manager/overview','#/buyer/orders/'+o.id]){
 console.log('NAV',route);await page.goto('http://127.0.0.1:5622/'+route);await page.waitForTimeout(3000);await page.getByText('正在加载…',{exact:true}).waitFor({state:'hidden',timeout:20000});console.log('BODY',(await page.locator('body').innerText()).slice(0,160));
}
}finally{await browser.close()}
console.log('Cross-role navigation passed');
