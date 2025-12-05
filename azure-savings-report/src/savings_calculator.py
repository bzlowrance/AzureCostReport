"""
Azure Savings Report - Savings Calculator
Calculates savings across different categories
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class SavingsSummary:
    """Summary of savings for a category"""
    category: str
    retail_cost: float
    negotiated_cost: float
    effective_cost: float
    negotiated_savings: float
    commitment_savings: float
    total_savings: float
    savings_percentage: float


@dataclass
class SavingsReport:
    """Complete savings report"""
    customer_name: str
    report_period_start: datetime
    report_period_end: datetime
    currency: str
    
    # Totals
    total_retail_cost: float
    total_negotiated_cost: float
    total_effective_cost: float
    total_savings: float
    total_savings_percentage: float
    
    # Breakdown by category
    negotiated_discount_savings: SavingsSummary
    reserved_instance_savings: SavingsSummary
    savings_plan_savings: SavingsSummary
    ahb_savings: SavingsSummary
    devtest_savings: SavingsSummary
    
    # Details
    savings_by_service: pd.DataFrame
    savings_by_subscription: pd.DataFrame
    monthly_trend: pd.DataFrame
    top_savings_resources: pd.DataFrame


class SavingsCalculator:
    """Calculates savings from cost data"""
    
    def __init__(self, costs_df: pd.DataFrame, prices_df: pd.DataFrame = None):
        self.costs_df = costs_df
        self.prices_df = prices_df
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare and normalize the cost data"""
        df = self.costs_df.copy()
        
        # Ensure required columns exist with defaults
        required_columns = {
            'ListCost': 0,
            'BilledCost': 0,
            'EffectiveCost': 0,
            'PricingCategory': 'Standard',
            'CommitmentDiscountCategory': '',
            'ServiceCategory': 'Unknown',
            'SubAccountName': 'Unknown',
            'ResourceName': 'Unknown'
        }
        
        for col, default in required_columns.items():
            if col not in df.columns:
                df[col] = default
        
        # Calculate derived columns
        df['NegotiatedSavings'] = df['ListCost'] - df['BilledCost']
        df['CommitmentSavings'] = df['BilledCost'] - df['EffectiveCost']
        df['TotalSavings'] = df['ListCost'] - df['EffectiveCost']
        
        # Categorize savings
        df['SavingsCategory'] = df.apply(self._categorize_savings, axis=1)
        
        self.costs_df = df
    
    def _categorize_savings(self, row) -> str:
        """Categorize the type of savings for a row"""
        pricing_category = str(row.get('PricingCategory', '')).lower()
        commitment_category = str(row.get('CommitmentDiscountCategory', '')).lower()
        sku_details = str(row.get('x_SkuDetails', '')).lower()
        sub_name = str(row.get('SubAccountName', '')).lower()
        
        if pricing_category == 'committed':
            if commitment_category == 'usage':
                return 'Reserved Instance'
            elif commitment_category == 'spend':
                return 'Savings Plan'
        
        if 'ahb' in sku_details or 'hybridbenefit' in sku_details or 'hybrid benefit' in sku_details:
            return 'Azure Hybrid Benefit'
        
        if 'devtest' in sub_name or 'dev/test' in sub_name or 'dev-test' in sub_name:
            return 'Dev/Test Pricing'
        
        return 'Negotiated Rate'
    
    def calculate_negotiated_discount_savings(self) -> SavingsSummary:
        """Calculate savings from EA/MCA negotiated discounts"""
        # Filter for standard pricing (not commitment-based)
        df = self.costs_df[self.costs_df['SavingsCategory'] == 'Negotiated Rate']
        
        retail_cost = df['ListCost'].sum()
        negotiated_cost = df['BilledCost'].sum()
        effective_cost = df['EffectiveCost'].sum()
        negotiated_savings = retail_cost - negotiated_cost
        
        return SavingsSummary(
            category="Negotiated Discount",
            retail_cost=retail_cost,
            negotiated_cost=negotiated_cost,
            effective_cost=effective_cost,
            negotiated_savings=negotiated_savings,
            commitment_savings=0,
            total_savings=negotiated_savings,
            savings_percentage=(negotiated_savings / retail_cost * 100) if retail_cost > 0 else 0
        )
    
    def calculate_ri_savings(self) -> SavingsSummary:
        """Calculate savings from Reserved Instances"""
        df = self.costs_df[self.costs_df['SavingsCategory'] == 'Reserved Instance']
        
        retail_cost = df['ListCost'].sum()
        negotiated_cost = df['BilledCost'].sum()
        effective_cost = df['EffectiveCost'].sum()
        negotiated_savings = retail_cost - negotiated_cost
        commitment_savings = negotiated_cost - effective_cost
        
        return SavingsSummary(
            category="Reserved Instances",
            retail_cost=retail_cost,
            negotiated_cost=negotiated_cost,
            effective_cost=effective_cost,
            negotiated_savings=negotiated_savings,
            commitment_savings=commitment_savings,
            total_savings=retail_cost - effective_cost,
            savings_percentage=((retail_cost - effective_cost) / retail_cost * 100) if retail_cost > 0 else 0
        )
    
    def calculate_savings_plan_savings(self) -> SavingsSummary:
        """Calculate savings from Savings Plans"""
        df = self.costs_df[self.costs_df['SavingsCategory'] == 'Savings Plan']
        
        retail_cost = df['ListCost'].sum()
        negotiated_cost = df['BilledCost'].sum()
        effective_cost = df['EffectiveCost'].sum()
        negotiated_savings = retail_cost - negotiated_cost
        commitment_savings = negotiated_cost - effective_cost
        
        return SavingsSummary(
            category="Savings Plans",
            retail_cost=retail_cost,
            negotiated_cost=negotiated_cost,
            effective_cost=effective_cost,
            negotiated_savings=negotiated_savings,
            commitment_savings=commitment_savings,
            total_savings=retail_cost - effective_cost,
            savings_percentage=((retail_cost - effective_cost) / retail_cost * 100) if retail_cost > 0 else 0
        )
    
    def calculate_ahb_savings(self) -> SavingsSummary:
        """Calculate savings from Azure Hybrid Benefit"""
        df = self.costs_df[self.costs_df['SavingsCategory'] == 'Azure Hybrid Benefit']
        
        # AHB savings are typically the difference between PAYG and AHB pricing
        # The ListCost should reflect what would have been paid without AHB
        retail_cost = df['ListCost'].sum()
        negotiated_cost = df['BilledCost'].sum()
        effective_cost = df['EffectiveCost'].sum()
        
        # AHB typically saves 40-80% on Windows/SQL licensing
        # If ListCost isn't populated, estimate based on service type
        if retail_cost == 0 and effective_cost > 0:
            # Estimate: AHB typically saves ~40% on compute
            retail_cost = effective_cost * 1.67  # Roughly 40% savings
        
        return SavingsSummary(
            category="Azure Hybrid Benefit",
            retail_cost=retail_cost,
            negotiated_cost=negotiated_cost,
            effective_cost=effective_cost,
            negotiated_savings=retail_cost - negotiated_cost,
            commitment_savings=0,
            total_savings=retail_cost - effective_cost,
            savings_percentage=((retail_cost - effective_cost) / retail_cost * 100) if retail_cost > 0 else 0
        )
    
    def calculate_devtest_savings(self) -> SavingsSummary:
        """Calculate savings from Dev/Test pricing"""
        df = self.costs_df[self.costs_df['SavingsCategory'] == 'Dev/Test Pricing']
        
        retail_cost = df['ListCost'].sum()
        negotiated_cost = df['BilledCost'].sum()
        effective_cost = df['EffectiveCost'].sum()
        
        return SavingsSummary(
            category="Dev/Test Pricing",
            retail_cost=retail_cost,
            negotiated_cost=negotiated_cost,
            effective_cost=effective_cost,
            negotiated_savings=retail_cost - negotiated_cost,
            commitment_savings=0,
            total_savings=retail_cost - effective_cost,
            savings_percentage=((retail_cost - effective_cost) / retail_cost * 100) if retail_cost > 0 else 0
        )
    
    def calculate_savings_by_service(self) -> pd.DataFrame:
        """Calculate savings breakdown by service"""
        df = self.costs_df.groupby('ServiceCategory').agg({
            'ListCost': 'sum',
            'BilledCost': 'sum',
            'EffectiveCost': 'sum',
            'NegotiatedSavings': 'sum',
            'CommitmentSavings': 'sum',
            'TotalSavings': 'sum'
        }).reset_index()
        
        df['SavingsPercentage'] = (df['TotalSavings'] / df['ListCost'] * 100).round(2)
        df = df.sort_values('TotalSavings', ascending=False)
        
        return df
    
    def calculate_savings_by_subscription(self) -> pd.DataFrame:
        """Calculate savings breakdown by subscription"""
        df = self.costs_df.groupby(['SubAccountId', 'SubAccountName']).agg({
            'ListCost': 'sum',
            'BilledCost': 'sum',
            'EffectiveCost': 'sum',
            'NegotiatedSavings': 'sum',
            'CommitmentSavings': 'sum',
            'TotalSavings': 'sum'
        }).reset_index()
        
        df['SavingsPercentage'] = (df['TotalSavings'] / df['ListCost'] * 100).round(2)
        df = df.sort_values('TotalSavings', ascending=False)
        
        return df
    
    def calculate_monthly_trend(self) -> pd.DataFrame:
        """Calculate monthly savings trend"""
        df = self.costs_df.copy()
        
        if 'ChargePeriodStart' in df.columns:
            df['Month'] = pd.to_datetime(df['ChargePeriodStart']).dt.to_period('M')
        else:
            # If no date column, return empty
            return pd.DataFrame()
        
        monthly = df.groupby('Month').agg({
            'ListCost': 'sum',
            'BilledCost': 'sum',
            'EffectiveCost': 'sum',
            'NegotiatedSavings': 'sum',
            'CommitmentSavings': 'sum',
            'TotalSavings': 'sum'
        }).reset_index()
        
        monthly['Month'] = monthly['Month'].astype(str)
        return monthly
    
    def calculate_top_savings_resources(self, top_n: int = 20) -> pd.DataFrame:
        """Get top resources by savings amount"""
        df = self.costs_df.groupby(['ResourceId', 'ResourceName', 'ServiceCategory', 'SavingsCategory']).agg({
            'ListCost': 'sum',
            'EffectiveCost': 'sum',
            'TotalSavings': 'sum'
        }).reset_index()
        
        df['SavingsPercentage'] = (df['TotalSavings'] / df['ListCost'] * 100).round(2)
        df = df.sort_values('TotalSavings', ascending=False).head(top_n)
        
        return df
    
    def generate_report(self, customer_name: str, start_date: datetime, end_date: datetime, currency: str = "USD") -> SavingsReport:
        """Generate complete savings report"""
        
        # Calculate all savings categories
        negotiated = self.calculate_negotiated_discount_savings()
        ri = self.calculate_ri_savings()
        sp = self.calculate_savings_plan_savings()
        ahb = self.calculate_ahb_savings()
        devtest = self.calculate_devtest_savings()
        
        # Calculate totals
        total_retail = sum([
            negotiated.retail_cost,
            ri.retail_cost,
            sp.retail_cost,
            ahb.retail_cost,
            devtest.retail_cost
        ])
        
        total_negotiated = sum([
            negotiated.negotiated_cost,
            ri.negotiated_cost,
            sp.negotiated_cost,
            ahb.negotiated_cost,
            devtest.negotiated_cost
        ])
        
        total_effective = sum([
            negotiated.effective_cost,
            ri.effective_cost,
            sp.effective_cost,
            ahb.effective_cost,
            devtest.effective_cost
        ])
        
        total_savings = total_retail - total_effective
        savings_pct = (total_savings / total_retail * 100) if total_retail > 0 else 0
        
        return SavingsReport(
            customer_name=customer_name,
            report_period_start=start_date,
            report_period_end=end_date,
            currency=currency,
            total_retail_cost=total_retail,
            total_negotiated_cost=total_negotiated,
            total_effective_cost=total_effective,
            total_savings=total_savings,
            total_savings_percentage=savings_pct,
            negotiated_discount_savings=negotiated,
            reserved_instance_savings=ri,
            savings_plan_savings=sp,
            ahb_savings=ahb,
            devtest_savings=devtest,
            savings_by_service=self.calculate_savings_by_service(),
            savings_by_subscription=self.calculate_savings_by_subscription(),
            monthly_trend=self.calculate_monthly_trend(),
            top_savings_resources=self.calculate_top_savings_resources()
        )
