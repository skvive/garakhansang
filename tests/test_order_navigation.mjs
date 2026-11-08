import assert from "node:assert/strict";
import { buildDirections, hasVerifiedGps, MARKET_ADDRESS } from "../storefront/order-lab/navigation.mjs";

const verified={
 name:"현장 검증 매장", isDemo:false,
 coordinateStatus:"verified",latitude:37.494321,longitude:127.112345,
 building:"가락시장",floor:"1F",room:"A-103"
};
const route=buildDirections(verified,"driving"),u=new URL(route.url);
assert.equal(route.verified,true);
assert.equal(route.mode,"store");
assert.equal(u.origin,"https://www.google.com");
assert.equal(u.searchParams.get("destination"),"37.494321,127.112345");
assert.equal(u.searchParams.get("travelmode"),"driving");
assert.match(route.locationLabel,/A-103/);
assert.equal(hasVerifiedGps({...verified,coordinateStatus:"unverified"}),false);
for(const bad of [undefined,null,{...verified,isDemo:true},{...verified,latitude:0},{...verified,longitude:null}]){
  const result=buildDirections(bad,"malicious");
  assert.equal(result.verified,false);
  assert.equal(result.destination,MARKET_ADDRESS);
  assert.equal(new URL(result.url).searchParams.get("travelmode"),"walking");
  assert.match(result.notice,/확인|가상|실제/);
}
console.log("Garakland navigation reuse: 8 scenarios / verified GPS and market fallback PASSED");
