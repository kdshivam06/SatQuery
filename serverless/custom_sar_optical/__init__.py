"""Provider-neutral serverless inference package for custom SAR-optical model."""

from serverless.custom_sar_optical.handler import handle_inference

__all__ = ["handle_inference"]
