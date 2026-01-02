"""
Custom exception handler for the API
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé pour standardiser les réponses d'erreur.
    
    Format de réponse standardisé :
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Description de l'erreur",
            "details": {} // Détails supplémentaires si disponibles
        }
    }
    """
    # Appeler le gestionnaire par défaut de DRF d'abord
    response = exception_handler(exc, context)

    if response is not None:
        # Reformater la réponse d'erreur
        error_data = {
            "success": False,
            "error": {
                "code": get_error_code(exc, response.status_code),
                "message": get_error_message(exc, response.data),
                "details": get_error_details(response.data)
            }
        }
        response.data = error_data
        return response

    # Gérer les exceptions Django non gérées par DRF
    if isinstance(exc, DjangoValidationError):
        error_data = {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Erreur de validation",
                "details": exc.message_dict if hasattr(exc, 'message_dict') else {"error": str(exc)}
            }
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        error_data = {
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Ressource non trouvée",
                "details": {}
            }
        }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)

    # Exception non gérée - retourner None pour utiliser le comportement par défaut
    return None


def get_error_code(exc, status_code):
    """Détermine le code d'erreur basé sur l'exception et le status code."""
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
    }
    
    # Codes personnalisés pour certaines exceptions
    exc_name = exc.__class__.__name__
    custom_codes = {
        "ValidationError": "VALIDATION_ERROR",
        "NotAuthenticated": "NOT_AUTHENTICATED",
        "AuthenticationFailed": "AUTHENTICATION_FAILED",
        "PermissionDenied": "PERMISSION_DENIED",
        "Throttled": "RATE_LIMIT_EXCEEDED",
    }
    
    return custom_codes.get(exc_name, error_codes.get(status_code, "UNKNOWN_ERROR"))


def get_error_message(exc, data):
    """Extrait un message d'erreur lisible."""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        if isinstance(exc.detail, list) and exc.detail:
            return str(exc.detail[0])
        if isinstance(exc.detail, dict):
            # Retourner le premier message trouvé
            for key, value in exc.detail.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                elif isinstance(value, str):
                    return f"{key}: {value}"
    
    return "Une erreur est survenue"


def get_error_details(data):
    """Extrait les détails de l'erreur pour une réponse structurée."""
    if isinstance(data, dict):
        details = {}
        for key, value in data.items():
            if key != 'detail':
                if isinstance(value, list):
                    details[key] = [str(v) for v in value]
                else:
                    details[key] = str(value)
        return details
    return {}


# Exceptions personnalisées pour l'application

class APIException(Exception):
    """Exception de base pour les erreurs API personnalisées."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "API_ERROR"
    default_message = "Une erreur est survenue"

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class InvalidTokenException(APIException):
    """Token invalide ou expiré."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "INVALID_TOKEN"
    default_message = "Token invalide ou expiré"


class ResourceNotFoundException(APIException):
    """Ressource non trouvée."""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "RESOURCE_NOT_FOUND"
    default_message = "Ressource non trouvée"


class PermissionDeniedException(APIException):
    """Permission refusée."""
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "PERMISSION_DENIED"
    default_message = "Vous n'avez pas la permission d'effectuer cette action"


class ConflictException(APIException):
    """Conflit avec l'état actuel de la ressource."""
    status_code = status.HTTP_409_CONFLICT
    default_code = "CONFLICT"
    default_message = "Conflit avec l'état actuel de la ressource"


class ValidationException(APIException):
    """Erreur de validation des données."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "VALIDATION_ERROR"
    default_message = "Erreur de validation des données"


class GroupLimitExceededException(APIException):
    """Limite de membres du groupe atteinte."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "GROUP_LIMIT_EXCEEDED"
    default_message = "Le nombre maximum de membres du groupe est atteint"


class InvitationExpiredException(APIException):
    """Invitation expirée."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "INVITATION_EXPIRED"
    default_message = "Cette invitation a expiré"