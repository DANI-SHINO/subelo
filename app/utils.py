from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import random
from app.models import Usuario, Prestamo
from flask import make_response
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from app.extensions import mail
from flask_mail import Message
from datetime import date, timedelta
import os

def generar_reporte_con_plantilla(atrasados):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 📌 Fondo base
    c.drawImage("static/imagenes/plantilla.png", 0, 0, width=width, height=height)

    # Título
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkgreen)
    c.drawString(50, height - 100, "Reporte de Libros Atrasados")

    # Datos tabla
    data = [["#", "Libro", "Usuario", "Fecha Vencida"]]
    for idx, p in enumerate(atrasados, start=1):
        data.append([
            str(idx),
            p.libro.titulo,
            p.usuario.correo,
            p.fecha_devolucion_esperada.strftime('%Y-%m-%d')
        ])

    # Tabla estilizada
    table = Table(data, colWidths=[40, 200, 200, 100])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    table.setStyle(style)

    # Posición tabla
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 300)

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def generar_reporte_prestados(prestados):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 📌 Fondo base
    ruta = os.path.join(os.getcwd(), 'static', 'imagenes', 'plantilla.png')
    c.drawImage(ruta, 0, 0, width=width, height=height)

    # 📌 Título
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.darkblue)
    c.drawString(50, height - 100, "📑 Reporte de Libros Más Prestados")

    # 📌 Datos tabla
    data = [["#", "Título", "Autor", "Total Préstamos"]]
    for idx, libro in enumerate(prestados, start=1):
        data.append([
            str(idx),
            libro.titulo,
            libro.autor,
            str(libro.total)
        ])

    # 📌 Tabla estilizada
    table = Table(data, colWidths=[40, 220, 150, 100])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 300)

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf



def generar_reporte_populares(populares):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 📌 Fondo base
    ruta = os.path.join(os.getcwd(), 'static', 'imagenes', 'plantilla.png')
    c.drawImage(ruta, 0, 0, width=width, height=height)

    # 📌 Título
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.purple)
    c.drawString(50, height - 100, "🌟 Reporte de Libros Populares")

    # 📌 Datos tabla
    data = [["#", "Título", "Autor", "Préstamos", "Reservas", "Total"]]
    for idx, libro in enumerate(populares, start=1):
        data.append([
            str(idx),
            libro.titulo,
            libro.autor,
            str(libro.prestamos),
            str(libro.reservas),
            str(libro.total)
        ])

    # 📌 Tabla estilizada
    table = Table(data, colWidths=[40, 150, 130, 70, 70, 70])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 300)

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generar_token(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='recuperar-contrasena')

def verificar_token(token, max_age=3600):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='recuperar-contrasena', max_age=max_age)
    except:
        return None
    return email

def generar_llave_prestamo():
    while True:
        nueva_llave = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
        if not Usuario.query.filter_by(llave_prestamo=nueva_llave).first():
            return nueva_llave

# app/utils.py

def enviar_recordatorios(app):
    with app.app_context():
        mañana = date.today() + timedelta(days=1)
        prestamos = Prestamo.query.filter(
            Prestamo.estado == 'activo',
            Prestamo.fecha_devolucion_esperada == mañana
        ).all()

        for prestamo in prestamos:
            usuario = prestamo.usuario
            libro = prestamo.libro

            msg = Message(
                '⏰ Recordatorio de Devolución',
                sender='noreply@biblioteca.com',
                recipients=[usuario.correo]
            )
            msg.body = f"""
Hola {usuario.nombre},

Te recordamos que debes devolver el libro "{libro.titulo}" mañana.

📅 Fecha de devolución esperada: {prestamo.fecha_devolucion_esperada}

¡Gracias por usar nuestra biblioteca!

Biblioteca Avocado
"""
            mail.send(msg)



