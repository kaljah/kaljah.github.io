import pdfplumber

with pdfplumber.open('Groupement_Berkine_Original_Uploaded_Report.pdf') as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for i, p in enumerate(pdf.pages):
        text = p.extract_text() or ""
        first_line = text.split('\n')[0] if text else "EMPTY"
        print(f"Page {i+1}: {first_line[:80]}")
