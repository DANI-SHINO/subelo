from flask import Flask
from app.extensions import db, login_manager, mail
from app.models import Usuario
from app.routes import main
from app.config import Config
from app.utils import enviar_recordatorios
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    app.register_blueprint(main)

    with app.app_context():
        # ¡IMPORTANTE! Crea todas las tablas si no existen
        db.create_all()

        if not Usuario.query.filter_by(rol='administrador').first():
            admin = Usuario(
                nombre='admin',
                apellido='admin',
                correo='admin@biblioteca.com',
                documento='1000000000',
                direccion='Oficina principal',
                telefono='0000000000',
                fecha_nacimiento=datetime(1990, 1, 1),
                rol='administrador',
                activo=True
            )
            admin.set_password('admin123')
            admin.generar_llave_prestamo()
            db.session.add(admin)
            db.session.commit()

            print("Usuario administrador creado: usuario=admin, contraseña=admin123")

    return app


if __name__ == '__main__':
    app = create_app()
    enviar_recordatorios(app)
    app.run(debug=True)