from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request."):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
        )


class EmailAlreadyExistsException(AppException):
    def __init__(self, message: str = "Email is already registered."):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="EMAIL_ALREADY_EXISTS",
        )


class UsernameAlreadyExistsException(AppException):
    def __init__(self, message: str = "Username is already taken."):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="USERNAME_ALREADY_EXISTS",
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Could not validate credentials."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class TooManyRequestsException(AppException):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="TOO_MANY_REQUESTS",
        )


class ServiceUnavailableException(AppException):
    def __init__(self, message: str = "A required service is temporarily unavailable."):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
        )


class ConflictException(AppException):
    def __init__(self, message: str = "A conflict occurred."):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
        )


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed."):
        super().__init__(
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            error_code="VALIDATION_ERROR",
        )




def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        return JSONResponse(
            status_code=exc.status_code,
            headers={"WWW-Authenticate": "Bearer"},
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
            },
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
            },
        )
