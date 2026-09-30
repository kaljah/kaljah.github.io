import { API_FACTORS } from "file:///C:/Users/samsung/Desktop/H2/new/client/src/utils/EmissionFactors.js";
const out={};
for (const [k,v] of Object.entries(API_FACTORS)) out[k]={usage:v.usage||[],baseUnit:v.baseUnit||null,unit:v.unit, hhv:v.hhv, co2:v.co2, stream:v.stream||null};
console.log(JSON.stringify(out));
