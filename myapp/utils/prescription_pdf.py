"""
Prescription PDF generation for Render deployment.
Generates PDFs on-the-fly instead of relying on stored files.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import json


def generate_prescription_pdf(prescription):
    """
    Generate a prescription PDF from prescription object.
    Creates PDF in memory without relying on stored files.
    """
    try:
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#E74C3C'),
            spaceAfter=12,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=6,
            spaceBefore=6
        )
        
        # Build content
        content = []
        
        # Header
        content.append(Paragraph("MediSafe+", title_style))
        content.append(Paragraph("Medical Prescription", styles['Heading2']))
        content.append(Spacer(1, 0.2*inch))
        
        # Prescription details
        appointment = prescription.live_appointment.appointment if prescription.live_appointment else None
        doctor = appointment.doctor if appointment else None
        patient = appointment.patient if appointment else None
        
        # Patient information
        content.append(Paragraph("Patient Information", heading_style))
        patient_data = [
            ['Name:', f"{patient.user.username}" if patient else "N/A"],
            ['Date:', datetime.now().strftime('%B %d, %Y')],
            ['Prescription #:', prescription.prescription_number or 'N/A'],
        ]
        patient_table = Table(patient_data, colWidths=[1.5*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        content.append(patient_table)
        content.append(Spacer(1, 0.2*inch))
        
        # Doctor information
        content.append(Paragraph("Doctor Information", heading_style))
        doctor_data = [
            ['Doctor:', f"{doctor.user.username}" if doctor else "N/A"],
            ['Specialization:', f"{doctor.specialization}" if doctor else "N/A"],
        ]
        doctor_table = Table(doctor_data, colWidths=[1.5*inch, 4*inch])
        doctor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        content.append(doctor_table)
        content.append(Spacer(1, 0.2*inch))
        
        # Medicines
        content.append(Paragraph("Medicines", heading_style))
        medicines = []
        if prescription.medicines:
            try:
                if isinstance(prescription.medicines, str):
                    meds = json.loads(prescription.medicines)
                else:
                    meds = prescription.medicines
                
                for med in meds if isinstance(meds, list) else [meds]:
                    med_name = med.get('name', 'Unknown') if isinstance(med, dict) else med
                    med_dosage = med.get('dosage', '') if isinstance(med, dict) else ''
                    med_frequency = med.get('frequency', '') if isinstance(med, dict) else ''
                    med_duration = med.get('duration', '') if isinstance(med, dict) else ''
                    
                    medicines.append([
                        med_name,
                        med_dosage,
                        med_frequency,
                        med_duration
                    ])
            except:
                medicines.append(['Unable to parse medicines', '', '', ''])
        else:
            medicines.append(['No medicines prescribed', '', '', ''])
        
        medicines_table = Table(
            [['Medicine', 'Dosage', 'Frequency', 'Duration']] + medicines,
            colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch]
        )
        medicines_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')]),
        ]))
        content.append(medicines_table)
        content.append(Spacer(1, 0.2*inch))
        
        # Notes
        if prescription.notes:
            content.append(Paragraph("Doctor's Notes", heading_style))
            content.append(Paragraph(prescription.notes, styles['BodyText']))
            content.append(Spacer(1, 0.2*inch))
        
        # Footer
        content.append(Spacer(1, 0.3*inch))
        footer_text = "This prescription was generated by MediSafe+ Medical System. Please follow doctor's instructions carefully."
        content.append(Paragraph(footer_text, styles['Normal']))
        
        # Generate PDF
        doc.build(content)
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"Error generating prescription PDF: {str(e)}")
        return None
