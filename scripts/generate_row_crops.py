import pdfplumber
import os

pdf_path = r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"
out_dir = r"screenshots\spot_check"
os.makedirs(out_dir, exist_ok=True)

# 10 targets:
targets = [
    {"id": "01", "name": "spot_01_hbns_heater4.png", "page": 27, "find": ["Heater", "4", "69,721.20"]},
    {"id": "02", "name": "spot_02_hbns_turbine3.png", "page": 27, "find": ["Turbine", "3", "115,299.77"]},
    {"id": "03", "name": "spot_03_hbns_flare_purging.png", "page": 27, "find": ["Flare", "Purging", "20,645.161"]},
    {"id": "04", "name": "spot_04_hbns_flare1_hp.png", "page": 27, "find": ["Flare1", "HP", "117,967.93"]},
    {"id": "05", "name": "spot_05_hbns_venting_cpf.png", "page": 27, "find": ["Venting", "CPF", "13,485.24"]},
    {"id": "06", "name": "spot_06_hbns_tank_liquid.png", "page": 28, "find": ["Tank", "Liquid", "Product"]},
    {"id": "07", "name": "spot_07_elm_h01_ngl_heater.png", "page": 33, "find": ["H01", "NGL", "62,315.67"]},
    {"id": "08", "name": "spot_08_elm_flare_ap.png", "page": 33, "find": ["Flare", "AP", "26,670.68"]},
    {"id": "09", "name": "spot_09_elm_flare_ot1.png", "page": 33, "find": ["Flare", "OT1", "18,637.18"]},
    {"id": "10", "name": "spot_10_elm_fire_suppressant.png", "page": 34, "find": ["Fire", "Suppressant", "1.22"]},
]

with pdfplumber.open(pdf_path) as pdf:
    for t in targets:
        p = pdf.pages[t["page"] - 1]
        words = p.extract_words()
        
        # Find word with the key term
        key_word = t["find"][-1]
        matching_words = [w for w in words if key_word in w["text"]]
        if not matching_words:
            matching_words = [w for w in words if t["find"][0] in w["text"]]
            
        if matching_words:
            # Pick the best matching word
            target_w = matching_words[0]
            # Crop 2 lines above and 2 lines below
            y0 = max(0, target_w["top"] - 18)
            y1 = min(p.height, target_w["bottom"] + 18)
            crop_box = (50, y0, 560, y1)
            im = p.crop(crop_box).to_image(resolution=300)
            dest = os.path.join(out_dir, t["name"])
            im.save(dest)
            print(f"Generated {t['name']} at y=[{y0:.1f}, {y1:.1f}]")
        else:
            print(f"FAILED for {t['name']}")

print("All row crops generated successfully!")
