import os

EMAILS_DIR = os.path.dirname(__file__)

def render_template(name: str, subject: str = "", **kwargs) -> str:
    # Загружаем body шаблон
    body_path = os.path.join(EMAILS_DIR, f"{name}.html")
    with open(body_path) as f:
        body = f.read()
    # Подставляем переменные в body
    for key, value in kwargs.items():
        body = body.replace(f"{{{{{key}}}}}", str(value))
    # Загружаем base
    base_path = os.path.join(EMAILS_DIR, "base.html")
    with open(base_path) as f:
        html = f.read()
    # Вставляем body в base
    html = html.replace("{{body}}", body)
    html = html.replace("{{subject}}", subject)
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html
