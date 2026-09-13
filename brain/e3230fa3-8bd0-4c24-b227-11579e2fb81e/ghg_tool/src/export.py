import pandas as pd
import io
import xlsxwriter

def to_excel(calculations, facility_info=None):
    """
    Convert calculations and facility info to an Excel file.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # --- FACILITY INFO SHEET ---
    if facility_info:
        ws_info = workbook.add_worksheet("Facility Info")
        bold = workbook.add_format({'bold': True})
        
        ws_info.write(0, 0, "Facility Information (EPA Reporting)", bold)
        
        row = 2
        for key, value in facility_info.items():
            # Format key for display (e.g., "org_name" -> "Organization Name")
            display_key = key.replace("_", " ").title()
            ws_info.write(row, 0, display_key, bold)
            ws_info.write(row, 1, value)
            row += 1
            
        ws_info.set_column(0, 0, 25)
        ws_info.set_column(1, 1, 40)

    # --- CALCULATIONS SHEET ---
    worksheet = workbook.add_worksheet("Emissions Data")
    
    if not calculations:
        worksheet.write(0, 0, "No calculations to export.")
    else:
        # Create DataFrame from calculations
        # Exclude _meta for cleaner export, but keep key details
        data = []
        for c in calculations:
            item = {k: v for k, v in c.items() if k != "_meta"}
            # Add method details if available
            if "_meta" in c:
                item["Method"] = c["_meta"].get("method", "")
                item["Formula"] = c["_meta"].get("formula", "")
            data.append(item)
            
        df = pd.DataFrame(data)
        
        # Write headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value)
            
        # Write data
        for row_num, row_data in enumerate(df.values):
            for col_num, value in enumerate(row_data):
                worksheet.write(row_num + 1, col_num, value)
                
    workbook.close()
    return output.getvalue()
