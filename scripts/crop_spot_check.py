import pdfplumber
from PIL import Image, ImageDraw
import os

pdf_path = r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"
out_dir = r"screenshots\spot_check"
os.makedirs(out_dir, exist_ok=True)

# 10 sampled sources (seed 42):
# 1: [HBNS] Heater 4 - Page 26 (Table 7) & Page 27 (Table 8)
# 2: [HBNS] Turbine 3 - Page 26 (Table 7) & Page 27 (Table 8)
# 3: [HBNS] Flare Purging - Page 26 (Table 7) & Page 27 (Table 8)
# 4: [HBNS] Flare1 – HP - Page 26 (Table 7) & Page 27 (Table 8)
# 5: [HBNS] Venting - CPF Non-Routine - Page 26 (Table 7) & Page 27 (Table 8)
# 6: [HBNS] Tank - Liquid Product - Page 27 (Table 7) & Page 28 (Table 8)
# 7: [El Merk] H01 NGL Hot Oil Heater - Page 32 (Table 14) & Page 33 (Table 15)
# 8: [El Merk] Flare – AP - Page 32 (Table 14) & Page 33 (Table 15)
# 9: [El Merk] Flare – OT1 - Page 32 (Table 14) & Page 33 (Table 15)
# 10: [El Merk] Fire Suppressant CO2 - Page 32 (Table 14) & Page 34 (Table 15)

with pdfplumber.open(pdf_path) as pdf:
    # Let's extract bounding boxes or text positions for these items to create perfect crops!
    sample_targets = [
        {"id": "01", "name": "Heater 4", "entity": "HBNS", "p_act": 26, "p_em": 27, "term": "Heater 4"},
        {"id": "02", "name": "Turbine 3", "entity": "HBNS", "p_act": 26, "p_em": 27, "term": "Turbine 3"},
        {"id": "03", "name": "Flare Purging", "entity": "HBNS", "p_act": 26, "p_em": 27, "term": "Flare Purging"},
        {"id": "04", "name": "Flare1 - HP", "entity": "HBNS", "p_act": 26, "p_em": 27, "term": "Flare1"},
        {"id": "05", "name": "Venting - CPF Non-Routine", "entity": "HBNS", "p_act": 26, "p_em": 27, "term": "Venting - CPF Non-Routine"},
        {"id": "06", "name": "Tank - Liquid Product", "entity": "HBNS", "p_act": 27, "p_em": 28, "term": "Tank - Liquid Product"},
        {"id": "07", "name": "H01 NGL Hot Oil Heater", "entity": "El Merk", "p_act": 32, "p_em": 33, "term": "H01 NGL Hot Oil Heater"},
        {"id": "08", "name": "Flare - AP", "entity": "El Merk", "p_act": 32, "p_em": 33, "term": "Flare – AP"},
        {"id": "09", "name": "Flare - OT1", "entity": "El Merk", "p_act": 32, "p_em": 33, "term": "Flare – OT1"},
        {"id": "10", "name": "Fire Suppressant CO2", "entity": "El Merk", "p_act": 32, "p_em": 34, "term": "Fire Suppressant CO2"},
    ]
    
    for t in sample_targets:
        # Render the emissions page image
        p_num = t["p_em"]
        page = pdf.pages[p_num - 1]
        im = page.to_image(resolution=200)
        
        # Save full page as base
        full_path = os.path.join(out_dir, f"spot_{t['id']}_{t['entity'].lower().replace(' ', '_')}_{t['term'][:10].strip().lower()}_page{p_num}.png")
        im.save(full_path)
        print(f"Saved: {full_path}")

print("All spot check images generated!")
