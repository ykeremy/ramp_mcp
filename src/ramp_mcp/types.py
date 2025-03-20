from typing import Literal, TypeAlias

# these should be enums
# claude likes to pass in empty strings to mean null
Interval: TypeAlias = Literal[
    "ANNUAL",
    "WEEKLY",
    "MONTHLY",
    "TOTAL",
    "",
]
Icon: TypeAlias = Literal[
    "AccountingServicesIcon",
    "AdvertisingIcon",
    "CONTRACTORS_AND_PROFESSIONAL_SERVICES",
    "CUSTOM",
    "CardIcon",
    "EducationStipendIcon",
    "EmployeeRewardsIcon",
    "GroundTransportationIcon",
    "LegalFeesIcon",
    "LodgingIcon",
    "LunchOrderingIcon",
    "OnboardingIcon",
    "PerDiemCardIcon",
    "SOFTWARE",
    "SaasSubscriptionIcon",
    "SoftwareTrialIcon",
    "SuppliesIcon",
    "TeamSocialIcon",
    "TravelExpensesIcon",
    "VirtualEventIcon",
    "WellnessIcon",
    "WorkFromHomeIcon",
    "",
]
Role: TypeAlias = Literal[
    "IT_ADMIN",
    "BUSINESS_ADMIN",
    "BUSINESS_OWNER",
    "BUSINESS_USER",
    "GUEST_USER",
    "",
]
