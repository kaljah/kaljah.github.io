from h import *
base={"year":2025,"month":1,"facility_id":1,"factor_source":"default"}
cases=[
 ("combustion","Natural Gas",1000,"scf"),
 ("combustion","Natural Gas",1000,"m3"),
 ("combustion","Diesel (No. 2 Fuel Oil)",1000,"gal"),
 ("combustion","Diesel (No. 2 Fuel Oil)",1000,"l"),
 ("combustion","Ethane",1000,"scf"),
 ("combustion","Ethane",1000,"gal"),
 ("combustion","Butane",1000,"scf"),
 ("combustion","Naphtha",1000,"gal"),
 ("combustion","Wood / Wood Waste",1,"tonne"),
 ("combustion","Bituminous Coal",1,"tonne"),
 ("combustion","Propane (Liquid)",1000,"gal"),
 ("combustion","Refinery Fuel Gas",1000,"scf"),
 ("combustion","Natural Gas",10,"GJ"),
 ("combustion","Natural Gas",10,"TJ"),
 ("fugitive","Fugitive - Valve (Gas/Vapor)",100,"count"),
 ("fugitive","Fugitive - Valve (Light Oil)",100,"count"),
 ("drilling","Drilling - Mud Degassing (Oil Based)",100,"bbl"),
 ("venting","Blowdown - Pipeline",2,"event"),
 ("pneumatic","Pneumatic Pump - Chemical Injection (Piston)",10,"count"),
 ("dehydrator","Dehydrator - Glycol (Uncontrolled)",100,"MMscf"),
]
for p,f,q,u in cases:
    pl=dict(base,process_type=p,fuel=f,fuel_type=f,amount=q,quantity=q,unit=u)
    s,j=post(pl)
    rid=(j or {}).get("id") or (j or {}).get("record_id") or (j or {}).get("emission_id")
    print(p,f,q,u,s, (j if s>=300 else ""), )
    r=sql(DB,"select id,co2_emissions,ch4_emissions,n2o_emissions,co2e_total,calc_method,uncertainty,uncertainty_ch4 from emissions order by id desc limit 1")
    print("   ",r)
