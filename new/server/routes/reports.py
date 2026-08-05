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
from models import Emission, Facility

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
