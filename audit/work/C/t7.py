from h import *
for extra in [{}, {"ch4_content":85,"co2_content":2}]:
    s,j=post(dict({"year":2025,"month":7,"facility_id":1,"process_type":"flaring","factor_source":"specific","fuel":"Natural Gas (Flaring)","fuel_type":"Natural Gas (Flaring)","amount":1000,"quantity":1000,"unit":"m3"},**extra))
    print(extra,s,j if s>=300 else sql(DB,"select co2_emissions,ch4_emissions,calc_method,factor_source from emissions order by id desc limit 1"))
