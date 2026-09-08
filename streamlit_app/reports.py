import io
import pandas as pd
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
except ImportError:
    pass

try:
    from docx import Document
except ImportError:
    pass


def generate_excel_report(registro_df: pd.DataFrame, comparativa_df: pd.DataFrame, dataset_info_df: pd.DataFrame, raw_dataset: pd.DataFrame, best_model: str) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        info_df = pd.DataFrame([
            {"Propiedad": "Fecha de reporte", "Valor": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"Propiedad": "Mejor Modelo Seleccionado", "Valor": best_model},
        ])
        info_df.to_excel(writer, sheet_name='Info_General', index=False)
        dataset_info_df.to_excel(writer, sheet_name='Resumen_Dataset', index=False)
        raw_dataset.to_excel(writer, sheet_name='Dataset_Completo', index=False)
        registro_df.to_excel(writer, sheet_name='Registro_Modelos', index=False)
        comparativa_df.to_excel(writer, sheet_name='Tabla_Comparativa', index=False)
    
    return output.getvalue()


def _add_df_to_word(doc, df, title):
    doc.add_heading(title, level=1)
    df_stringified = df.copy()
    for col in df_stringified.columns:
        if df_stringified[col].dtype.kind in 'fc':
            df_stringified[col] = df_stringified[col].round(4)
            
    table = doc.add_table(rows=1, cols=len(df_stringified.columns))
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(df_stringified.columns):
        hdr_cells[i].text = str(col)
        
    for index, row in df_stringified.iterrows():
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)
    doc.add_paragraph("")


def generate_word_report(registro_df: pd.DataFrame, comparativa_df: pd.DataFrame, dataset_info_df: pd.DataFrame, best_model: str) -> bytes:
    doc = Document()
    doc.add_heading('Reporte de Evaluación de Modelos IA', 0)
    
    doc.add_paragraph(f'Fecha de generación: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    p = doc.add_paragraph('El mejor modelo seleccionado fue: ')
    p.add_run(best_model).bold = True
    
    _add_df_to_word(doc, dataset_info_df, 'Cantidad de Datos y Campos')
    _add_df_to_word(doc, registro_df, 'Registro de Modelos')
    _add_df_to_word(doc, comparativa_df, 'Tabla Comparativa de Modelos')
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _add_df_to_pdf(elements, df, title, styles, t_style):
    elements.append(Paragraph(title, styles['Heading2']))
    
    data_list = [df.columns.tolist()]
    for index, row in df.iterrows():
        formatted_row = []
        for val in row:
            if isinstance(val, float):
                formatted_row.append(f"{val:.4f}")
            else:
                formatted_row.append(str(val))
        data_list.append(formatted_row)
        
    table = Table(data_list)
    table.setStyle(t_style)
    elements.append(table)
    elements.append(Spacer(1, 20))


def generate_pdf_report(registro_df: pd.DataFrame, comparativa_df: pd.DataFrame, dataset_info_df: pd.DataFrame, best_model: str) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter))
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    
    elements.append(Paragraph("Reporte de Evaluación de Modelos IA", title_style))
    elements.append(Paragraph(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
    elements.append(Paragraph(f'<b>Mejor modelo seleccionado: {best_model}</b>', normal_style))
    elements.append(Spacer(1, 20))
    
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2a3f5f")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f4f4")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ])
    
    _add_df_to_pdf(elements, dataset_info_df, "Cantidad de Datos y Campos Entrenados", styles, t_style)
    _add_df_to_pdf(elements, registro_df, "Registro de Modelos", styles, t_style)
    _add_df_to_pdf(elements, comparativa_df, "Tabla Comparativa de Modelos", styles, t_style)
    
    doc.build(elements)
    
    return output.getvalue()
