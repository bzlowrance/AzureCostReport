"""
Azure Savings Report - KQL Queries for ADX
Pre-built KQL queries for common savings analysis scenarios
"""

# Comprehensive savings summary query
SAVINGS_SUMMARY_QUERY = """
// Azure Savings Realization Summary
// This query calculates savings across all categories
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| extend 
    SavingsCategory = case(
        PricingCategory == "Committed" and CommitmentDiscountCategory == "Usage", "Reserved Instance",
        PricingCategory == "Committed" and CommitmentDiscountCategory == "Spend", "Savings Plan",
        x_SkuDetails has_any ("AHB", "HybridBenefit", "Hybrid Benefit"), "Azure Hybrid Benefit",
        SubAccountName has_any ("DevTest", "Dev/Test", "Dev-Test"), "Dev/Test Pricing",
        "Negotiated Rate"
    )
| summarize 
    RetailCost = sum(ListCost),
    NegotiatedCost = sum(BilledCost),
    EffectiveCost = sum(EffectiveCost)
    by SavingsCategory
| extend 
    NegotiatedSavings = RetailCost - NegotiatedCost,
    CommitmentSavings = NegotiatedCost - EffectiveCost,
    TotalSavings = RetailCost - EffectiveCost
| extend 
    SavingsPercentage = round(TotalSavings / RetailCost * 100, 2)
| order by TotalSavings desc
"""

# Savings by service category query
SAVINGS_BY_SERVICE_QUERY = """
// Savings by Service Category
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| summarize 
    RetailCost = sum(ListCost),
    NegotiatedCost = sum(BilledCost),
    EffectiveCost = sum(EffectiveCost)
    by ServiceCategory
| extend 
    NegotiatedSavings = RetailCost - NegotiatedCost,
    CommitmentSavings = NegotiatedCost - EffectiveCost,
    TotalSavings = RetailCost - EffectiveCost
| extend 
    SavingsPercentage = round(TotalSavings / RetailCost * 100, 2)
| where TotalSavings > 0
| order by TotalSavings desc
| take 20
"""

# Monthly savings trend query
MONTHLY_TREND_QUERY = """
// Monthly Savings Trend
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| summarize 
    RetailCost = sum(ListCost),
    NegotiatedCost = sum(BilledCost),
    EffectiveCost = sum(EffectiveCost)
    by Month = startofmonth(ChargePeriodStart)
| extend 
    NegotiatedSavings = RetailCost - NegotiatedCost,
    CommitmentSavings = NegotiatedCost - EffectiveCost,
    TotalSavings = RetailCost - EffectiveCost
| extend 
    SavingsPercentage = round(TotalSavings / RetailCost * 100, 2)
| order by Month asc
"""

# Reserved Instance utilization and savings
RI_UTILIZATION_QUERY = """
// Reserved Instance Utilization and Savings
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| where PricingCategory == "Committed" and CommitmentDiscountCategory == "Usage"
| summarize 
    RetailCost = sum(ListCost),
    EffectiveCost = sum(EffectiveCost),
    UsedQuantity = sum(PricingQuantity)
    by CommitmentDiscountId, CommitmentDiscountName, ServiceCategory
| extend 
    Savings = RetailCost - EffectiveCost,
    SavingsPercentage = round((RetailCost - EffectiveCost) / RetailCost * 100, 2)
| order by Savings desc
"""

# Savings Plan utilization and savings
SP_UTILIZATION_QUERY = """
// Savings Plan Utilization and Savings
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| where PricingCategory == "Committed" and CommitmentDiscountCategory == "Spend"
| summarize 
    RetailCost = sum(ListCost),
    EffectiveCost = sum(EffectiveCost)
    by CommitmentDiscountId, CommitmentDiscountName, ServiceCategory
| extend 
    Savings = RetailCost - EffectiveCost,
    SavingsPercentage = round((RetailCost - EffectiveCost) / RetailCost * 100, 2)
| order by Savings desc
"""

# Azure Hybrid Benefit identification
AHB_SAVINGS_QUERY = """
// Azure Hybrid Benefit Savings
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| where x_SkuDetails has_any ("AHB", "HybridBenefit", "Hybrid Benefit", "AHUB")
    or x_SkuMeterName has "Windows"
    or x_SkuMeterName has "SQL"
| extend 
    AHBType = case(
        x_SkuMeterName has "SQL", "SQL Server",
        x_SkuMeterName has "Windows", "Windows Server",
        "Other"
    )
| summarize 
    RetailCost = sum(ListCost),
    EffectiveCost = sum(EffectiveCost),
    ResourceCount = dcount(ResourceId)
    by AHBType, ServiceCategory
| extend 
    Savings = RetailCost - EffectiveCost,
    SavingsPercentage = round((RetailCost - EffectiveCost) / RetailCost * 100, 2)
| order by Savings desc
"""

# Retail vs Negotiated price comparison by meter
PRICE_COMPARISON_QUERY = """
// Retail vs Negotiated Price Comparison
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| where PricingCategory == "Standard" // On-demand pricing only
| summarize 
    TotalQuantity = sum(PricingQuantity),
    AvgListPrice = avg(ListUnitPrice),
    AvgContractPrice = avg(ContractedUnitPrice),
    TotalListCost = sum(ListCost),
    TotalBilledCost = sum(BilledCost)
    by ServiceCategory, x_SkuMeterName
| extend 
    DiscountPercentage = round((AvgListPrice - AvgContractPrice) / AvgListPrice * 100, 2),
    TotalSavings = TotalListCost - TotalBilledCost
| where TotalSavings > 100 // Filter out noise
| order by TotalSavings desc
| take 50
"""

# Subscription-level savings breakdown
SUBSCRIPTION_SAVINGS_QUERY = """
// Savings by Subscription
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| summarize 
    RetailCost = sum(ListCost),
    NegotiatedCost = sum(BilledCost),
    EffectiveCost = sum(EffectiveCost)
    by SubAccountId, SubAccountName
| extend 
    NegotiatedSavings = RetailCost - NegotiatedCost,
    CommitmentSavings = NegotiatedCost - EffectiveCost,
    TotalSavings = RetailCost - EffectiveCost
| extend 
    SavingsPercentage = round(TotalSavings / RetailCost * 100, 2)
| order by TotalSavings desc
"""

# Top resources by savings
TOP_RESOURCES_QUERY = """
// Top Resources by Savings
let StartDate = datetime({start_date});
let EndDate = datetime({end_date});
//
Costs
| where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
| summarize 
    RetailCost = sum(ListCost),
    EffectiveCost = sum(EffectiveCost)
    by ResourceId, ResourceName, ServiceCategory, SubAccountName
| extend 
    TotalSavings = RetailCost - EffectiveCost,
    SavingsPercentage = round((RetailCost - EffectiveCost) / RetailCost * 100, 2)
| where TotalSavings > 0
| order by TotalSavings desc
| take 50
"""


def format_query(query: str, start_date: str, end_date: str) -> str:
    """Format a query template with date parameters"""
    return query.format(start_date=start_date, end_date=end_date)


# Export all queries
QUERIES = {
    'savings_summary': SAVINGS_SUMMARY_QUERY,
    'savings_by_service': SAVINGS_BY_SERVICE_QUERY,
    'monthly_trend': MONTHLY_TREND_QUERY,
    'ri_utilization': RI_UTILIZATION_QUERY,
    'sp_utilization': SP_UTILIZATION_QUERY,
    'ahb_savings': AHB_SAVINGS_QUERY,
    'price_comparison': PRICE_COMPARISON_QUERY,
    'subscription_savings': SUBSCRIPTION_SAVINGS_QUERY,
    'top_resources': TOP_RESOURCES_QUERY
}
