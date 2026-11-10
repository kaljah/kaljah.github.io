import pdfplumber
import os

pdf_path = r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"
out_dir = r"screenshots\spot_check"
os.makedirs(out_dir, exist_ok=True)

with pdfplumber.open(pdf_path) as pdf:
    # Pages: 26, 27, 28, 32, 33, 34 (0-indexed: 25, 26, 27, 31, 32, 33)
    pages_to_render = [25, 26, 27, 31, 32, 33]
    for p_idx in pages_to_render:
        p = pdf.pages[p_idx]
        im = p.to_image(resolution=200)
        im.save(os.path.join(out_dir, f"page_{p_idx+1}.png"))
        print(f"Rendered page_{p_idx+1}.png")

print("Render complete!")
