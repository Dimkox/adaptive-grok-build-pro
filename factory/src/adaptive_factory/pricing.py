"""Pure, deterministic pricing for versioned provider usage facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping


_MICRO_USD_PER_MILLION_TOKENS = 1_000_000
_MAX_SIGNED_BIGINT = 2**63 - 1
_PRICE_TABLE_FIELDS = frozenset(
    {
        "schema_version",
        "input_usd_micros_per_million",
        "output_usd_micros_per_million",
        "reasoning_usd_micros_per_million",
        "cached_input_usd_micros_per_million",
        "cache_write_usd_micros_per_million",
    }
)


class PricingContractError(ValueError):
    """Raised when a usage fact or immutable pricing table is unsafe to price."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _nonnegative_bigint(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise PricingContractError("invalid_nonnegative_integer", name)
    if value > _MAX_SIGNED_BIGINT:
        raise PricingContractError("integer_overflow", name)
    return value


@dataclass(frozen=True)
class UsageTokens:
    """Five mutually exclusive normalized provider billing buckets."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _nonnegative_bigint(value, name)
        if self.total_tokens > _MAX_SIGNED_BIGINT:
            raise PricingContractError("integer_overflow", "total_tokens")

    @property
    def total_tokens(self) -> int:
        return sum(asdict(self).values())


@dataclass(frozen=True)
class PriceTableV1:
    """Closed schema-v1 rates in integer micro-USD per million tokens."""

    schema_version: int
    input_usd_micros_per_million: int
    output_usd_micros_per_million: int
    reasoning_usd_micros_per_million: int
    cached_input_usd_micros_per_million: int
    cache_write_usd_micros_per_million: int

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise PricingContractError("unsupported_price_table_schema")
        for name, value in asdict(self).items():
            if name != "schema_version":
                _nonnegative_bigint(value, name)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PriceTableV1":
        if not isinstance(value, Mapping):
            raise PricingContractError("invalid_price_table")
        fields = frozenset(value)
        unknown = fields - _PRICE_TABLE_FIELDS
        missing = _PRICE_TABLE_FIELDS - fields
        if unknown:
            raise PricingContractError("unknown_price_table_fields", ",".join(sorted(unknown)))
        if missing:
            raise PricingContractError("missing_price_table_fields", ",".join(sorted(missing)))
        return cls(**dict(value))

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def price_table_digest(table: PriceTableV1) -> str:
    """Return the SHA-256 digest of the canonical closed price-table JSON."""
    if not isinstance(table, PriceTableV1):
        raise PricingContractError("invalid_price_table")
    canonical = json.dumps(
        table.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def calculate_cost_usd_micros(
    usage: UsageTokens, table: PriceTableV1, supplied_price_table_digest: str
) -> int:
    """Derive cost by flooring every token bucket independently before summing."""
    if not isinstance(usage, UsageTokens):
        raise PricingContractError("invalid_usage_tokens")
    if not isinstance(supplied_price_table_digest, str) or supplied_price_table_digest != price_table_digest(table):
        raise PricingContractError("price_table_digest_mismatch")

    cost = sum(
        tokens * rate // _MICRO_USD_PER_MILLION_TOKENS
        for tokens, rate in zip(
            asdict(usage).values(),
            (
                table.input_usd_micros_per_million,
                table.output_usd_micros_per_million,
                table.reasoning_usd_micros_per_million,
                table.cached_input_usd_micros_per_million,
                table.cache_write_usd_micros_per_million,
            ),
            strict=True,
        )
    )
    if cost > _MAX_SIGNED_BIGINT:
        raise PricingContractError("integer_overflow", "cost_usd_micros")
    return cost
