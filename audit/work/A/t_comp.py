import h
# UI-shaped completions payload: rate 0.5 Mcf/hr, 24 h, 2 events, 80% CH4, vented
ui = {"calc_method":"rate_duration","comp_duration":24,"comp_rate":0.5,"ch4_content":80,"amount":2}
p = {"process_type":"completions","factor_source":"specific","amount":0.5*24*28.3168,"quantity":0.5*24*28.3168,"unit":"m3",
     "calc_inputs":{"completions":ui}}
h.show("completions rate_duration (UI shape)", p)
# expected: 0.5 Mcf/hr*24h*2 events = 24 Mcf = 24000 scf -> m3
m3 = 24000*0.028316846592
ch4_t = m3*0.8*0.6785/1000
print("   expected ch4 t (density 0.6785):", ch4_t, " co2e AR5:", ch4_t*28)
# Same, but user left dropdown untouched (calc_method absent)
ui2 = dict(ui); ui2.pop("calc_method")
h.show("completions default dropdown (calc_method absent)", {**p, "calc_inputs":{"completions":ui2}})
# metered via API directly: amount=1000 m3 1 event
h.show("completions metered amount=1000 m3", {"process_type":"completions","factor_source":"specific","amount":1000,"unit":"m3","ch4_content":80,"comp_method":"metered_volume"})
print("   expected ch4 t:", 1000*0.8*0.6785/1000)
