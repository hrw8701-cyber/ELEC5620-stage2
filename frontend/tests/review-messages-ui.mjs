import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,channel:'msedge'});
try{
 const page=await browser.newPage();const base=process.env.BASE_URL||'http://127.0.0.1:5623';
 const state=await(await page.request.get(base+'/api/state',{headers:{'X-Demo-Role':'seller'}})).json();
 let status='review_busy';
 await page.route('**/api/actions',r=>r.fulfill({json:{state,result:{status,suggested:null,errors:status==='input_invalid'?{material:'请填写有效内容（2–80 字符）'}:{}}}}));
 await page.goto(base+'/#/seller/listings/new');
 for(const [s,text] of [['review_busy','图片审核服务繁忙'],['review_timeout','图片审核超时'],['review_unavailable','图片审核服务暂不可用'],['input_invalid','家具资料不完整或格式不正确'],['photo_rejected','上传图片不符合平台政策'],['insufficient','未找到足够的可比二手商品']]){
  status=s;await page.getByTestId('get-suggested-price').click();
  await page.locator('.suggestion').getByText(text,{exact:false}).waitFor();
  if(s!=='photo_rejected')assert.equal(await page.locator('.suggestion').getByText('上传图片不符合平台政策',{exact:true}).count(),0);
 }
 await page.getByRole('button',{name:'EN',exact:true}).click();status='review_busy';await page.getByTestId('get-suggested-price').click();await page.getByText('Photo review is busy.',{exact:false}).waitFor();
 await page.getByLabel('Front photo',{exact:true}).setInputFiles({name:'empty.jpg',mimeType:'image/jpeg',buffer:Buffer.alloc(0)});
 await page.getByRole('alert').filter({hasText:'The photo file is empty.'}).waitFor();
 console.log('PASS: distinct review/field/market messages, English busy message, empty upload message.');
}finally{await browser.close();}
