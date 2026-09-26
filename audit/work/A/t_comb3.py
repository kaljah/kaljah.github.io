import h
comp = dict(c1=87.5,c2=5.2,c3=2.1,c4=1.0,c5=0.5,co2_mol=1.8,n2_mol=1.9)
base = {"process_type":"combustion","factor_source":"specific","fuel":"Natural Gas","amount":50000,"unit":"scf","hhv":1010,"combustion_efficiency":0.993}
V = 50000*0.028316846592
def hand(fr, eta=0.993):
    carbon = sum(fr.get(f"c{i}",0)*i for i in range(1,11))
    co2 = (V*carbon*eta*1.861 + V*fr.get("co2",0)*1.861)/1000
    ch4 = V*fr["c1"]*(1-eta)*0.6785/1000
    return co2, ch4
fr = {k.replace("_mol",""):v/100 for k,v in comp.items()}
co2, ch4 = hand(fr)
n2o = 50000*1010/1e6*0.0001/1000
print("hand co2", co2, "ch4", ch4, "n2o", n2o, "co2e", co2+28*ch4+265*n2o)
h.show("T3 combustion template sample (mol%)", {**base, **comp})
# same composition expressed as fractions
h.show("T3 combustion as fractions", {**base, **{k:v/100 for k,v in comp.items()}})
# flaring: CH4 90% + N2 10% (fractions), 1000 m3, elevated default DE .98, CE .984
fl = {"process_type":"flaring","factor_source":"specific","fuel":"Natural Gas (Flaring)","amount":1000,"unit":"m3","c1":90,"n2_mol":10}
print("hand flaring ch4:", 1000*0.9*0.02*0.6785/1000, " co2:", 1000*0.9*0.984*1.861/1000)
h.show("T3 flaring CH4 90 + N2 10", fl)
