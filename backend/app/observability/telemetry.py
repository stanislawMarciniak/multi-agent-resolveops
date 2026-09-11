from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,
)
from opentelemetry.instrumentation.httpx import (
    HTTPXClientInstrumentor,
)
from opentelemetry.sdk.metrics import (
    MeterProvider,
)
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    Resource,
)
from opentelemetry.sdk.trace import (
    TracerProvider,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from app.config import Settings

_configured = False


def configure_telemetry(
    settings: Settings,
) -> None:
    global _configured

    if (
        _configured
        or not settings.otel_enabled
    ):
        return

    resource = Resource.create(
        {
            SERVICE_NAME: (
                settings.otel_service_name
            ),
        }
    )

    tracer_provider = TracerProvider(
        resource=resource
    )

    metric_readers = []

    endpoint = (
        settings
        .otel_exporter_otlp_endpoint
        .rstrip("/")
    )

    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=(
                        f"{endpoint}/v1/traces"
                    )
                )
            )
        )

        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=(
                        f"{endpoint}/v1/metrics"
                    )
                )
            )
        )

    if settings.otel_console_exporter:
        tracer_provider.add_span_processor(
            SimpleSpanProcessor(
                ConsoleSpanExporter()
            )
        )

    trace.set_tracer_provider(
        tracer_provider
    )

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers,
    )

    metrics.set_meter_provider(
        meter_provider
    )

    HTTPXClientInstrumentor().instrument(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )

    _configured = True


def instrument_fastapi(
    app: FastAPI,
) -> None:
    # opentelemetry-instrumentation-fastapi 0.63b1 crashes while naming
    # spans for APIRouter-mounted routes (`_IncludedRouter` has no `.path`).
    # That aborts the request before CORSMiddleware can attach headers, which
    # browsers report as a CORS failure. Disable FastAPI server spans until
    # the instrumentation package is upgraded; HTTPX client spans remain.
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=".*",
    )