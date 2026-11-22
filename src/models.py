"""Data models for the STR Deal Finder."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PermitStatus(Enum):
    ALLOWED = "ALLOWED"
    CONDITIONAL = "CONDITIONAL"
    RESTRICTED = "RESTRICTED"
    BANNED = "BANNED"
    UNKNOWN = "UNKNOWN"


class RevenueSource(Enum):
    MASHVISOR = "mashvisor"
    HEURISTIC = "heuristic"
    MANUAL = "manual"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Property:
    zpid: str
    address: str
    city: str
    state: str
    zipcode: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: Optional[int] = None
    lot_size: Optional[int] = None
    hoa_monthly: Optional[float] = None
    property_tax_annual: Optional[float] = None
    year_built: Optional[int] = None
    listing_url: str = ""
    market: str = ""
    property_type: str = ""

    @property
    def full_address(self) -> str:
        return f"{self.address}, {self.city}, {self.state} {self.zipcode}"


@dataclass
class RevenueEstimate:
    annual_revenue: float
    nightly_rate: float
    occupancy_rate: float
    source: RevenueSource = RevenueSource.HEURISTIC
    confidence: Confidence = Confidence.MEDIUM


@dataclass
class ExpenseBreakdown:
    mortgage_annual: float = 0.0
    property_tax: float = 0.0
    insurance: float = 0.0
    hoa_annual: float = 0.0
    property_management: float = 0.0
    utilities: float = 0.0
    maintenance: float = 0.0
    cleaning: float = 0.0
    platform_fees: float = 0.0
    supplies: float = 0.0
    str_permit: float = 0.0
    accounting: float = 0.0
    furniture_reserve: float = 0.0
    landscaping: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.mortgage_annual
            + self.property_tax
            + self.insurance
            + self.hoa_annual
            + self.property_management
            + self.utilities
            + self.maintenance
            + self.cleaning
            + self.platform_fees
            + self.supplies
            + self.str_permit
            + self.accounting
            + self.furniture_reserve
            + self.landscaping
        )


@dataclass
class PermitInfo:
    status: PermitStatus = PermitStatus.UNKNOWN
    permit_required: bool = True
    permit_type: str = ""
    restrictions: str = ""
    notes: str = ""


@dataclass
class ImprovementBreakdown:
    furnishing_cost: float = 0.0
    amenity_cost: float = 0.0
    cosmetic_rehab: float = 0.0
    amenity_details: list[tuple[str, float]] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.furnishing_cost + self.amenity_cost + self.cosmetic_rehab


@dataclass
class Deal:
    property: Property
    revenue: RevenueEstimate
    expenses: ExpenseBreakdown
    permit: PermitInfo
    improvements: ImprovementBreakdown = field(default_factory=ImprovementBreakdown)
    cash_invested: float = 0.0
    annual_cash_flow: float = 0.0
    cash_on_cash_return: float = 0.0

    @property
    def is_good_deal(self) -> bool:
        return (
            self.cash_on_cash_return >= 0.10
            and self.permit.status != PermitStatus.BANNED
        )

    @property
    def summary_line(self) -> str:
        return (
            f"${self.property.price:,.0f} | "
            f"{self.property.bedrooms}bd/{self.property.bathrooms}ba | "
            f"CoC: {self.cash_on_cash_return:.1%} | "
            f"Rev: ${self.revenue.annual_revenue:,.0f} | "
            f"Permit: {self.permit.status.value} | "
            f"{self.property.full_address}"
        )
