from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, DateField, SubmitField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError, Optional, NumberRange, Email
from app.models import Usuario
from datetime import date

class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    apellido = StringField('Apellido', validators=[Optional(), Length(min=2, max=50)])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    documento = StringField('Número de Documento', validators=[DataRequired(), Length(min=5, max=20)])
    direccion = StringField('Dirección', validators=[DataRequired(), Length(min=5, max=100)])
    telefono = StringField('Teléfono', validators=[Optional(), Length(min=7, max=20)])
    fecha_nacimiento = DateField('Fecha de Nacimiento', format='%Y-%m-%d', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$', message='Debe contener letras y números.')
    ])

    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])

    submit = SubmitField('Registrarse')

    def validate_correo(self, correo):
        if Usuario.query.filter_by(correo=correo.data).first():
            raise ValidationError('Ya existe una cuenta con este correo.')

    def validate_documento(self, documento):
        if Usuario.query.filter_by(documento=documento.data).first():
            raise ValidationError('Ya existe una cuenta con este número de documento.')

class LibroForm(FlaskForm):
    isbn = StringField(
        'ISBN',
        validators=[
            DataRequired(message="El ISBN es obligatorio."),
            Length(min=10, max=17, message="El ISBN debe tener entre 10 y 17 caracteres."),
            Regexp(r'^[0-9X-]+$', message='El ISBN solo puede contener números, guiones y "X".')
        ]
    )
    titulo = StringField(
        'Título',
        validators=[
            DataRequired(message="El título es obligatorio."),
            Length(max=255, message="El título no puede exceder los 255 caracteres.")
        ]
    )
    autor = StringField(
        'Autor',
        validators=[
            DataRequired(message="El autor es obligatorio."),
            Length(max=255, message="El nombre del autor no puede exceder los 255 caracteres.")
        ]
    )
    descripcion = TextAreaField(
        'Descripción',
        validators=[
            Optional() # Permite que sea opcional
            # No se necesita Length si tu columna de DB es TEXT/LONGTEXT
        ]
    )
    categoria = SelectField(
        'Categoría',
        choices=[
            ('novela', 'Novela'),
            ('filosofia', 'Filosofía'),
            ('poesia', 'Poesía'),
            ('teatro', 'Teatro'),
            ('ensayo', 'Ensayo'),
            ('cronica', 'Crónica'),
            ('historieta', 'Historieta'),
            ('biografia', 'Biografía'),
            ('cuento', 'Cuento'),
            ('ciencia_ficcion', 'Ciencia Ficción'), # Agrego esta por los ejemplos de OpenLibrary
            ('thriller', 'Thriller'), # Agrego esta por los ejemplos de OpenLibrary
            ('fantasía', 'Fantasía'), # Agrego esta por los ejemplos de OpenLibrary
            ('clasico', 'Clásico'), # Agrego esta por los ejemplos de OpenLibrary
            ('terror', 'Terror'), # Agrego esta por los ejemplos de OpenLibrary
            ('romance', 'Romance'), # Agrego esta por los ejemplos de OpenLibrary
            ('historia', 'Historia'), # Agrego esta por los ejemplos de OpenLibrary
            ('ficcion_criminal', 'Ficción Criminal'), # Agrego esta por los ejemplos de OpenLibrary
            ('drama', 'Drama'), # Agrego esta por los ejemplos de OpenLibrary
            ('comedia', 'Comedia'), # Agrego esta por los ejemplos de OpenLibrary
            ('juvenil', 'Juvenil'), # Agrego esta por los ejemplos de OpenLibrary
            ('sátira', 'Sátira'), # Agrego esta por los ejemplos de OpenLibrary
            ('gonzo', 'Gonzo'), # Agrego esta por los ejemplos de OpenLibrary
            ('realismo_magico', 'Realismo Mágico'), # Agrego esta por los ejemplos de OpenLibrary
            ('novela_historica', 'Novela Histórica'), # Agrego esta por los ejemplos de OpenLibrary
            ('otros', 'Otros'),
            ('', 'Seleccione una categoría') # Opción por defecto para forzar la selección
        ],
        validators=[
            DataRequired(message="Debe seleccionar una categoría.") # Asegura que se seleccione una opción
        ],
        render_kw={"placeholder": "Seleccione una categoría"} # Placeholder para el campo
    )
    editorial = StringField(
        'Editorial',
        validators=[
            Optional(),
            Length(max=255, message="La editorial no puede exceder los 255 caracteres.")
        ]
    )
    fecha_publicacion = DateField(
        'Fecha de Publicación',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    cantidad_total = IntegerField(
        'Cantidad Total',
        validators=[
            DataRequired(message="La cantidad total es obligatoria."),
            NumberRange(min=0, message="La cantidad total no puede ser negativa.")
        ]
    )

    portada = FileField(
        'Portada',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png'], 'Solo se permiten imágenes JPG y PNG.')
        ]
    )

    portada_url = HiddenField(
        'URL de Portada',
        validators=[
            Optional(),
            Length(max=500, message="La URL de la portada no puede exceder los 500 caracteres.") # Limita la longitud de la URL
        ]
    )
    submit = SubmitField('Guardar')

class EditarLibroForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired()])
    autor = StringField("Autor", validators=[DataRequired()])
    descripcion = TextAreaField("Descripción", validators=[Optional()])
    categoria = SelectField(
        "Categoría",
        choices=[
            ('novela', 'Novela'),
            ('filosofia', 'Filosofía'),
            ('poesia', 'Poesía'),
            ('teatro', 'Teatro'),
            ('ensayo', 'Ensayo'),
            ('cronica', 'Crónica'),
            ('historieta', 'Historieta'),
            ('biografia', 'Biografía'),
            ('cuento', 'Cuento'),
            ('audiolibro', 'Audiolibro')
        ],
        validators=[DataRequired()]
    )
    cantidad_total = IntegerField("Cantidad Total", validators=[Optional(), NumberRange(min=0)])
    cantidad_disponible = IntegerField("Cantidad Disponible", validators=[Optional(), NumberRange(min=0)])
    fecha_publicacion = DateField("Fecha de Publicación", format='%Y-%m-%d', validators=[Optional()])
    editorial = StringField("Editorial", validators=[Optional()])
    portada_url = HiddenField('URL de Portada', validators=[Optional()])
    submit = SubmitField("Guardar cambios")

class PrestamoForm(FlaskForm):
    llave_prestamo = StringField("Llave de préstamo", validators=[
        DataRequired(),
        Length(min=7, max=7, message="La llave debe tener el formato XXX-XXX (7 caracteres)")
    ])
    libro_id = SelectField("Libro", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Guardar")

class NuevaReservaForm(FlaskForm):
    llave_prestamo = StringField("Llave de préstamo", validators=[
        DataRequired(),
        Length(min=7, max=7, message="La llave debe tener el formato XXX-XXX")
    ])
    libro_id = SelectField("Libro", coerce=int, validators=[DataRequired()])
    fecha_expiracion = DateField("Fecha Expiración", format='%Y-%m-%d')
    submit = SubmitField("Guardar")

class ReservaLectorForm(FlaskForm):
    llave_prestamo = StringField(
        'Llave de Préstamo',
        validators=[DataRequired(message='Ingresa tu llave de préstamo.')]
    )
    submit = SubmitField('Reservar')

class EditarReservaForm(FlaskForm):
    libro_id = SelectField('Libro', coerce=int, validators=[DataRequired()])
    fecha_expiracion = DateField('Fecha de Expiración', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Guardar cambios')

class AgregarLectorPresencialForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    documento = StringField('Número de Documento', validators=[DataRequired(), Length(min=5, max=20)])
    direccion = StringField('Dirección', validators=[DataRequired(), Length(min=5, max=100)])
    correo = StringField('Correo', validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField('Registrar')

    def validate_documento(self, documento):
        if Usuario.query.filter_by(documento=documento.data).first():
            raise ValidationError('Ya existe un usuario con este número de documento.')


class EditarUsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    direccion = StringField('Dirección', validators=[DataRequired()])
    rol = SelectField('Rol', choices=[('lector', 'Lector'), ('bibliotecario', 'Bibliotecario'), ('administrador', 'Administrador')], validators=[DataRequired()])
    submit = SubmitField('Guardar')


