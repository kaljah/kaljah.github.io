import pdfplumber
from PIL import Image
import os

pdf_path = r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"
out_dir = r"screenshots\spot_check"
os.makedirs(out_dir, exist_ok=True)

with pdfplumber.open(pdf_path) as pdf:
    # 1: Heater 4 (Page 27, Table 8)
    # 2: Turbine 3 (Page 27, Table 8)
    # 3: Flare Purging (Page 27, Table 8)
    # 4: Flare1 - HP (Page 27, Table 8)
    # 5: Venting - CPF Non-Routine (Page 27, Table 8)
    # 6: Tank - Produced Water / Tank - Liquid Product (Page 28, Table 8)
    # 7: H01 NGL Hot Oil Heater (Page 33, Table 15)
    # 8: Flare – AP (Page 33, Table 15)
    # 9: Flare – OT1 (Page 33, Table 15)
    # 10: Fire Suppressant CO2 (Page 34, Table 15)

    targets = [
        ("spot_01_hbns_heater4.png", 27, ["Heater 4"]),
        ("spot_02_hbns_turbine3.png", 27, ["Turbine 3"]),
        ("spot_03_hbns_flare_purging.png", 27, ["Flare Purging"]),
        ("spot_04_hbns_flare1_hp.png", 27, ["Flare1"]),
        ("spot_05_hbns_venting_cpf.png", 27, ["Venting - CPF"]),
        ("spot_06_hbns_tank_liquid.png", 28, ["Tank - Liquid Product"]),
        ("spot_07_elm_h01_ngl_heater.png", 33, ["H01 NGL"]),
        ("spot_08_elm_flare_ap.png", 33, ["Flare – AP", "Flare - AP"]),
        ("spot_09_elm_flare_ot1.png", 33, ["Flare – OT1", "Flare - OT1"]),
        ("spot_10_elm_fire_suppressant.png", 34, ["Fire Suppressant CO2"]),
    ]

    for fname, p_num, search_words in targets:
        p = pdf.pages[p_num - 1]
        words = p.extract_words()
        
        # Find matching word bounding box
        matched = []
        for w in words:
            for sw in search_words:
                if sw.lower() in w["text"].lower():
                    matched.append(w)
                    break
        
        if matched:
            top_y = min(w["top"] for w in matched) - 15
            bottom_y = max(w["bottom"] for w in matched) + 20
            # Width across the whole table: x0=50, x1=560
            crop_bbox = (40, max(0, top_y), 560, min(p.height, bottom_y))
            cropped_page = p.crop(crop_bbox)
            im = cropped_page.to_image(resolution=250)
            dest = os.path.join(out_dir, fname)
            im.save(dest)
            print(f"Successfully cropped {fname} at y=[{top_y:.1f}, {bottom_y:.1f}]")
        else:
            print(f"Could not find words {search_words} on page {p_num}")

print("Done cropping spot checks!")
