"""
mcp2/tools/math_tools.py
--------------------------
Simple math tools for MCP2 server.
No orchestration needed here — pure computation, no A2A delegation.
"""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b  # e.g. add(3, 4) → 7.0


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b  # e.g. multiply(3, 4) → 12.0


def power(base: float, exp: float) -> float:
    """Raise base to the power of exp."""
    return base ** exp  # e.g. power(2, 10) → 1024.0


def average(numbers: list) -> float:
    """Return average of a list of numbers."""
    if not numbers:
        return 0.0
    # Sum all values and divide by count
    return sum(numbers) / len(numbers)  # e.g. [1,2,3] → 2.0
