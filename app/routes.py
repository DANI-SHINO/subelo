from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import extract, func
from time import time
from datetime import timedelta, date
import os
import requests
# Importa las extensiones correctamente
from app.extensions import db, login_manager, mail
from app.models import Usuario, Libro, Prestamo, Reserva, Favorito, HistorialReporte
from app.forms import RegistroForm, LibroForm, EditarLibroForm, EditarReservaForm, NuevaReservaForm, PrestamoForm, ReservaLectorForm, AgregarLectorPresencialForm,  EditarUsuarioForm
from app.utils import verificar_token, generar_token, generar_reporte_con_plantilla, generar_reporte_populares, generar_reporte_prestados
from app.libro import prestar_libro, devolver_libro
from PIL import Image



main = Blueprint('main', __name__)
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def roles_requeridos(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main.before_app_request
def actualizar_reservas_vencidas():
    hoy = date.today()

    reservas_vencidas = Reserva.query.filter(
        Reserva.estado == 'activa',
        Reserva.fecha_expiracion < hoy
    ).all()

    for reserva in reservas_vencidas:
        reserva.estado = 'vencida'
        if reserva.libro:
            reserva.libro.cantidad_disponible += 1
            reserva.libro.actualizar_estado()
        current_app.logger.info(f"Reserva #{reserva.id} marcada como vencida.")

    if reservas_vencidas:
        db.session.commit()

@main.before_app_request
def marcar_prestamos_atrasados():
    hoy = date.today()
    prestamos = Prestamo.query.filter(
        Prestamo.estado == 'activo',
        Prestamo.fecha_devolucion_esperada < hoy
    ).all()

    for prestamo in prestamos:
        prestamo.estado = 'atrasado'
        current_app.logger.info(f"Préstamo #{prestamo.id} marcado como atrasado.")
    
    if prestamos:
        db.session.commit()


@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    libros = Libro.query.filter(Libro.estado != 'eliminado').paginate(page=page, per_page=12)
    # Detectar rol actual (si hay usuario logueado)
    rol = current_user.rol if current_user.is_authenticated else None

    return render_template('index.html', libros=libros, rol=rol)


@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        # Obtener todos los datos del formulario
        nombre = form.nombre.data
        apellido = form.apellido.data
        correo = form.correo.data
        documento = form.documento.data
        direccion = form.direccion.data
        telefono = form.telefono.data
        fecha_nacimiento = form.fecha_nacimiento.data
        password = form.password.data

        # Validar duplicados extra (opcional, ya validado en form)
        if Usuario.query.filter_by(correo=correo).first():
            flash('Correo no disponible.', 'danger')
            return redirect(url_for('main.registro'))
        if Usuario.query.filter_by(documento=documento).first():
            flash('Número de documento ya registrado.', 'danger')
            return redirect(url_for('main.registro'))

        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            documento=documento,
            direccion=direccion,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento,
            rol='lector',
            activo=True
        )

        # Generar llave_prestamo de préstamo y contraseña
        nuevo_usuario.generar_llave_prestamo()
        nuevo_usuario.set_password(password)

        # Guardar en base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('registro.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(correo=correo, activo=True).first()

        if usuario and usuario.check_password(password):
            # ✅ Validar rol prohibido antes de permitir login
            if usuario.rol == 'lector*':
                flash('Tu cuenta no está habilitada para acceder al sistema.', 'danger')
                return redirect(url_for('main.login'))

            login_user(usuario)
            flash('Has iniciado sesión.', 'success')

            # ✅ Redirección según rol válido
            if usuario.rol == 'administrador':
                return redirect(url_for('main.index'))
            elif usuario.rol == 'bibliotecario':
                return redirect(url_for('main.index'))
            elif usuario.rol == 'lector':
                return redirect(url_for('main.catalogo'))
            else:
                return redirect(url_for('main.index'))

        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('main.login'))

    return render_template('login.html')



@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('main.index'))

@main.route('/usuarios')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@main.route('/usuarios/<int:usuario_id>/toggle', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def toggle_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.nombre == 'admin':
        flash('No se puede desactivar al administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    if current_user.rol == 'bibliotecario' and usuario.rol == 'administrador':
        flash('No tienes permiso para modificar a un administrador.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f"El usuario '{usuario.nombre}' ha sido {estado}.", 'success')
    return redirect(url_for('main.lista_usuarios'))
    
@main.route('/usuarios/<int:usuario_id>/cambiar_rol', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def cambiar_rol(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.nombre == 'admin':
        flash('No se puede cambiar el rol del administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    nuevo_rol = request.form.get('rol')

    if nuevo_rol not in ['lector', 'bibliotecario', 'administrador']:
        flash('Rol inválido.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash('Rol actualizado correctamente.', 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/admin/inicio', endpoint='inicio')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def admin_inicio():
    return render_template('admin.html', version=time())

@main.route('/admin/inicio-contenido')
@login_required
@roles_requeridos('administrador')
def inicio_contenido():
    total_administradores = Usuario.query.filter_by(rol='administrador').count()
    total_lectores = Usuario.query.filter_by(rol='lector').count()
    total_libros = Libro.query.count()
    total_prestamos = Prestamo.query.count() if 'Prestamo' in globals() else 0
    total_reservas = Reserva.query.count() if 'Reserva' in globals() else 0


    return render_template('inicio.html',
        total_administradores=total_administradores,
        total_lectores=total_lectores,
        total_libros=total_libros,
        total_prestamos=total_prestamos,
        total_reservas=total_reservas,

    )

@main.route('/api/datos_libro/<isbn>')
def api_datos_libro(isbn):

    ol_url_bibkeys = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"

    titulo = autores = editorial = fecha = portada_url = descripcion = ''
    categoria = None

    try:
        response_bibkeys = requests.get(ol_url_bibkeys)
        response_bibkeys.raise_for_status()
        data_bibkeys = response_bibkeys.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al consultar OpenLibrary (bibkeys): {e}")
        return jsonify({"success": False, "error": "Error al obtener datos de OpenLibrary"})

    if f"ISBN:{isbn}" in data_bibkeys:
        libro_data_ol = data_bibkeys[f"ISBN:{isbn}"]

        titulo = libro_data_ol.get('title', '')
        autores = ', '.join(a['name'] for a in libro_data_ol.get('authors', [])) if libro_data_ol.get('authors') else ''
        editorial = ', '.join(p['name'] for p in libro_data_ol.get('publishers', [])) if 'publishers' in libro_data_ol else ''
        fecha = libro_data_ol.get('publish_date', None)

        desc_raw = libro_data_ol.get('description')
        if isinstance(desc_raw, dict):
            descripcion = desc_raw.get('value', '')
        elif isinstance(desc_raw, str):
            descripcion = desc_raw

        if 'cover' in libro_data_ol:
            portada_url = libro_data_ol['cover'].get('large') or libro_data_ol['cover'].get('medium') or libro_data_ol['cover'].get('small')
        if not portada_url and isbn:
            portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
            try:
                check_resp = requests.head(portada_url)
                if not check_resp.ok:
                    portada_url = None
            except requests.exceptions.RequestException:
                portada_url = None

        # Diccionario de mapeo de categorías
        mapeo_categorias = {
            "fiction": "novela",
            "novel": "novela",
            "detective and mystery stories": "novela",
            "police procedural": "thriller",
            "science fiction": "ciencia_ficcion",
            "fantasy": "fantasía",
            "thrillers": "thriller",
            "horror": "terror",
            "romance": "romance",
            "historical fiction": "novela_historica",
            "history": "historia",
            "biography": "biografia",
            "short stories": "cuento",
            "poetry": "poesia",
            "drama": "teatro",
            "comedies": "comedia",
            "juvenile fiction": "juvenil",
            "young adult fiction": "juvenil",
            "graphic novels": "historieta",
            "comics": "historieta",
            "philosophy": "filosofia",
            "essays": "ensayo",
            "true crime": "ficcion_criminal",
            "crime fiction": "ficcion_criminal",
            "political satire": "sátira",
            "satire": "sátira",
            "classic fiction": "clasico",
            "classic literature": "clasico",
            "magical realism": "realismo_magico"
        }

        edition_key = libro_data_ol.get('key')
        subjects = []
        if edition_key and edition_key.startswith('/books/'):
            olid = edition_key.split('/')[-1]
            ol_url_edition = f"https://openlibrary.org/books/{olid}.json"

            try:
                response_edition = requests.get(ol_url_edition)
                response_edition.raise_for_status()
                edition_data_full = response_edition.json()

                if not descripcion:
                    desc_ed = edition_data_full.get('description')
                    if isinstance(desc_ed, dict):
                        descripcion = desc_ed.get('value', '')
                    elif isinstance(desc_ed, str):
                        descripcion = desc_ed

                subjects = edition_data_full.get('subjects', [])

                # Fallback a works si no hay subjects
                if not subjects and 'works' in edition_data_full:
                    work_key = edition_data_full['works'][0]['key']
                    ol_url_work = f"https://openlibrary.org{work_key}.json"
                    try:
                        response_work = requests.get(ol_url_work)
                        response_work.raise_for_status()
                        work_data = response_work.json()

                        subjects = work_data.get('subjects', [])

                        if not descripcion:
                            desc_work = work_data.get('description')
                            if isinstance(desc_work, dict):
                                descripcion = desc_work.get('value', '')
                            elif isinstance(desc_work, str):
                                descripcion = desc_work

                    except requests.exceptions.RequestException as e:
                        print(f"Error obteniendo Work: {e}")
                    except ValueError as e:
                        print(f"Error parseando Work: {e}")

            except requests.exceptions.RequestException as e:
                print(f"Error obteniendo edición: {e}")
            except ValueError as e:
                print(f"Error parseando edición: {e}")

        # --- Mapeo final de categoría ---
        categoria_mapeada = None

        for s in subjects:
            s_lower = s.lower().strip()
            if s_lower in mapeo_categorias:
                categoria_mapeada = mapeo_categorias[s_lower]
                break

        if not categoria_mapeada:
            for s in subjects:
                s_lower = s.lower().strip()
                for key in mapeo_categorias:
                    if key in s_lower:
                        categoria_mapeada = mapeo_categorias[key]
                        break
                if categoria_mapeada:
                    break

        if not categoria_mapeada:
            for s in subjects:
                s_lower = s.lower().strip()
                if "fiction" in s_lower:
                    categoria_mapeada = "novela"
                    break
                elif "science" in s_lower:
                    categoria_mapeada = "ciencia_ficcion"
                    break
                elif "fantasy" in s_lower:
                    categoria_mapeada = "fantasía"
                    break
                elif "horror" in s_lower:
                    categoria_mapeada = "terror"
                    break
                elif "biography" in s_lower:
                    categoria_mapeada = "biografia"
                    break
                elif "history" in s_lower:
                    categoria_mapeada = "historia"
                    break
                elif "political" in s_lower:
                    categoria_mapeada = "sátira"
                    break

        # Fallback final: si no mapea nada o no hay subjects => 'otros'
        if not categoria_mapeada:
            categoria_mapeada = "otros"

        categoria = categoria_mapeada

        return jsonify({
            "success": True,
            "titulo": titulo or '',
            "autor": autores or '',
            "editorial": editorial or '',
            "fecha_publicacion": fecha or '',
            "isbn": isbn,
            "portada_url": portada_url or '',
            "descripcion": descripcion or '',
            "categoria": categoria or ''
        })

    return jsonify({"success": False, "error": "Libro no encontrado en OpenLibrary"})


@main.route('/api/dashboard_data')
@login_required
@roles_requeridos('administrador')
def dashboard_data():
    data = {
        'total_administradores': Usuario.query.filter_by(rol='administrador').count(),
        'total_lectores': Usuario.query.filter_by(rol='lector').count(),
        'total_libros': Libro.query.count(),
        'total_prestamos': Prestamo.query.count() if 'Prestamo' in globals() else 0,
        'total_reservas': Reserva.query.count() if 'Reserva' in globals() else 0,
        'total_reportes': HistorialReporte.query.count(),
    }
    return jsonify(data)


@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)

@main.route('/admin/usuarios/editar_formulario/<int:id>')
@login_required
@roles_requeridos('administrador')
def editar_formulario_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    form = EditarUsuarioForm(
        nombre=usuario.nombre,
        correo=usuario.correo,
        direccion=usuario.direccion,
        rol=usuario.rol
    )
    return render_template(
        'partials/usuarios_editar.html',
        form=form,
        usuario=usuario
    )

@main.route('/admin/usuarios/editar/<int:id>', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    form = EditarUsuarioForm()

    if form.validate_on_submit():
        usuario.nombre = form.nombre.data
        usuario.correo = form.correo.data
        usuario.direccion = form.direccion.data
        usuario.rol = form.rol.data

        db.session.commit()
        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for('main.mostrar_usuarios'))
    else:
        flash("Error al validar el formulario.", "danger")

    return redirect(url_for('main.mostrar_usuarios'))


@main.route("/admin/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario eliminado"})

# rutas de bibliotecario/usuarios
from flask import jsonify

@main.route('/admin/usuarios/agregar', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def agregar_usuario():
    form = AgregarLectorPresencialForm()

    if form.validate_on_submit():
        nombre = form.nombre.data.strip()
        correo = form.correo.data.strip()
        documento = form.documento.data.strip()
        direccion = form.direccion.data.strip()

        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido='-',
            correo=correo,
            documento=documento,
            direccion=direccion,
            telefono='-',
            fecha_nacimiento=date(2000, 1, 1),
            rol='lector*',
            activo=True
        )
        nuevo_usuario.generar_llave_prestamo()
        nuevo_usuario.set_password('000000')

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return jsonify({"success": True, "mensaje": "Lector presencial registrado correctamente."})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "mensaje": "Error al registrar usuario.", "errores": str(e)})

    elif form.errors:
        print("ERRORES:", form.errors)
        return jsonify({"success": False, "mensaje": "Errores de validación.", "errores": form.errors})
        

    return render_template('registro_fragmento.html', form=form)

#rutas de admin/libros
@main.route('/admin/libros/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def nuevo_libro():
    form = LibroForm()

    isbn_param = request.args.get('isbn')
    if isbn_param and request.method == 'GET':
        # Autocompleta desde tu API interna
        try:
            api_response = requests.get(url_for('main.api_datos_libro', isbn=isbn_param, _external=True))
            api_response.raise_for_status()
            data = api_response.json()

            if data.get("success"):
                form.isbn.data = data.get('isbn', '')
                form.titulo.data = data.get('titulo', '')
                form.autor.data = data.get('autor', '')
                form.editorial.data = data.get('editorial', '')
                form.descripcion.data = data.get('descripcion', '')
                form.categoria.data = data.get('categoria', '')
                raw_date = data.get('fecha_publicacion', '')
                if raw_date:
                    try:
                        if len(raw_date) == 4 and raw_date.isdigit():
                            raw_date = f"{raw_date}-01-01"
                        elif len(raw_date) == 7:
                            raw_date = f"{raw_date}-01"
                        form.fecha_publicacion.data = datetime.strptime(raw_date, '%Y-%m-%d').date()
                    except ValueError:
                        form.fecha_publicacion.data = None
                else:
                    form.fecha_publicacion.data = None

                form.portada_url.data = data.get('portada_url')
            else:
                flash(f"No se pudieron obtener datos para ISBN {isbn_param}: {data.get('error', 'Error desconocido')}", 'warning')
        except requests.exceptions.RequestException as e:
            flash(f"Error de red al consultar la API interna: {e}", 'danger')
        except ValueError as e:
            flash(f"Error al procesar la respuesta de la API interna: {e}", 'danger')

    if form.validate_on_submit():
        isbn = form.isbn.data
        libro_existente = Libro.query.filter_by(isbn=isbn).first()
        if libro_existente:
            flash('Ya existe un libro con ese ISBN.', 'danger')
        else:
            cantidad_total = form.cantidad_total.data or 0

            # Procesa la portada subida
            portada_file = form.portada.data  # viene del FileField
            portada_url = form.portada_url.data or '/static/imagenes/portada_default.png'

            if portada_file:
                filename = secure_filename(portada_file.filename)
                carpeta_portadas = os.path.join(current_app.root_path, 'static', 'portadas')
                os.makedirs(carpeta_portadas, exist_ok=True)
                ruta_completa = os.path.join(carpeta_portadas, filename)
                portada_file.save(ruta_completa)
                portada_url = f'/static/portadas/{filename}'

            nuevo_libro = Libro(
                isbn=isbn,
                titulo=form.titulo.data,
                autor=form.autor.data,
                descripcion=form.descripcion.data,
                categoria=form.categoria.data,
                editorial=form.editorial.data,
                fecha_publicacion=form.fecha_publicacion.data,
                cantidad_total=cantidad_total,
                cantidad_disponible=cantidad_total,
                portada_url=portada_url
            )
            nuevo_libro.actualizar_estado()

            db.session.add(nuevo_libro)
            db.session.commit()

            flash('Libro creado exitosamente.', 'success')
            return redirect(url_for('main.mostrar_libros'))

    return render_template('nuevo_libro.html', form=form)

@main.route('/admin/libros/mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_libros():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    return render_template('libros_tabla.html', libros=libros)

@main.route('/admin/libros/eliminar/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def eliminar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    # Solo eliminamos si no hay préstamos activos
    if libro.cantidad_disponible < libro.cantidad_total:
        flash('No se puede eliminar: hay ejemplares prestados.', 'danger')
        return redirect(url_for('main.admin_libros'))

    libro.marcar_como_eliminado()
    db.session.commit()
    flash('Libro marcado como eliminado.', 'success')
    return redirect(url_for('main.admin_libros'))

@main.route('/admin/libros/editar/<int:libro_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def editar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    form = EditarLibroForm(obj=libro)

    if form.validate_on_submit():
        # Nueva cantidad total y cantidad disponible del formulario
        nueva_cantidad_total = form.cantidad_total.data
        nueva_cantidad_disponible = form.cantidad_disponible.data

        # Validar que la cantidad disponible nunca sea mayor que la cantidad total
        if nueva_cantidad_disponible > nueva_cantidad_total:
            flash("La cantidad disponible no puede ser mayor que la cantidad total.", "danger")
            return redirect(url_for('main.editar_libro', libro_id=libro_id))

        # Actualizar campos del libro
        libro.titulo = form.titulo.data
        libro.autor = form.autor.data
        libro.categoria = form.categoria.data
        libro.descripcion = form.descripcion.data
        libro.editorial = form.editorial.data
        libro.fecha_publicacion = form.fecha_publicacion.data
        libro.cantidad_total = nueva_cantidad_total
        libro.cantidad_disponible = nueva_cantidad_disponible
        libro.disponible = nueva_cantidad_total > 0  # Disponible solo si hay al menos un ejemplar

        # Guardar cambios
        db.session.commit()
        flash('Libro editado exitosamente.', 'success')
        return redirect(url_for('main.mostrar_libros'))

    return render_template('editar_libro.html', form=form, libro=libro)

@main.route('/admin/libros/scan', methods=['GET'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def escanear_libro():
    return render_template('escanear_libro.html')

@main.route('/admin/reservas/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def reservas_agregar():
    form = NuevaReservaForm()

    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.all()]

    if request.method == 'GET':
       form.fecha_expiracion.data = date.today() + timedelta(days=7)

    if form.validate_on_submit():
        usuario_id = request.form.get('usuario_id')
        usuario = Usuario.query.get(usuario_id)

        usuario = Usuario.query.filter_by(llave_prestamo=form.llave_prestamo.data).first()
        if not usuario:
            flash('Llave incorrecta.', 'danger')
            return redirect(url_for('main.reservas_tabla'))

        libro = Libro.query.get(form.libro_id.data)
        if libro.cantidad_disponible <= 0:
            flash('No hay ejemplares disponibles para reservar.', 'warning')
            return redirect(url_for('main.reservas_tabla'))

        nueva_reserva = Reserva(
            usuario_id=usuario.id,
            libro_id=libro.id,
            fecha_expiracion=date.today() + timedelta(days=7),
            estado='activa'
        )

        libro.cantidad_disponible -= 1
        libro.actualizar_estado()

        db.session.add(nueva_reserva)
        db.session.commit()

        flash('✅ Reserva registrada correctamente y ejemplar bloqueado.', 'success')
        return redirect(url_for('main.reservas_tabla'))

    return render_template('reservas_agregar.html', form=form)


@main.route('/reservar/<int:libro_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('lector')
def reservar_libro_lector(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    form = ReservaLectorForm()

    if form.validate_on_submit():
        if current_user.llave_prestamo != form.llave_prestamo.data:
            flash('Llave incorrecta.', 'danger')
            return redirect(url_for('main.reservar_libro_lector', libro_id=libro.id))

        if libro.cantidad_disponible <= 0:
            flash('No hay ejemplares disponibles.', 'warning')
            return redirect(url_for('main.catalogo'))

        nueva_reserva = Reserva(
            usuario_id=current_user.id,
            libro_id=libro.id,
            fecha_expiracion=date.today() + timedelta(days=7),
            estado='activa'
        )
        libro.cantidad_disponible -= 1
        libro.actualizar_estado()

        db.session.add(nueva_reserva)
        db.session.commit()

        # ✅ Envía correo al usuario
        msg = Message(
            'Reserva confirmada - Biblioteca',
            sender='noreply@biblioteca.com',
            recipients=[current_user.correo]
        )
        msg.body = f"""
Hola {current_user.nombre},

Tu reserva para el libro "{libro.titulo}" se ha registrado correctamente.

Fecha de expiración: {nueva_reserva.fecha_expiracion}

Gracias por usar Biblioteca Avocado 📚

"""
        mail.send(msg)

        flash(f'Reserva para "{libro.titulo}" registrada correctamente.', 'success')
        return redirect(url_for('main.catalogo'))

    return render_template('reservar_libro.html', form=form, libro=libro)

@main.route('/reservas/<int:reserva_id>/cancelar', methods=['POST'])
@login_required
@roles_requeridos('lector')
def cancelar_reserva_lector(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    # Verifica que la reserva sea del usuario autenticado
    if reserva.usuario_id != current_user.id:
        flash('No tienes permiso para cancelar esta reserva.', 'danger')
        return redirect(url_for('main.mis_libros'))
    
    if reserva.estado == 'activa':
        reserva.libro.cantidad_disponible += 1
        reserva.libro.actualizar_estado()

    # Cambiar estado
    reserva.estado = 'cancelada'
    db.session.commit()

    # Envía correo de confirmación
    msg = Message(
        'Reserva Cancelada',
        sender='noreply@biblioteca.com',  # Usa tu remitente fijo
        recipients=[current_user.correo]
    )
    msg.body = f"""
Hola {current_user.nombre},

Tu reserva para el libro "{reserva.libro.titulo}" ha sido cancelada correctamente.

Si no realizaste esta acción, por favor contáctanos de inmediato.

Saludos,
El equipo de Biblioteca Avocado
"""

    mail.send(msg)

    flash(f'Reserva del libro "{reserva.libro.titulo}" cancelada y correo enviado.', 'success')
    return redirect(url_for('main.mis_libros'))

#rutas de admin/prestamos
@main.route('/admin/prestamos/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario','lector')
def nuevo_prestamo():
    form = PrestamoForm()

    # ⚡ Llena opciones de libros disponibles
    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.filter(Libro.cantidad_disponible > 0).all()]

    # ⚡ Si viene libro_id por GET, lo pone como seleccionado
    libro_id = request.args.get('libro_id', type=int)
    if libro_id and not form.libro_id.data:
        form.libro_id.data = libro_id

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(llave_prestamo=form.llave_prestamo.data).first()
        if not usuario:
            flash('Llave incorrecta.', 'danger')
            return redirect(url_for('main.nuevo_prestamo'))

        libro = Libro.query.get(form.libro_id.data)
        if libro and libro.cantidad_disponible > 0:
            nuevo_prestamo = Prestamo(
                usuario_id=usuario.id,
                libro_id=libro.id,
                fecha_prestamo=datetime.now().date(),
                fecha_devolucion_esperada=(datetime.now() + timedelta(days=7)).date(),
                estado='activo'
            )
            libro.cantidad_disponible -= 1
            db.session.add(nuevo_prestamo)
            db.session.commit()

            # ✅ Enviar correo de confirmación
            msg = Message(
                'Préstamo Registrado',
                sender='noreply@biblioteca.com',
                recipients=[usuario.correo]
            )
            msg.body = f"""
            Hola {usuario.nombre},

            Se ha registrado un préstamo para el libro "{libro.titulo}".

            📅 Fecha de préstamo: {nuevo_prestamo.fecha_prestamo}
            ⏰ Fecha de devolución esperada: {nuevo_prestamo.fecha_devolucion_esperada}

            Por favor, devuelve el libro a tiempo para evitar recargos.

            Saludos,
            El equipo de Biblioteca sbs
            """
            mail.send(msg)

            flash('Préstamo registrado correctamente.', 'success')
            return redirect(url_for('main.mostrar_prestamos'))
        else:
            flash('El libro no está disponible.', 'danger')

    return render_template('prestamos_agregar.html', form=form)

@main.route('/admin/prestamos/devolver/<int:prestamo_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def devolver_prestamo(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)

    if prestamo.fecha_devolucion:
        flash('Este préstamo ya fue devuelto.', 'warning')
    else:
        prestamo.fecha_devolucion = datetime.now().date()
        prestamo.estado = 'devuelto'
        libro = Libro.query.get(prestamo.libro_id)
        if libro:
            libro.cantidad_disponible += 1
        db.session.commit()
        flash('Préstamo marcado como devuelto.', 'success')

    return redirect(url_for('main.mostrar_prestamos'))  

@main.route('/admin/prestamos/mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_prestamos():
    prestamos = Prestamo.query.all()
    return render_template('prestamos_tabla.html', prestamos=prestamos)

#rutas admin/reservas
@main.route('/admin/reservas/editar/<int:reserva_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def editar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    form = EditarReservaForm(obj=reserva)

    # ⚠️ Solo permitir cambiar LIBRO y FECHA
    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.order_by(Libro.titulo).all()]

    if request.method == 'GET':
        form.libro_id.data = reserva.libro_id
        form.fecha_expiracion.data = reserva.fecha_expiracion

    if form.validate_on_submit():
        # Si se cambia el libro, ajustar disponibilidad
        if reserva.libro_id != form.libro_id.data:
            libro_anterior = Libro.query.get(reserva.libro_id)
            libro_nuevo = Libro.query.get(form.libro_id.data)

            if reserva.estado == 'activa':
                libro_anterior.cantidad_disponible += 1
                libro_nuevo.cantidad_disponible -= 1
                libro_anterior.actualizar_estado()
                libro_nuevo.actualizar_estado()

            reserva.libro_id = form.libro_id.data

        reserva.fecha_expiracion = form.fecha_expiracion.data

        db.session.commit()
        flash('✅ Reserva actualizada correctamente.', 'success')
        return redirect(url_for('main.reservas_tabla'))

    return render_template('editar_reserva.html', form=form, reserva=reserva)


@main.route('/admin/reservas/eliminar/<int:reserva_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def eliminar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    # Devolver disponibilidad solo si la reserva estaba activa
    libro = Libro.query.get(reserva.libro_id)
    if libro and reserva.estado == 'activa':
        libro.cantidad_disponible += 1

    reserva.estado = 'eliminada'
    db.session.commit()
    flash(f'🗑️ Reserva #{reserva.id} eliminada correctamente.', 'success')
    return redirect(url_for('main.reservas_tabla'))

@main.route('/admin/reservas/prestar/<int:reserva_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def prestar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    if reserva.estado != 'activa':
        flash('⚠️ Solo se pueden prestar reservas activas.', 'warning')
        return redirect(url_for('main.reservas_tabla'))

    libro = Libro.query.get(reserva.libro_id)
    if not libro or libro.cantidad_disponible <= 0:
        flash('❌ El libro no está disponible para préstamo.', 'danger')
        return redirect(url_for('main.reservas_tabla'))

    # Validar si ya tiene un préstamo activo del mismo libro
    prestamo_existente = Prestamo.query.filter_by(
        usuario_id=reserva.usuario_id,
        libro_id=reserva.libro_id,
        estado='activo'
    ).first()
    if prestamo_existente:
        flash('⚠️ Este usuario ya tiene un préstamo activo de este libro.', 'warning')
        return redirect(url_for('main.reservas_tabla'))

    nuevo_prestamo = Prestamo(
        usuario_id=reserva.usuario_id,
        libro_id=reserva.libro_id,
        fecha_prestamo=datetime.now().date(),
        fecha_devolucion_esperada=(datetime.now() + timedelta(days=7)).date(),
        estado='activo'
    )
    db.session.add(nuevo_prestamo)

    reserva.estado = 'confirmada'
    db.session.commit()

    flash(f'📚 Préstamo creado desde reserva #{reserva.id}.', 'success')
    return redirect(url_for('main.reservas_tabla'))

@main.route('/admin/reservas/mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def reservas_tabla():
    reservas = Reserva.query.filter(Reserva.estado != 'eliminada').all()
    return render_template('reservas_tabla.html', reservas=reservas)

#rutas admin/reportes

@main.route('/admin/reportes/historial')
@login_required
@roles_requeridos('administrador')
def historial_reportes():
    historial = HistorialReporte.query.order_by(
        HistorialReporte.fecha_generacion.desc()
    ).all()
    return render_template('reportes/historial_reportes.html', historial=historial)



@main.route('/admin/reportes/atrasados')
@login_required
@roles_requeridos('administrador')
def reporte_libros_atrasados():
    atrasados = Prestamo.query.filter(
        Prestamo.fecha_devolucion_esperada < date.today(),
        Prestamo.fecha_devolucion.is_(None)
    ).all()
    return render_template('reportes/fragmento_atrasados.html', atrasados=atrasados)


@main.route('/admin/reportes/descargar_reporte_atrasados')
@login_required
@roles_requeridos('administrador')
def descargar_reporte_atrasados():
    atrasados = Prestamo.query.filter(
        Prestamo.fecha_devolucion_esperada < date.today(),
        Prestamo.fecha_devolucion.is_(None)
    ).all()
    pdf = generar_reporte_con_plantilla(atrasados)

    nombre_archivo = f"reporte_atrasados_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    ruta_carpeta = os.path.join(current_app.root_path, 'static', 'archivos')
    os.makedirs(ruta_carpeta, exist_ok=True)

    ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)
    with open(ruta_archivo, 'wb') as f:
        f.write(pdf)

    historial = HistorialReporte(
        nombre_reporte="Libros Atrasados",
        ruta_archivo=f'archivos/{nombre_archivo}',
        admin_id=current_user.id
    )
    db.session.add(historial)
    db.session.commit()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={nombre_archivo}'
    return response

@main.route('/admin/reportes/prestados')
@login_required
@roles_requeridos('administrador')
def reporte_libros_prestados():
    prestamos = Prestamo.query.filter(Prestamo.estado == 'activo').all()
    return render_template('reportes/fragmento_prestados.html', prestamos=prestamos)


@main.route('/admin/reportes/descargar_reporte_prestados')
@login_required
@roles_requeridos('administrador')
def descargar_reporte_prestados():
    prestamos = Prestamo.query.filter(Prestamo.estado == 'activo').all()
    pdf = generar_reporte_prestados(prestamos)

    nombre_archivo = f"reporte_prestados_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    ruta_carpeta = os.path.join(current_app.root_path, 'static', 'archivos')
    os.makedirs(ruta_carpeta, exist_ok=True)

    ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)
    with open(ruta_archivo, 'wb') as f:
        f.write(pdf)

    historial = HistorialReporte(
        nombre_reporte="Libros Prestados",
        ruta_archivo=f'archivos/{nombre_archivo}',
        admin_id=current_user.id
    )
    db.session.add(historial)
    db.session.commit()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={nombre_archivo}'
    return response


@main.route('/admin/reportes/populares')
@login_required
@roles_requeridos('administrador')
def reporte_libros_populares():
    populares = db.session.query(
        Libro.id,
        Libro.titulo,
        Libro.autor,
        func.count(Prestamo.id).label('prestamos'),
        func.count(Reserva.id).label('reservas'),
        (func.count(Prestamo.id) + func.count(Reserva.id)).label('total')
    ).outerjoin(Prestamo).outerjoin(Reserva).group_by(Libro.id).order_by(
        db.desc('total')
    ).limit(5).all()

    return render_template('reportes/fragmento_populares.html', populares=populares)


@main.route('/admin/reportes/descargar_reporte_populares')
@login_required
@roles_requeridos('administrador')
def descargar_reporte_populares():
    populares = db.session.query(
        Libro.id,
        Libro.titulo,
        Libro.autor,
        func.count(Prestamo.id).label('prestamos'),
        func.count(Reserva.id).label('reservas'),
        (func.count(Prestamo.id) + func.count(Reserva.id)).label('total')
    ).outerjoin(Prestamo).outerjoin(Reserva).group_by(Libro.id).order_by(
        db.desc('total')
    ).limit(5).all()

    pdf = generar_reporte_populares(populares)

    nombre_archivo = f"reporte_populares_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    ruta_carpeta = os.path.join(current_app.root_path, 'static', 'archivos')
    os.makedirs(ruta_carpeta, exist_ok=True)

    ruta_archivo = os.path.join(ruta_carpeta, nombre_archivo)
    with open(ruta_archivo, 'wb') as f:
        f.write(pdf)

    historial = HistorialReporte(
        nombre_reporte="Libros Populares",
        ruta_archivo=f'archivos/{nombre_archivo}',
        admin_id=current_user.id
    )
    db.session.add(historial)
    db.session.commit()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={nombre_archivo}'
    return response

#formatos de imagenes y fotos de perfil
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def extension_permitida(nombre_archivo):
    return '.' in nombre_archivo and \
           nombre_archivo.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    usuario = Usuario.query.get(current_user.id)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        correo = request.form.get('correo')
        archivo = request.files.get('foto_perfil')

        if nombre:
            usuario.nombre = nombre
        if apellido:
            usuario.apellido = apellido
        if correo:
            usuario.correo = correo

        if archivo and archivo.filename != '':
            filename = secure_filename(archivo.filename)
            extension = os.path.splitext(filename)[1]
            nuevo_nombre = f"user_{usuario.id}{extension}"
            ruta_guardado = os.path.join(current_app.root_path, 'static', 'fotos_perfil', nuevo_nombre)
            archivo.save(ruta_guardado)
            usuario.foto = f"fotos_perfil/{nuevo_nombre}"

            flash("Foto de perfil actualizada con éxito", "success")
        else:
            flash("Perfil actualizado con éxito", "success")

        db.session.commit()
        return redirect(url_for('main.configuracion'))

    return render_template('configuracion.html', usuario=usuario)

#ruta de catalogo
@main.route('/catalogo')
@login_required
@roles_requeridos('lector')
def catalogo():
    page = request.args.get('page', 1, type=int)  # Página actual desde ?page=
    per_page = 12  # Ahora muestra 12 libros por página

    # Aplica el filtro y paginación
    libros = Libro.query.filter(Libro.estado != 'eliminado').paginate(page=page, per_page=per_page)

    # Favoritos del usuario lector
    favoritos_ids = []
    if current_user.is_authenticated and current_user.rol == 'lector':
        favoritos_ids = [f.libro_id for f in current_user.favoritos]

    return render_template('catalogo.html', libros=libros, favoritos_ids=favoritos_ids)

#ruta de perfil
@main.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        usuario = Usuario.query.get(current_user.id)
        usuario.nombre = request.form['nombre']
        usuario.correo = request.form['correo']

        # Si hay una nueva foto de perfil
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file.filename != '':
                filename = secure_filename(file.filename)
                ruta_carpeta = os.path.join('static', 'imagenes', 'perfil')
                os.makedirs(ruta_carpeta, exist_ok=True)  # Crea carpeta si no existe
                filepath = os.path.join(ruta_carpeta, filename)
                file.save(filepath)
                usuario.foto = f'imagenes/perfil/{filename}'

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('main.perfil'))

    return render_template('perfil.html', usuario=current_user)

@main.route('/foto_perfil')
@login_required
def foto_perfil():
    if current_user.foto:
        ruta = os.path.join('static', current_user.foto.replace('/', os.sep))
        if os.path.exists(ruta):
            return send_file(ruta, mimetype='image/jpeg')
    
    # Si no tiene foto, o no existe el archivo
    return redirect(url_for('static', filename='imagenes/perfil/default.png'))

@main.route('/libro/<int:libro_id>')
@login_required
def detalle_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    es_favorito = False
    if current_user.is_authenticated and current_user.rol == 'lector':
        es_favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first() is not None
    return render_template('detalle_libro.html', libro=libro, es_favorito=es_favorito)


@main.route('/favoritos/toggle/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('lector')
def toggle_favorito(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first()

    if favorito:
        db.session.delete(favorito)
        flash('Libro eliminado de tus favoritos.', 'info')
    else:
        nuevo_favorito = Favorito(usuario_id=current_user.id, libro_id=libro.id)
        db.session.add(nuevo_favorito)
        flash('Libro añadido a tus favoritos.', 'success')

    db.session.commit()
    return redirect(url_for('main.detalle_libro', libro_id=libro.id))

@main.route('/mis_libros')
@login_required
@roles_requeridos('lector')
def mis_libros():
    # Obtener préstamos activos del usuario
    mis_prestamos = Prestamo.query.filter_by(usuario_id=current_user.id).all()
    # Obtener reservas activas del usuario
    mis_reservas = Reserva.query.filter_by(usuario_id=current_user.id, estado='activa').all()
    # Obtener favoritos del usuario
    mis_favoritos = Favorito.query.filter_by(usuario_id=current_user.id).all()

    return render_template('mis_libros.html',
                           prestamos=mis_prestamos,
                           reservas=mis_reservas,
                           favoritos=mis_favoritos)

@main.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            token = generar_token(usuario.correo)
            link = url_for('main.restablecer', token=token, _external=True)

            msg = Message('Recuperar contraseña', sender='noreply@biblioteca.com', recipients=[usuario.correo])
            msg.body = (
                        f'Estimado usuario,\n\n'
                        f'Hemos recibido una solicitud para restablecer la contraseña de su cuenta de biblioteca avocado.\n'
                        f'Para continuar con el proceso, por favor haga clic en el siguiente enlace:\n\n'
                        f'{link}\n\n'
                        f'Si usted no solicitó este cambio, puede ignorar este mensaje.\n\n'
                        f'Atentamente,\n'
                        f'El equipo de la Biblioteca'
                    )

            mail.send(msg)

            flash('Te enviamos un correo para recuperar tu contraseña.', 'info')
        else:
            flash('Correo no encontrado.', 'danger')
    return render_template('recuperar.html')

@main.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    email = verificar_token(token)
    if not email:
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        nueva_pass = request.form['password']
        usuario = Usuario.query.filter_by(correo=email).first()
        if usuario:
            usuario.set_password(nueva_pass)
            db.session.commit()
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('main.login'))
    return render_template('restablecer.html')

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')
def usuarios_modal():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)

@main.route('/api/prestamos_mes')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def prestamos_por_mes():
    resultados = db.session.query(
        extract('month', Prestamo.fecha_prestamo).label('mes'),
        func.count().label('total')
    ).group_by('mes').order_by('mes').all()

    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return jsonify([
        {'mes': meses[int(r.mes) - 1], 'total': r.total}
        for r in resultados
    ])

@main.route('/api/libros_populares')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def libros_populares():
    resultados = db.session.query(
        Libro.titulo,
        func.count(Prestamo.id).label('total')
    ).join(Prestamo).group_by(Libro.id).order_by(func.count(Prestamo.id).desc()).limit(5).all()

    return jsonify([{'titulo': r.titulo, 'total': r.total} for r in resultados])

@main.route('/api/libros_atrasados')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def libros_atrasados():
    resultados = db.session.query(
        Libro.titulo,
        func.count(Prestamo.id).label('total')
    ).join(Prestamo).filter(Prestamo.estado == 'atrasado') \
     .group_by(Libro.id).order_by(func.count(Prestamo.id).desc()).limit(5).all()

    return jsonify([{'titulo': r.titulo, 'total': r.total} for r in resultados])

@main.route('/ajax/buscar_usuario_por_llave')
@login_required
def ajax_buscar_usuario_por_llave():
    llave = request.args.get('llave_prestamo')
    usuario = Usuario.query.filter_by(llave_prestamo=llave).first()
    if usuario:
        return jsonify({
            'success': True,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'usuario_id': usuario.id
        })
    else:
        return jsonify({'success': False})



#rutas para el contenido de los contadores
@main.route('/admin/usuarios/solo_mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_usuarios_sencillo():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar_sencillo.html', usuarios=usuarios)

@main.route('/admin/libros/solo_mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_libros_sencillo():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    return render_template('libros_tabla_sencillo.html', libros=libros)

@main.route('/admin/prestamos/solo_mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_prestamos_sencillo():
    prestamos = Prestamo.query.all()
    return render_template('prestamos_tabla_sencillo.html', prestamos=prestamos)

@main.route('/admin/reservas/solo_mostrar')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def mostrar_reservas_sencillo():
    reservas = Reserva.query.all()
    return render_template('reservas_tabla_sencillo.html', reservas=reservas)

@main.route('/buscar', methods=['GET'])
def buscar():
    consulta = request.args.get('q', '').strip()  # obtén ?q=...
    resultados = []

    if consulta:
        # Puedes ajustar a tu modelo real:
        resultados = Libro.query.filter(
            Libro.titulo.ilike(f'%{consulta}%')
        ).all()

    return render_template('resultados_busqueda.html', resultados=resultados, consulta=consulta)

@main.route('/categoria/<categoria>')
def categoria(categoria):
    libros = Libro.query.filter_by(categoria=categoria).all()
    return render_template('categoria.html', libros=libros, categoria=categoria)
