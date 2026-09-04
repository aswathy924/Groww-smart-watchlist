
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.schemas import AnomalyInjectionRequest, AnomalyInjectionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["Test / Demo"])


@router.post(
    "/inject-anomaly",
    response_model=AnomalyInjectionResponse,
    summary="Inject a market anomaly for testing",
    description=(
        "Manually trigger one of four anomaly types on a specific symbol "
        "to test the delta engine's detection and alerting behaviour:\n\n"
        "- **price_surge** — +6% immediate price move\n"
        "- **volume_explosion** — 4× volume multiplier on next tick\n"
        "- **bad_tick** — +20% spike tagged SUSPECT_TICK (suppressed from alerts)\n"
        "- **feed_delay** — Pause tick emission for `duration_seconds` (default: 10s)\n"
    ),
)
async def inject_anomaly(
    request: Request,
    body: AnomalyInjectionRequest,
) -> AnomalyInjectionResponse:
    """
    Route the injection request through the FeedInjector.

    The injector is stored on `app.state.injector` by the lifespan
    context in main.py.
    """
    injector = getattr(request.app.state, "injector", None)
    if injector is None:
        raise HTTPException(
            status_code=503,
            detail="Feed injector is not initialised. Is the market feed running?",
        )

    # Validate that the symbol is tracked
    feed = getattr(request.app.state, "feed", None)
    if feed is None:
        raise HTTPException(status_code=503, detail="Market feed is not running.")

    tracked_symbols = feed.list_symbols()
    if body.symbol.upper() not in tracked_symbols:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Symbol {body.symbol!r} is not tracked by the active feed. "
                f"Available: {sorted(tracked_symbols)}"
            ),
        )

    try:
        message = await injector.inject(
            symbol=body.symbol,
            anomaly_type=body.anomaly_type,
            duration_seconds=body.duration_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Injection failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Injection error: {exc}")

    return AnomalyInjectionResponse(
        status="injected",
        symbol=body.symbol.upper(),
        anomaly_type=body.anomaly_type.value,
        message=message,
    )
