class IntegrationError(Exception):
    status_code = 400
    code = "integration_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class StudentNotFound(IntegrationError):
    status_code = 404
    code = "student_not_found"


class QuestionNotFound(IntegrationError):
    status_code = 404
    code = "question_not_found"


class RecommendationNotFound(IntegrationError):
    status_code = 404
    code = "recommendation_not_found"


class RecommendationUnavailable(IntegrationError):
    status_code = 404
    code = "recommendation_unavailable"


class InvalidAttempt(IntegrationError):
    status_code = 422
    code = "invalid_attempt"


class ModelUnavailable(IntegrationError):
    status_code = 503
    code = "model_unavailable"


class InsufficientData(IntegrationError):
    status_code = 409
    code = "insufficient_data"


class InvalidFeatureVector(IntegrationError):
    status_code = 422
    code = "invalid_feature_vector"
