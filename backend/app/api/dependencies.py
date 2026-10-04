from fastapi import Request


def get_db(request: Request):
    session = request.app.state.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_ampa_service(request: Request):
    service = request.app.state.ampa_service
    if service is None or not service.available:
        from app.services.errors import ModelUnavailable
        raise ModelUnavailable("Trained AMPA model unavailable; configure MISTIQ_AMPA_MODEL_PATH")
    return service
