from h import *
base={"year":2025,"month":1,"facility_id":1,"factor_source":"default"}
cases=[("combustion","Diesel (No. 2 Fuel Oil)",1,"tonne"),("combustion","Diesel (No. 2 Fuel Oil)",1000,"kg"),
("combustion","Natural Gas",1,"tonne"),("combustion","Natural Gas",1000,"kg"),("combustion","Crude Oil",1,"tonne"),
("combustion","Bituminous Coal",1,"ton"),("combustion","Petroleum Coke",1,"tonne"),("combustion","Natural Gas",1,"Mcf"),("combustion","Natural Gas",1,"MMscf"),
("combustion","Motor Gasoline",1,"bbl"),("combustion","Residual Fuel Oil (No. 6)",1,"m3"),("combustion","Propane (Gas)",1000,"scf"),("combustion","Propane (Liquid)",1,"m3"),
("mobile","Diesel (No. 2 Fuel Oil)",1000,"gal"),("mobile","Motor Gasoline",1000,"L")]
for p,f,q,u in cases:
    pl=dict(base,process_type=p,fuel=f,fuel_type=f,amount=q,quantity=q,unit=u)
    s,j=post(pl)
    r=sql(DB,"select co2_emissions,ch4_emissions,n2o_emissions,calc_method from emissions order by id desc limit 1")[0]
    print(f"{p:10s} {f:28s} {q:6} {u:6} {s} co2={r['co2_emissions']:.6g} ch4={r['ch4_emissions']:.4g} n2o={r['n2o_emissions']:.4g} {r['calc_method']}")
