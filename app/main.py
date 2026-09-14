"""FastAPI entry point for the OISO recommendation service."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.schemas import (
    ApiResponse,
    CourseRecommendationData,
    CourseRecommendationRequest,
    HealthData,
)
from app.service import RecommendationService


logger = logging.getLogger(__name__)


def create_app(
    recommendation_service: RecommendationService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.recommendation_service = recommendation_service
        app.state.startup_error = None

        if app.state.recommendation_service is None:
            try:
                app.state.recommendation_service = (
                    RecommendationService.from_settings(runtime_settings)
                )
            except Exception as exc:  # Keep liveness available for diagnostics.
                logger.exception("Recommendation engine initialization failed")
                app.state.startup_error = str(exc)

        yield

    application = FastAPI(
        title="OISO Course Recommendation API",
        version="0.1.0",
        description="Spring 백엔드가 호출하는 임베딩 기반 관광 코스 추천 서비스",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_settings.cors_allowed_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {
                    "code": 4000,
                    "message": "요청 값이 올바르지 않습니다.",
                    "data": {"errors": exc.errors()},
                },
            ),
        )

    def get_recommendation_service(request: Request) -> RecommendationService:
        service = getattr(request.app.state, "recommendation_service", None)
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Recommendation model is not ready.",
            )
        return service

    @application.get(
        "/health",
        response_model=ApiResponse[HealthData],
        tags=["system"],
    )
    def health(request: Request) -> ApiResponse[HealthData]:
        loaded = getattr(request.app.state, "recommendation_service", None) is not None
        return ApiResponse(
            code=2000,
            message="서비스가 실행 중입니다.",
            data=HealthData(status="UP", model_loaded=loaded),
        )

    @application.get(
        "/ready",
        response_model=ApiResponse[HealthData],
        tags=["system"],
    )
    def ready(request: Request) -> ApiResponse[HealthData]:
        loaded = getattr(request.app.state, "recommendation_service", None) is not None
        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Recommendation model is not ready.",
            )
        return ApiResponse(
            code=2000,
            message="추천 요청을 처리할 수 있습니다.",
            data=HealthData(status="READY", model_loaded=True),
        )

    @application.post(
        "/api/v1/recommendations/courses",
        response_model=ApiResponse[CourseRecommendationData],
        response_model_by_alias=True,
        tags=["recommendations"],
    )
    def recommend_course(
        body: CourseRecommendationRequest,
        service: RecommendationService = Depends(get_recommendation_service),
    ) -> ApiResponse[CourseRecommendationData]:
        result = service.recommend(body)
        return ApiResponse(
            code=2000,
            message="관광 코스 추천에 성공했습니다.",
            data=result,
        )

    return application


app = create_app()

