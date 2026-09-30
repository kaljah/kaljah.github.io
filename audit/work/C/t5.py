from h import *
def mk(**kw): return c.post("/api/custom-factors/",json=kw).get_json()["id"]
def run(label,cf,proc,q,u,exp):
    post({"year":2025,"month":4,"facility_id":1,"process_type":proc,"factor_source":"custom","fuel":str(cf),"fuel_type":str(cf),"amount":q,"quantity":q,"unit":u,"custom_factor_id":cf})
    r=sql(DB,"select co2_emissions,calc_method from emissions order by id desc limit 1")[0]
    print(f"{label:50s} exp={exp:.5g} t act={r['co2_emissions']:.5g} t ratio={r['co2_emissions']/exp:.4g} {r['calc_method']}")
t=mk(name="MD tonne",co2_factor=3170,unit="tonne",usage="combustion")
run("unit=tonne co2=3170 kg/unit, 1 tonne",t,"combustion",1,"tonne",3.17)
run("unit=tonne co2=3170 kg/unit, 1000 kg",t,"combustion",1000,"kg",3.17)
k=mk(name="MD kg",co2_factor=3.17,unit="kg")
run("unit=kg co2=3.17, 1 tonne",k,"combustion",1,"tonne",3.17)
g=mk(name="MD gal",co2_factor=10.21,unit="gal")
run("unit=gal co2=10.21, 1 bbl",g,"combustion",1,"bbl",0.42882)
s=mk(name="MD scf",co2_factor=0.0541,unit="scf")
run("unit=scf co2=0.0541, 1000 m3",s,"combustion",1000,"m3",1000*35.3147*0.0541/1000)
m=mk(name="MD m3",co2_factor=1.9,unit="m³")
run("unit=m³ co2=1.9, 1000 scf",m,"combustion",1000,"scf",1000*0.0283168*1.9/1000)
b=mk(name="MD bbl",co2_factor=430,unit="bbl")
run("unit=bbl co2=430, 1000 L",b,"combustion",1000,"L",1000/158.987*430/1000)
run("unit=tonne co2=3170, 1 tonne flaring",t,"flaring",1,"tonne",3.17)
