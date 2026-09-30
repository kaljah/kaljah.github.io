import { API_FACTORS, PROCESS_TYPES } from "file:///C:/Users/samsung/Desktop/H2/new/client/src/utils/EmissionFactors.js";
const out = {};
for (const [k,v] of Object.entries(API_FACTORS)) out[k] = {co2:v.co2,ch4:v.ch4,n2o:v.n2o,unit:v.unit,hhv:v.hhv,baseUnit:v.baseUnit,usage:v.usage,type:v.type};
console.log(JSON.stringify({factors:out, ptypes:PROCESS_TYPES}));
