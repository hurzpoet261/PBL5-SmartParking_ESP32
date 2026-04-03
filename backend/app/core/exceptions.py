from fastapi import HTTPException, status


class AppExceptionCase(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BadRequestException(AppExceptionCase):
    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class NotFoundException(AppExceptionCase):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppExceptionCase):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


def http_exception(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)
