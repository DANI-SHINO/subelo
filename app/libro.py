from app.models import db, Libro, Prestamo
from datetime import datetime, timedelta

def prestar_libro(libro, usuario):
    if libro.cantidad_disponible <= 0:
        return "No hay ejemplares disponibles"
    prestamo = Prestamo(
        libro_id=libro.id,
        usuario_id=usuario.id,
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_esperada=datetime.utcnow() + timedelta(days=7),
        estado='prestado'
    )
    libro.cantidad_disponible -= 1
    libro.disponible = libro.cantidad_disponible > 0
    db.session.add(prestamo)
    db.session.commit()
    return "Préstamo realizado correctamente"

def devolver_libro(prestamo):
    prestamo.estado = 'devuelto'
    prestamo.fecha_devolucion_real = datetime.utcnow()
    libro = Libro.query.get(prestamo.libro_id)
    libro.cantidad_disponible += 1
    libro.disponible = libro.cantidad_disponible > 0
    db.session.commit()
    return "Libro devuelto correctamente"

def eliminar_libro(libro_id):
    libro = Libro.query.get(libro_id)
    if not libro:
        return "Libro no encontrado"
    if libro.cantidad_disponible < libro.cantidad_total:
        return "No se puede eliminar: hay ejemplares prestados."
    libro.marcar_como_eliminado()
    db.session.commit()
    return "Libro marcado como eliminado"
