from flask import Flask
from flask_assets import Environment
from flask_wtf.csrf import CSRFProtect
from os import path

import i18n


def create_app(config):
    app = Flask(__name__,
                template_folder=config.JOURNALIST_TEMPLATES_DIR,
                static_folder=path.join(config.SECUREDROP_ROOT, 'static'))

    app.config.from_object(config.JournalistInterfaceFlaskConfig)

    CSRFProtect(app)
    Environment(app)

    i18n.setup_app(app)

    return app