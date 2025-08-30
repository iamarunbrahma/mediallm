#!/usr/bin/env python3
# Author: Arun Brahma

from __future__ import annotations

from typing import Final


class FilterValidator:
    """Validates and fixes FFmpeg filter chains."""

    # Scale filter validation patterns
    _SCALE_FILTER_PATTERNS: Final[dict[str, str]] = {
        "9/16": "scale=iw:iw*16/9:force_original_aspect_ratio=decrease",
        "16/9": "scale=iw:iw*9/16:force_original_aspect_ratio=decrease",
        "ih*9/16:ih": "scale=iw:iw*16/9:force_original_aspect_ratio=decrease",
        "iw*16/9:iw": "scale=iw:iw*9/16:force_original_aspect_ratio=decrease",
    }

    @classmethod
    def validate_and_fix_scale_filter(cls, scale_filter: str | None) -> str | None:
        """Validate and fix scale filter to ensure even dimensions for codec compatibility."""
        if not scale_filter or not scale_filter.startswith("scale="):
            return scale_filter

        # Extract the scale parameters (remove "scale=" prefix)
        scale_params = scale_filter[6:]

        # Check if it's a simple width:height format
        if ":" in scale_params and not any(op in scale_params for op in ["*", "/", "+", "-"]):
            return cls._fix_simple_scale(scale_params)

        # For aspect ratio changes that might result in odd dimensions
        for pattern, replacement in cls._SCALE_FILTER_PATTERNS.items():
            if pattern in scale_params:
                return replacement

        # For other complex expressions, add force_original_aspect_ratio=decrease to help FFmpeg
        # handle dimension calculations more safely, but only if not already present
        if "force_original_aspect_ratio" not in scale_params:
            return f"scale={scale_params}:force_original_aspect_ratio=decrease"

        return scale_filter

    @classmethod
    def _fix_simple_scale(cls, scale_params: str) -> str:
        """Fix simple scale parameters to ensure even dimensions."""
        parts = scale_params.split(":")
        if len(parts) >= 2:
            try:
                width = int(parts[0])
                height = int(parts[1])
                # Make sure both dimensions are even for codec compatibility
                if width % 2 != 0:
                    width -= 1
                if height % 2 != 0:
                    height -= 1
                # Reconstruct the scale filter with additional parameters if any
                result = f"scale={width}:{height}"
                if len(parts) > 2:
                    result += ":" + ":".join(parts[2:])
                # Add force_original_aspect_ratio=decrease if not already present
                if "force_original_aspect_ratio" not in result:
                    result += ":force_original_aspect_ratio=decrease"
                return result
            except ValueError:
                # If parsing fails, return original filter
                pass

        return f"scale={scale_params}"

    @classmethod
    def validate_and_fix_filter_chain(cls, filter_chain: list[str]) -> list[str]:
        """Validate and fix filter chain with proper scale filter handling."""
        validated_filters = []

        for filter_item in filter_chain:
            # Skip empty or whitespace-only filters
            if not filter_item or not filter_item.strip():
                continue

            if filter_item.startswith("scale="):
                # Apply scale filter validation for even dimensions
                fixed_filter = cls.validate_and_fix_scale_filter(filter_item)
                if fixed_filter:
                    validated_filters.append(fixed_filter)
            else:
                # For non-scale filters, don't add force_original_aspect_ratio=decrease
                # as it's not supported by most filters
                validated_filters.append(filter_item)

        return validated_filters

    @classmethod
    def combine_filters(cls, filters: list[str]) -> str:
        """Combine multiple filters into a single filter string."""
        # Remove duplicate scale filters (keep the last one)
        scale_filters = [f for f in filters if f.startswith("scale=")]
        non_scale_filters = [f for f in filters if not f.startswith("scale=")]

        # If there are multiple scale filters, keep only the last one
        if len(scale_filters) > 1:
            scale_filters = [scale_filters[-1]]

        # Reconstruct the filter chain
        final_filters = non_scale_filters + scale_filters

        # Join filters with commas
        if final_filters:
            filter_str = ",".join(final_filters)
            # Ensure the filter string is not empty after joining
            if filter_str.strip():
                return filter_str

        return ""
