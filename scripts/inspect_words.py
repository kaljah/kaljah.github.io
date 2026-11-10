import pdfplumber

pdf_path = r"C:\Users\samsung\.gemini\antigravity\brain\479daf75-25e8-4af0-af9b-4526d452b933\.user_uploaded\media_1794223915555_82a10d63.pdf"

with pdfplumber.open(pdf_path) as pdf:
    p27 = pdf.pages[26] # 0-indexed 26 is page 27
    words = p27.extract_words()
    print("Page 27 sample words:")
    for w in words[:40]:
        print(f"'{w['text']}' at x0={w['x0']:.1f}, top={w['top']:.1f}")
