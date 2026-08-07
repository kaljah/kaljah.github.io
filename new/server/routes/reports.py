from routes.auth import login_required
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from extensions import db
from models import Emission, Facility, Scope2Emission, Scope3Emission, OgmpSurvey, ProductionData, LevelUpgradeLog
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

reports_bp = Blueprint('reports', __name__)

def create_pdf_report(emissions_data, filters):
    """Generate PDF report for emissions data"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#10b981'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=10
    )
    
    # Title
    elements.append(Paragraph("GHG Emissions Report", title_style))
    
    # Report metadata
    report_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on {report_date}", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Filter summary
    filter_text = "<b>Report Filters:</b><br/>"
    if filters.get('year'):
        filter_text += f"Year: {filters['year']}<br/>"
    if filters.get('month'):
        filter_text += f"Month: {filters['month']}<br/>"
    if filters.get('facility_id'):
        facility = Facility.query.get(filters['facility_id'])
        if facility:
            filter_text += f"Facility: {facility.name}<br/>"
    if filters.get('process_type'):
        filter_text += f"Process Type: {filters['process_type']}<br/>"
    
    elements.append(Paragraph(filter_text, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    total_co2e = sum(e.get('total_co2e', 0) for e in emissions_data)
    total_co2 = sum(e.get('co2_emissions', 0) for e in emissions_data)
    total_ch4 = sum(e.get('ch4_emissions', 0) for e in emissions_data)
    total_n2o = sum(e.get('n2o_emissions', 0) for e in emissions_data)
    
    elements.append(Paragraph("Emission Summary", heading_style))
    
    summary_data = [
        ['Metric', 'Value (tonnes CO₂e)'],
        ['Total CO₂', f'{total_co2:,.2f}'],
        ['Total CH₄', f'{total_ch4:,.2f}'],
        ['Total N₂O', f'{total_n2o:,.2f}'],
        ['Total CO₂e', f'{total_co2e:,.2f}']
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5'))
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Detailed emissions table
    elements.append(Paragraph("Detailed Emissions Data", heading_style))
    
    # Table headers
    table_data = [['Date', 'Facility', 'Process', 'Fuel/Source', 'Amount', 'CO₂', 'CH₄', 'N₂O', 'Total CO₂e']]
    
    # Table rows
    for emission in emissions_data[:50]:  # Limit to 50 records for PDF
        table_data.append([
            emission.get('date', 'N/A'),
            emission.get('facility_name', 'N/A')[:15],  # Truncate long names
            emission.get('process_type', 'N/A')[:12],
            emission.get('fuel_type', 'N/A')[:12],
            f"{emission.get('amount', 0):,.1f}",
            f"{emission.get('co2_emissions', 0):,.2f}",
            f"{emission.get('ch4_emissions', 0):,.2f}",
            f"{emission.get('n2o_emissions', 0):,.2f}",
            f"{emission.get('total_co2e', 0):,.2f}"
        ])
    
    # Create table
    col_widths = [0.8*inch, 1*inch, 0.9*inch, 0.9*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.9*inch]
    details_table = Table(table_data, colWidths=col_widths)
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(details_table)
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = f"<i>Report contains {len(emissions_data)} emission records. " \
                 f"Generated by GHG Emissions Management System.</i>"
    elements.append(Paragraph(footer_text, styles['Italic']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@reports_bp.route('/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate PDF report based on filters"""
    try:
        from models import Scope2Emission, Scope3Emission
        data = request.get_json()
        filters = data.get('filters', {})
        scope = filters.get('scope', 'all')
        
        # Determine years/months/facilities
        try:
            year = int(filters['year']) if filters.get('year') and filters['year'] != 'all' else None
        except (ValueError, TypeError):
            year = None
            
        try:
            month = int(filters['month']) if filters.get('month') and filters['month'] != 'all' else None
        except (ValueError, TypeError):
            month = None
            
        facility_id = None
        if filters.get('facility_id') and filters['facility_id'] != 'all':
            try:
                facility_id = int(filters['facility_id'])
            except (ValueError, TypeError):
                facility_id = None
                
        process_type = filters.get('process_type') if filters.get('process_type') and filters['process_type'] != 'all' else None

        emissions_data = []

        # 1. SCOPE 1
        if scope in ['all', '1']:
            q = Emission.query
            if year: q = q.filter_by(year=year)
            if month: q = q.filter_by(month=month)
            if facility_id: q = q.filter_by(facility_id=facility_id)
            if process_type: q = q.filter_by(process_type=process_type)
            q = q.filter(Emission.status != 'Draft')
            
            for e in q.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 1,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': e.process_type or 'N/A',
                    'fuel_type': e.fuel_type or 'N/A',
                    'amount': e.quantity or 0,
                    'co2_emissions': e.co2_emissions or 0,
                    'ch4_emissions': e.ch4_emissions or 0,
                    'n2o_emissions': e.n2o_emissions or 0,
                    'total_co2e': e.co2e_total or 0
                })

        # 2. SCOPE 2
        if scope in ['all', '2']:
            q2 = Scope2Emission.query
            if year: q2 = q2.filter_by(year=year)
            if month: q2 = q2.filter_by(month=month)
            if facility_id: q2 = q2.filter_by(facility_id=facility_id)
            q2 = q2.filter(Scope2Emission.status != 'Draft')
            for e in q2.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 2,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': f"Scope 2: {e.source_type or 'Electricity'}",
                    'fuel_type': e.grid_region or 'Grid',
                    'amount': e.electricity_kwh or 0,
                    'co2_emissions': 0, 'ch4_emissions': 0, 'n2o_emissions': 0,
                    'total_co2e': e.co2e or 0
                })

        # 3. SCOPE 3
        if scope in ['all', '3']:
            q3 = Scope3Emission.query
            if year: q3 = q3.filter_by(year=year)
            if month: q3 = q3.filter_by(month=month)
            if facility_id: q3 = q3.filter_by(facility_id=facility_id)
            q3 = q3.filter(Scope3Emission.status != 'Draft')
            for e in q3.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 3,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': e.category or 'Scope 3',
                    'fuel_type': e.sub_category or 'Value Chain',
                    'amount': e.activity_data or 0,
                    'co2_emissions': 0, 'ch4_emissions': 0, 'n2o_emissions': 0,
                    'total_co2e': e.co2e or 0
                })
        
        # Sort by date
        emissions_data.sort(key=lambda x: x['date'], reverse=True)

        # Generate PDF
        pdf_buffer = create_pdf_report(emissions_data, filters)
        
        # Return PDF file
        filename = f"emissions_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/export', methods=['GET'])
@login_required
def export_emissions():
    """Export emissions data as PDF - GET version for frontend integration"""
    try:
        from models import Scope2Emission, Scope3Emission
        # Get query parameters
        year = request.args.get('year')
        month = request.args.get('month')
        facility_id = request.args.get('facility_id')
        process_type = request.args.get('process_type')
        scope = request.args.get('scope', 'all')
        
        filters = {'year': year, 'month': month, 'facility_id': facility_id, 'process_type': process_type, 'scope': scope}
        
        emissions_data = []

        # Scope filters for SQL
        y_int = None
        if year and year != 'all':
            try: y_int = int(year)
            except: pass
            
        m_int = None
        if month and month != 'all':
            try: m_int = int(month)
            except: pass
            
        f_int = None
        if facility_id and facility_id != 'all':
            try: f_int = int(facility_id)
            except: pass

        # 1. SCOPE 1
        if scope in ['all', '1']:
            q1 = Emission.query
            if y_int: q1 = q1.filter_by(year=y_int)
            if m_int: q1 = q1.filter_by(month=m_int)
            if f_int: q1 = q1.filter_by(facility_id=f_int)
            if process_type and process_type != 'all': q1 = q1.filter_by(process_type=process_type)
            q1 = q1.filter(Emission.status != 'Draft')
            for e in q1.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 1,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': e.process_type or 'N/A',
                    'fuel_type': e.fuel_type or 'N/A',
                    'amount': e.quantity or 0,
                    'co2_emissions': e.co2_emissions or 0, 'ch4_emissions': e.ch4_emissions or 0, 'n2o_emissions': e.n2o_emissions or 0,
                    'total_co2e': e.co2e_total or 0
                })

        # 2. SCOPE 2
        if scope in ['all', '2']:
            q2 = Scope2Emission.query
            if y_int: q2 = q2.filter_by(year=y_int)
            if m_int: q2 = q2.filter_by(month=m_int)
            if f_int: q2 = q2.filter_by(facility_id=f_int)
            q2 = q2.filter(Scope2Emission.status != 'Draft')
            for e in q2.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 2,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': 'Indirect Electricity',
                    'fuel_type': e.source_type or 'Electricity',
                    'amount': e.electricity_kwh or 0,
                    'co2_emissions': 0, 'ch4_emissions': 0, 'n2o_emissions': 0,
                    'total_co2e': e.co2e or 0
                })

        # 3. SCOPE 3
        if scope in ['all', '3']:
            q3 = Scope3Emission.query
            if y_int: q3 = q3.filter_by(year=y_int)
            if m_int: q3 = q3.filter_by(month=m_int)
            if f_int: q3 = q3.filter_by(facility_id=f_int)
            q3 = q3.filter(Scope3Emission.status != 'Draft')
            for e in q3.all():
                fac = Facility.query.get(e.facility_id) if e.facility_id else None
                m_val = e.month if e.month is not None else 1
                emissions_data.append({
                    'scope': 3,
                    'date': f"{e.year or 0}-{m_val:02d}-01",
                    'facility_name': fac.name if fac else 'Unknown',
                    'process_type': e.category or 'Value Chain',
                    'fuel_type': e.sub_category or 'Scope 3',
                    'amount': e.activity_data or 0,
                    'co2_emissions': 0, 'ch4_emissions': 0, 'n2o_emissions': 0,
                    'total_co2e': e.co2e or 0
                })

        emissions_data.sort(key=lambda x: x['date'], reverse=True)
        
        # Generate PDF
        pdf_buffer = create_pdf_report(emissions_data, filters)
        
        # Return PDF file
        year_str = year if year and year != 'all' else 'all'
        month_str = month if month and month != 'all' else 'all'
        filename = f"emissions_{year_str}_{month_str}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/ogmp-export', methods=['GET'])
@login_required
def export_ogmp_excel():
    """
    Generates a 5-tab UNEP / OGMP 2.0 Standard Disclosure Workbook (Excel):
    1. Executive Summary & Asset Metadata
    2. Bottom-Up Source Inventory (L1-L4)
    3. Top-Down Measurement Campaigns (L4/L5)
    4. Reconciliation Matrix
    5. Gold Standard Progression Roadmap
    """
    try:
        year = request.args.get('year', 'all')
        year_filter = int(year) if year and year.isdigit() else None
        facility_id = request.args.get('facility_id')
        facility_filter = int(facility_id) if facility_id and facility_id.isdigit() else None

        # Prepare workbook
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default empty sheet

        # Styling definitions
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy
        sub_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")     # Blue
        accent_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")  # Teal
        gold_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")    # Amber
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        def style_header_row(ws, row_idx, fill=header_fill):
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.fill = fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        def autofit_columns(ws):
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or '')
                    if '\n' in val_str:
                        val_str = max(val_str.split('\n'), key=len)
                    max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # -------------------------------------------------------------
        # TAB 1: Executive Summary & Facility Metadata
        # -------------------------------------------------------------
        ws1 = wb.create_sheet(title="1. Executive Summary")
        ws1.views.sheetView[0].showGridLines = True
        ws1.cell(row=1, column=1, value="OGMP 2.0 METHANE EMISSIONS DISCLOSURE REPORT").font = title_font
        ws1.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Reporting Period: {year if year != 'all' else 'All Active Years'}").font = regular_font

        ws1.cell(row=4, column=1, value="Facility Name")
        ws1.cell(row=4, column=2, value="Code")
        ws1.cell(row=4, column=3, value="Segment")
        ws1.cell(row=4, column=4, value="Operator Status")
        ws1.cell(row=4, column=5, value="Country")
        ws1.cell(row=4, column=6, value="Base Year")
        ws1.cell(row=4, column=7, value="Target Gold Year")
        ws1.cell(row=4, column=8, value="Current Level")
        ws1.cell(row=4, column=9, value="Gas Production (m³)")
        ws1.cell(row=4, column=10, value="Bottom-Up CH₄ (t)")
        ws1.cell(row=4, column=11, value="Top-Down CH₄ (t)")
        ws1.cell(row=4, column=12, value="Loss Rate (%)")
        ws1.cell(row=4, column=13, value="Gold Target (%)")
        ws1.cell(row=4, column=14, value="Target Compliance")
        ws1.cell(row=4, column=15, value="Pathway Status")
        style_header_row(ws1, 4, header_fill)

        fac_q = Facility.query
        if facility_filter:
            fac_q = fac_q.filter_by(id=facility_filter)
        facilities = fac_q.all()

        row_curr = 5
        for f in facilities:
            op_st = f.operator_status or 'operated'
            b_yr = f.ogmp_membership_year or 2023
            target_yr = b_yr + (3 if op_st == 'operated' else 5)
            
            # Aggregate CH4
            em_q = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
                Emission.facility_id == f.id,
                Emission.status != 'Draft'
            )
            if year_filter: em_q = em_q.filter(Emission.year == year_filter)
            bu_ch4 = em_q.scalar() or 0.0

            # Aggregate Gas Production
            prod_q = db.session.query(db.func.sum(ProductionData.gas_amount)).filter(
                ProductionData.facility_id == f.id
            )
            if year_filter: prod_q = prod_q.filter(ProductionData.year == year_filter)
            gas_mscf = prod_q.scalar() or 0.0
            gas_m3 = gas_mscf * 28.3168

            # Top Down
            td_q = db.session.query(db.func.sum(OgmpSurvey.estimated_annual_tch4)).filter(
                OgmpSurvey.facility_id == f.id
            )
            if year_filter: td_q = td_q.filter(OgmpSurvey.year == year_filter)
            td_ch4 = td_q.scalar() or 0.0

            # Loss rate %
            ch4_vol_m3 = (bu_ch4 * 1000.0) / 0.6785 if bu_ch4 > 0 else 0.0
            loss_rate_pct = (ch4_vol_m3 / gas_m3 * 100.0) if gas_m3 > 0 else 0.0
            target_rate = 0.20 if 'upstream' in (f.segment or 'Upstream').lower() else 0.05
            comp_status = 'Compliant' if loss_rate_pct <= target_rate else 'Non-Compliant'

            # Level
            curr_lvl = 5 if td_ch4 > 0 and bu_ch4 > 0 and abs(td_ch4 - bu_ch4) / bu_ch4 <= (f.reconciliation_threshold or 20.0)/100.0 else (4 if td_ch4 > 0 else 3)
            pathway = 'Gold Standard Achieved' if curr_lvl == 5 else ('On Track' if (year_filter or 2026) <= target_yr else 'Overdue')

            ws1.cell(row=row_curr, column=1, value=f.name)
            ws1.cell(row=row_curr, column=2, value=f.code or 'N/A')
            ws1.cell(row=row_curr, column=3, value=f.segment or 'Upstream')
            ws1.cell(row=row_curr, column=4, value=op_st.replace('_', '-').title())
            ws1.cell(row=row_curr, column=5, value=f.country or 'Algeria')
            ws1.cell(row=row_curr, column=6, value=b_yr)
            ws1.cell(row=row_curr, column=7, value=target_yr)
            ws1.cell(row=row_curr, column=8, value=f"Level {curr_lvl}")
            ws1.cell(row=row_curr, column=9, value=round(gas_m3, 2))
            ws1.cell(row=row_curr, column=10, value=round(bu_ch4, 2))
            ws1.cell(row=row_curr, column=11, value=round(td_ch4, 2))
            ws1.cell(row=row_curr, column=12, value=round(loss_rate_pct, 4))
            ws1.cell(row=row_curr, column=13, value=target_rate)
            ws1.cell(row=row_curr, column=14, value=comp_status)
            ws1.cell(row=row_curr, column=15, value=pathway)

            for c in range(1, 16):
                ws1.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws1)

        # -------------------------------------------------------------
        # TAB 2: Bottom-Up Inventory (Level 1 - Level 4)
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="2. Bottom-Up Inventory")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="OGMP 2.0 SOURCE-LEVEL EMISSIONS INVENTORY (L1 - L4)").font = title_font
        
        ws2.cell(row=3, column=1, value="Record ID")
        ws2.cell(row=3, column=2, value="Facility")
        ws2.cell(row=3, column=3, value="Year")
        ws2.cell(row=3, column=4, value="Month")
        ws2.cell(row=3, column=5, value="Process / Category")
        ws2.cell(row=3, column=6, value="Equipment / Source Code")
        ws2.cell(row=3, column=7, value="Activity Quantity")
        ws2.cell(row=3, column=8, value="Unit")
        ws2.cell(row=3, column=9, value="EF Source")
        ws2.cell(row=3, column=10, value="CH₄ Emissions (t)")
        ws2.cell(row=3, column=11, value="CO₂e Total (t)")
        ws2.cell(row=3, column=12, value="OGMP Level")
        ws2.cell(row=3, column=13, value="Calculation Method")
        style_header_row(ws2, 3, sub_fill)

        em_list_q = Emission.query.filter(Emission.status != 'Draft')
        if year_filter: em_list_q = em_list_q.filter_by(year=year_filter)
        if facility_filter: em_list_q = em_list_q.filter_by(facility_id=facility_filter)
        em_list = em_list_q.order_by(Emission.year.desc(), Emission.month.desc()).limit(1500).all()

        row_curr = 4
        for em in em_list:
            fac_name = em.facility.name if em.facility else (em.facility_parent.name if em.facility_parent else 'Unknown')
            lvl = em.ogmp_level or (4 if em.factor_source == 'specific' else 3)
            ws2.cell(row=row_curr, column=1, value=em.record_id or f"EM-{em.id}")
            ws2.cell(row=row_curr, column=2, value=fac_name)
            ws2.cell(row=row_curr, column=3, value=em.year)
            ws2.cell(row=row_curr, column=4, value=em.month)
            ws2.cell(row=row_curr, column=5, value=em.process_type or 'N/A')
            ws2.cell(row=row_curr, column=6, value=em.source_type_code or em.equipment_id or 'N/A')
            ws2.cell(row=row_curr, column=7, value=em.quantity or 0)
            ws2.cell(row=row_curr, column=8, value=em.unit or '')
            ws2.cell(row=row_curr, column=9, value=em.factor_source or 'Default EF')
            ws2.cell(row=row_curr, column=10, value=round(em.ch4_emissions or 0, 4))
            ws2.cell(row=row_curr, column=11, value=round(em.co2e_total or 0, 2))
            ws2.cell(row=row_curr, column=12, value=f"Level {lvl}")
            ws2.cell(row=row_curr, column=13, value=em.calc_method or ('Facility Specific' if lvl >= 4 else 'Generic EF'))

            for c in range(1, 14):
                ws2.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws2)

        # -------------------------------------------------------------
        # TAB 3: Top-Down Measurement Surveys (Level 4/5)
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="3. Top-Down Surveys")
        ws3.views.sheetView[0].showGridLines = True
        ws3.cell(row=1, column=1, value="OGMP 2.0 SITE-LEVEL MEASUREMENT CAMPAIGNS (L4 / L5)").font = title_font
        
        ws3.cell(row=3, column=1, value="Survey ID")
        ws3.cell(row=3, column=2, value="Facility")
        ws3.cell(row=3, column=3, value="Year")
        ws3.cell(row=3, column=4, value="Survey Date")
        ws3.cell(row=3, column=5, value="Technology / Method")
        ws3.cell(row=3, column=6, value="Measured Rate (kg CH₄/hr)")
        ws3.cell(row=3, column=7, value="Operating Hours (hr/yr)")
        ws3.cell(row=3, column=8, value="Annualized Rate (tCH₄/yr)")
        ws3.cell(row=3, column=9, value="Detection Limit (kg/hr)")
        ws3.cell(row=3, column=10, value="Instrument / Vendor")
        ws3.cell(row=3, column=11, value="Reconciliation Status")
        ws3.cell(row=3, column=12, value="Operator Notes")
        style_header_row(ws3, 3, accent_fill)

        surv_q = OgmpSurvey.query
        if year_filter: surv_q = surv_q.filter_by(year=year_filter)
        if facility_filter: surv_q = surv_q.filter_by(facility_id=facility_filter)
        surveys = surv_q.order_by(OgmpSurvey.survey_date.desc()).all()

        row_curr = 4
        for s in surveys:
            fac_name = s.facility.name if s.facility else (s.facility_parent.name if s.facility_parent else 'Unknown')
            ws3.cell(row=row_curr, column=1, value=f"OGMP-{s.id}")
            ws3.cell(row=row_curr, column=2, value=fac_name)
            ws3.cell(row=row_curr, column=3, value=s.year)
            ws3.cell(row=row_curr, column=4, value=s.survey_date)
            ws3.cell(row=row_curr, column=5, value=s.survey_type)
            ws3.cell(row=row_curr, column=6, value=s.measured_rate_kg_hr)
            ws3.cell(row=row_curr, column=7, value=s.operating_hours_year or 8760)
            ws3.cell(row=row_curr, column=8, value=s.estimated_annual_tch4)
            ws3.cell(row=row_curr, column=9, value=s.detection_threshold or 'N/A')
            ws3.cell(row=row_curr, column=10, value=s.instrument_vendor or 'N/A')
            ws3.cell(row=row_curr, column=11, value=s.reconciliation_status or 'Reconciled')
            ws3.cell(row=row_curr, column=12, value=s.operator_notes or '')

            for c in range(1, 13):
                ws3.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws3)

        # -------------------------------------------------------------
        # TAB 4: Reconciliation Matrix (Bottom-Up vs Top-Down)
        # -------------------------------------------------------------
        ws4 = wb.create_sheet(title="4. Reconciliation Matrix")
        ws4.views.sheetView[0].showGridLines = True
        ws4.cell(row=1, column=1, value="OGMP 2.0 BOTTOM-UP VS TOP-DOWN RECONCILIATION MATRIX").font = title_font

        ws4.cell(row=3, column=1, value="Facility")
        ws4.cell(row=3, column=2, value="Reporting Year")
        ws4.cell(row=3, column=3, value="Segment")
        ws4.cell(row=3, column=4, value="Bottom-Up Total (tCH₄)")
        ws4.cell(row=3, column=5, value="Top-Down Survey Total (tCH₄)")
        ws4.cell(row=3, column=6, value="Reconciliation Variance (%)")
        ws4.cell(row=3, column=7, value="Threshold (%)")
        ws4.cell(row=3, column=8, value="Discrepancy Flag")
        ws4.cell(row=3, column=9, value="Reconciliation Status")
        ws4.cell(row=3, column=10, value="Operator Explanation & Remediation")
        style_header_row(ws4, 3, gold_fill)

        row_curr = 4
        for f in facilities:
            # Bottom-Up
            bu_q = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
                Emission.facility_id == f.id,
                Emission.status != 'Draft'
            )
            if year_filter: bu_q = bu_q.filter(Emission.year == year_filter)
            bu_total = bu_q.scalar() or 0.0

            # Top-Down
            td_q = db.session.query(db.func.sum(OgmpSurvey.estimated_annual_tch4)).filter(
                OgmpSurvey.facility_id == f.id
            )
            if year_filter: td_q = td_q.filter(OgmpSurvey.year == year_filter)
            td_total = td_q.scalar() or 0.0

            thresh = f.reconciliation_threshold or 20.0
            var_pct = round(((td_total - bu_total) / bu_total * 100.0), 2) if bu_total > 0 and td_total > 0 else 0.0
            is_flagged = abs(var_pct) > thresh if (bu_total > 0 and td_total > 0) else False
            rec_status = 'Pending Measurement' if td_total == 0 else ('Reconciled' if not is_flagged else 'Discrepancy Flagged')

            ws4.cell(row=row_curr, column=1, value=f.name)
            ws4.cell(row=row_curr, column=2, value=year if year != 'all' else 'All Years')
            ws4.cell(row=row_curr, column=3, value=f.segment or 'Upstream')
            ws4.cell(row=row_curr, column=4, value=round(bu_total, 2))
            ws4.cell(row=row_curr, column=5, value=round(td_total, 2))
            ws4.cell(row=row_curr, column=6, value=f"{var_pct:+.2f}%" if td_total > 0 else "N/A")
            ws4.cell(row=row_curr, column=7, value=f"±{thresh}%")
            ws4.cell(row=row_curr, column=8, value="FLAGGED (> Threshold)" if is_flagged else "PASS")
            ws4.cell(row=row_curr, column=9, value=rec_status)
            ws4.cell(row=row_curr, column=10, value="Within acceptable variance bounds" if not is_flagged else "Site measurement exceeds bottom-up inventory. Investigate uncombusted slip or uninventoried vent sources.")

            for c in range(1, 11):
                ws4.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws4)

        # -------------------------------------------------------------
        # TAB 5: Gold Standard Progression Roadmap
        # -------------------------------------------------------------
        ws5 = wb.create_sheet(title="5. Gold Standard Roadmap")
        ws5.views.sheetView[0].showGridLines = True
        ws5.cell(row=1, column=1, value="OGMP 2.0 GOLD STANDARD PATHWAY & MILESTONE TRACKER").font = title_font

        ws5.cell(row=3, column=1, value="Facility")
        ws5.cell(row=3, column=2, value="Operator Type")
        ws5.cell(row=3, column=3, value="OGMP Base Year")
        ws5.cell(row=3, column=4, value="Compliance Timeline")
        ws5.cell(row=3, column=5, value="Target Deadline Year")
        ws5.cell(row=3, column=6, value="Current Level")
        ws5.cell(row=3, column=7, value="Milestone Status")
        ws5.cell(row=3, column=8, value="Next Mandatory Action")
        style_header_row(ws5, 3, header_fill)

        row_curr = 4
        for f in facilities:
            op_st = f.operator_status or 'operated'
            b_yr = f.ogmp_membership_year or 2023
            timeline = "3 Years (Operated Asset)" if op_st == 'operated' else "5 Years (Non-Operated Asset)"
            target_yr = b_yr + (3 if op_st == 'operated' else 5)
            
            # Check survey existence
            has_survey = OgmpSurvey.query.filter_by(facility_id=f.id).first() is not None
            curr_lvl = "Level 5 (Reconciled)" if has_survey else "Level 3 (Generic Factors)"
            status = "Gold Standard Achieved" if has_survey else ("On Track" if 2026 <= target_yr else "Action Plan Required")
            action = "Maintain annual top-down measurement campaigns" if has_survey else "Schedule aerial / satellite top-down measurement and upgrade to equipment-level EFs"

            ws5.cell(row=row_curr, column=1, value=f.name)
            ws5.cell(row=row_curr, column=2, value=op_st.replace('_', '-').title())
            ws5.cell(row=row_curr, column=3, value=b_yr)
            ws5.cell(row=row_curr, column=4, value=timeline)
            ws5.cell(row=row_curr, column=5, value=target_yr)
            ws5.cell(row=row_curr, column=6, value=curr_lvl)
            ws5.cell(row=row_curr, column=7, value=status)
            ws5.cell(row=row_curr, column=8, value=action)

            for c in range(1, 9):
                ws5.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws5)

        # Save to buffer and send
        output_buffer = BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = f"OGMP_2.0_Methane_Disclosure_{year if year != 'all' else 'AllYears'}.xlsx"
        return send_file(
            output_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

