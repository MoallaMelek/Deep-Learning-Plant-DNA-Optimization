from pathlib import Path

def generate_pdf(html_file: str, output_pdf: str = None) -> str:
    import pdfkit
    if output_pdf is None:
        output_pdf = html_file.replace('.html', '.pdf')
    if not Path(html_file).exists():
        return None
    try:
        config  = pdfkit.configuration(
            wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        )
        options = {'enable-local-file-access': '', 'quiet': ''}
        pdfkit.from_file(html_file, output_pdf,
                        configuration=config, options=options)
        return output_pdf
    except Exception as e:
        print(f'PDF error: {e}')
        return None

def generate_fiche_pdf(engine, rag, sequence, accession='', output_dir='.'):
    from fiche_generator import generate_fiche
    html_path = f'{output_dir}/fiche_{accession or "seq"}.html'
    pdf_path  = f'{output_dir}/fiche_{accession or "seq"}.pdf'
    pred = engine.predict_trait(sequence)
    engine._last_xgb_prediction = pred
    generate_fiche(engine=engine, rag=rag, sequence=sequence,
                   accession=accession, output_file=html_path)
    return generate_pdf(html_path, pdf_path)