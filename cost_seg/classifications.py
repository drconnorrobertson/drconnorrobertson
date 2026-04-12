"""IRS asset classification categories for cost segregation studies."""

# MACRS recovery periods and common building components
ASSET_CLASSES = {
    "5-year": {
        "recovery_period": 5,
        "description": "5-Year Personal Property",
        "components": [
            "Carpeting (removable)",
            "Appliances",
            "Task lighting",
            "Decorative lighting",
            "Window treatments",
            "Certain electrical connections",
            "Computer/data wiring",
            "Security systems (non-structural)",
            "Signage (interior)",
        ],
    },
    "7-year": {
        "recovery_period": 7,
        "description": "7-Year Personal Property",
        "components": [
            "Furniture and fixtures",
            "Office equipment",
            "Specialty kitchen equipment",
            "Storage systems",
            "Movable partitions",
            "Decorative millwork",
            "Accent walls",
        ],
    },
    "15-year": {
        "recovery_period": 15,
        "description": "15-Year Land Improvements",
        "components": [
            "Parking lots and paving",
            "Sidewalks and curbing",
            "Landscaping",
            "Fencing",
            "Outdoor lighting",
            "Drainage systems",
            "Retaining walls",
            "Irrigation systems",
            "Signage (exterior)",
        ],
    },
    "27.5-year": {
        "recovery_period": 27.5,
        "description": "27.5-Year Residential Rental Property",
        "components": [
            "Structural components (residential)",
            "Roofing (residential)",
            "HVAC (residential)",
            "Plumbing (residential, structural)",
            "Electrical (residential, structural)",
            "Walls and ceilings (residential)",
        ],
    },
    "39-year": {
        "recovery_period": 39,
        "description": "39-Year Nonresidential Real Property",
        "components": [
            "Structural components",
            "Roofing",
            "HVAC (structural/central)",
            "Plumbing (structural)",
            "Electrical (structural)",
            "Walls, floors, ceilings (structural)",
            "Elevators and escalators",
            "Fire protection/sprinkler (structural)",
            "Load-bearing framework",
        ],
    },
}

# Default percentage allocations by property type
DEFAULT_ALLOCATIONS = {
    "office": {
        "5-year": 0.08,
        "7-year": 0.06,
        "15-year": 0.10,
        "39-year": 0.76,
    },
    "retail": {
        "5-year": 0.10,
        "7-year": 0.05,
        "15-year": 0.12,
        "39-year": 0.73,
    },
    "restaurant": {
        "5-year": 0.15,
        "7-year": 0.10,
        "15-year": 0.08,
        "39-year": 0.67,
    },
    "warehouse": {
        "5-year": 0.05,
        "7-year": 0.03,
        "15-year": 0.15,
        "39-year": 0.77,
    },
    "manufacturing": {
        "5-year": 0.12,
        "7-year": 0.08,
        "15-year": 0.10,
        "39-year": 0.70,
    },
    "medical": {
        "5-year": 0.12,
        "7-year": 0.08,
        "15-year": 0.08,
        "39-year": 0.72,
    },
    "hotel": {
        "5-year": 0.15,
        "7-year": 0.10,
        "15-year": 0.10,
        "39-year": 0.65,
    },
    "apartment": {
        "5-year": 0.10,
        "7-year": 0.05,
        "15-year": 0.10,
        "27.5-year": 0.75,
    },
    "multifamily": {
        "5-year": 0.10,
        "7-year": 0.05,
        "15-year": 0.10,
        "27.5-year": 0.75,
    },
}
