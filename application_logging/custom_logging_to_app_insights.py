import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics
from config import APPLICATION_INSIGHTS_CONNECTION_STRING

# from opentelemetry import trace

# # Create an OpenTelemetry tracer for distributed tracing (optional, for monitoring and diagnostics)
# tracer = trace.get_tracer(__name__)

# Reserved keys to avoid clashing with LogRecord attributes
RESERVED_LOG_KEYS = {
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "message"
}

# Flag to ensure logger is configured only once
_logger_configured = False

#@tracer.start_as_current_span("configure_logger_fn")
def configure_logger():
    """
    Configures the root logger to send logs to Azure Monitor using the provided connection string.
    Ensures configuration happens only once.
    Returns a logger instance for the current module.
    """
    global _logger_configured

    if not _logger_configured:
        configure_azure_monitor(
            connection_string=APPLICATION_INSIGHTS_CONNECTION_STRING,
        )
        # Set log levels for different loggers if needed
        # logging.getLogger("azure").setLevel(logging.INFO)
        # logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.INFO)
        # logging.getLogger("applicationinsights").setLevel(logging.WARNING)
        logging.getLogger().setLevel(logging.INFO)
        _logger_configured = True

    return logging.getLogger(__name__)

# --- Log trace ---
def log_step(logger, message: str, level: str = "info", **custom_dimensions):
    """
    Logs a message at the specified level with optional custom dimensions.
    Reserved keys are prefixed to avoid conflicts.
    """
    attributes = {
        (f"meta_{k}" if k in RESERVED_LOG_KEYS else k): v
        for k, v in custom_dimensions.items()
    }

    if level == "debug":
        logger.debug(message, extra=attributes)
    elif level == "warning":
        logger.warning(message, extra=attributes)
    elif level == "error":
        logger.error(message, extra=attributes)
    elif level == "exception":
        logger.exception(message, extra=attributes)
    else:
        logger.info(message, extra=attributes)

# --- Log custom event ---
# def log_custom_event(logger, event_name: str, level: str = "info", **custom_dimensions):
#     """
#     Logs a custom event with a name and optional custom dimensions.
#     Reserved keys are prefixed to avoid conflicts.
#     """
#     attributes = {
#         (f"meta_{k}" if k in RESERVED_LOG_KEYS else k): v
#         for k, v in custom_dimensions.items()
#     }
    
#     extra_attrs = {
#         "microsoft.custom_event.name": event_name,
#         **attributes
#     }

#     level = level.lower()
#     if level == "debug":
#         logger.debug(f"Custom event: {event_name}", extra=extra_attrs)
#     elif level == "warning":
#         logger.warning(f"Custom event: {event_name}", extra=extra_attrs)
#     elif level == "error":
#         logger.error(f"Custom event: {event_name}", extra=extra_attrs)
#     elif level == "exception":
#         logger.exception(f"Custom event: {event_name}", extra=extra_attrs)
#     else:
#         logger.info(f"Custom event: {event_name}", extra=extra_attrs)

#@tracer.start_as_current_span("log_custom_event_fn")
def log_custom_event(logger, event_name: str, level: str = "info", **custom_dimensions):
    """
    Logs a custom event with a name and optional custom dimensions.
    Reserved keys are prefixed to avoid conflicts.
    """
    attributes = {
        (f"meta_{k}" if k in RESERVED_LOG_KEYS else k): v
        for k, v in custom_dimensions.items()
    }
    
    level = level.lower()

    # Map log level string to numeric severity like Application Insights
    severity_map = {
        "debug": 0,
        "info": 1,
        "warning": 2,
        "error": 3,
        "exception": 4
    }

    extra_attrs = {
        "microsoft.custom_event.name": event_name,
        "severityLevel": severity_map.get(level, 1),  # default to Info
        **attributes,
    }

    logger.info(f"Custom event: {event_name}", extra=extra_attrs)

# --- Log exception ---
def log_exception(logger, error: Exception, **custom_dimensions):
    """
    Logs an exception with optional custom dimensions.
    """
    logger.exception(f"Exception occurred: {str(error)}", extra=custom_dimensions)

# --- Record custom metric ---
def log_custom_metric(metric_name: str, value: float = 1.0, **custom_dimensions):
    """
    Records a custom metric to Azure Monitor using OpenTelemetry.
    Falls back to logging a warning if metric recording fails.
    """
    try:
        # Enable custom metric namespace for Application Insights
        os.environ["APPLICATIONINSIGHTS_METRIC_NAMESPACE_OPT_IN"] = "true"

        meter = metrics.get_meter_provider().get_meter("ai_pipeline_meter")
        counter = meter.create_counter(metric_name)
        counter.add(value, attributes=custom_dimensions)

    except Exception as e:
        # Fallback log if metrics fail
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to record metric '{metric_name}': {e}")