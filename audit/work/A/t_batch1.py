import h
def run(label, p, exp=None):
    r = h.show(label, p)
    if exp: print("   EXPECTED:", exp)
# 1 fugitive Tier 1, component per-hour factor, 10 valves (UI: amount=count)
run("fugitive T1 Block Valve x10", {"process_type":"fugitive","factor_source":"default","fuel":"Component - Block Valve","amount":10,"unit":"count"},
    "ch4 = 10*4.36e-6 t/h*8760 = %.5f t/yr (or *744 h for a month = %.6f)" % (10*4.36e-6*8760, 10*4.36e-6*744))
run("wellhead_fugitive T1 Wellhead-Gas x10", {"process_type":"wellhead_fugitive","factor_source":"default","fuel":"Wellhead - Gas","amount":10,"unit":"count"},
    "ch4 = 10*1.8e-5*8760 = %.4f t/yr" % (10*1.8e-5*8760))
run("wellhead_fugitive T3 Wellhead-Gas x10", {"process_type":"wellhead_fugitive","factor_source":"specific","fuel":"Wellhead - Gas","amount":10,"unit":"count"},
    "ch4 = %.4f t/yr (factor already CH4)" % (10*1.8e-5*8760))
run("fugitive_component T3 Block Valve x10", {"process_type":"fugitive_component","factor_source":"specific","fuel":"Component - Block Valve","amount":10,"unit":"count"},
    "ch4 = %.5f t/yr" % (10*4.36e-6*8760))
# 2 offshore gas, 10^6 scf denominators
run("wellhead_fugitive T1 Offshore Gas 5 MMscf", {"process_type":"wellhead_fugitive","factor_source":"default","fuel":"Offshore - Gas Production (Facility)","amount":5,"unit":"mmscf"},
    "ch4 = 5*0.0104 = 0.052 t")
run("refinery T1 fuel gas 50,000 bbl", {"process_type":"refinery_fugitive","factor_source":"default","fuel":"Refinery - Fuel Gas System (50-99k bbl/day)","amount":50000,"unit":"bbl"},
    "ch4 = 50 kbbl*0.000375 = 0.01875 t")
# 3 dehydrator scf/MMscf default
run("dehydrator T1 DehyUncont 100 MMscf", {"process_type":"dehydrator","factor_source":"default","fuel":"Dehydrator - Glycol (Uncontrolled)","amount":100,"unit":"mmscf"},
    "ch4 = 100*0.177 scf*0.0283168*0.6785/1000 = %.3e t" % (100*0.177*0.028316846592*0.6785/1000))
# 5 negative amount for process not in dispatcher
run("loading T1 negative amount", {"process_type":"loading","factor_source":"default","fuel":"Loading - Crude Oil (Tank Truck)","amount":-1000000,"unit":"bbl"}, "reject (422)")
run("fccu negative", {"process_type":"separation","factor_source":"default","fuel":"Wastewater - Oil/Water Separator","amount":-5000,"unit":"bbl"}, "reject (422)")
# 6 energy units with kg/MMBtu factor
run("NG combustion 1000 kWh", {"process_type":"combustion","factor_source":"default","fuel":"Natural Gas","amount":1000,"unit":"kwh"},
    "1000 kWh = 3.412 MMBtu -> co2 = %.5f t" % (3.412142*53.06/1000))
run("NG combustion 1000 GJ", {"process_type":"combustion","factor_source":"default","fuel":"Natural Gas","amount":1000,"unit":"gj"},
    "co2 = %.4f t" % (1000*0.947817*53.06/1000))
run("NG combustion 1e6 MJ", {"process_type":"combustion","factor_source":"default","fuel":"Natural Gas","amount":1000000,"unit":"mj"},
    "co2 = %.4f t" % (1e6*0.000947817*53.06/1000))
run("NG combustion 1000 MMBtu", {"process_type":"combustion","factor_source":"default","fuel":"Natural Gas","amount":1000,"unit":"mmbtu"}, "co2=53.06 t")
run("NG combustion 1000 therm", {"process_type":"combustion","factor_source":"default","fuel":"Natural Gas","amount":1000,"unit":"therm"}, "co2=5.306 t")
