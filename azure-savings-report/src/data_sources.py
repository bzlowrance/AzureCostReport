"""
Azure Savings Report - Data Sources
Abstraction layer for different data sources (ADX, Storage, API)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd


@dataclass
class CostRecord:
    """Standardized cost record based on FOCUS schema"""
    charge_period_start: datetime
    charge_period_end: datetime
    billing_account_id: str
    billing_account_name: str
    sub_account_id: str  # Subscription ID
    sub_account_name: str  # Subscription Name
    resource_id: str
    resource_name: str
    resource_type: str
    service_name: str
    service_category: str
    region: str
    pricing_category: str  # OnDemand, Committed, etc.
    pricing_model: str
    charge_category: str
    billed_cost: float
    effective_cost: float
    list_cost: float  # Retail cost
    list_unit_price: float
    contracted_unit_price: float
    pricing_quantity: float
    pricing_unit: str
    commitment_discount_category: str  # Usage (RI) or Spend (Savings Plan)
    commitment_discount_id: str
    commitment_discount_name: str
    tags: dict


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def get_costs(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Retrieve cost data for the specified date range"""
        pass
    
    @abstractmethod
    def get_prices(self) -> pd.DataFrame:
        """Retrieve price sheet data"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the data source"""
        pass


class ADXDataSource(DataSource):
    """Azure Data Explorer data source (for FinOps Hub)"""
    
    def __init__(self, cluster_uri: str, database: str, costs_table: str = "Costs", prices_table: str = "Prices"):
        self.cluster_uri = cluster_uri
        self.database = database
        self.costs_table = costs_table
        self.prices_table = prices_table
        self._client = None
    
    def _get_client(self):
        """Get or create the Kusto client"""
        if self._client is None:
            from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
            from azure.identity import DefaultAzureCredential
            
            # Use DefaultAzureCredential for authentication
            credential = DefaultAzureCredential()
            kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
                self.cluster_uri, credential
            )
            self._client = KustoClient(kcsb)
        return self._client
    
    def test_connection(self) -> bool:
        """Test connection to ADX"""
        try:
            client = self._get_client()
            result = client.execute(self.database, ".show database schema")
            return True
        except Exception as e:
            print(f"ADX connection failed: {e}")
            return False
    
    def get_costs(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Query costs from ADX"""
        client = self._get_client()
        
        query = f"""
        {self.costs_table}
        | where ChargePeriodStart >= datetime({start_date.strftime('%Y-%m-%d')})
        | where ChargePeriodEnd <= datetime({end_date.strftime('%Y-%m-%d')})
        | project 
            ChargePeriodStart,
            ChargePeriodEnd,
            BillingAccountId,
            BillingAccountName,
            SubAccountId,
            SubAccountName,
            ResourceId,
            ResourceName,
            ResourceType,
            ServiceName,
            ServiceCategory,
            Region,
            PricingCategory,
            ChargeCategory,
            BilledCost,
            EffectiveCost,
            ListCost,
            ListUnitPrice,
            ContractedUnitPrice,
            PricingQuantity,
            PricingUnit,
            CommitmentDiscountCategory,
            CommitmentDiscountId,
            CommitmentDiscountName,
            x_SkuDetails,
            Tags
        """
        
        response = client.execute(self.database, query)
        
        # Convert to DataFrame
        df = pd.DataFrame(response.primary_results[0])
        return df
    
    def get_prices(self) -> pd.DataFrame:
        """Query prices from ADX"""
        client = self._get_client()
        
        query = f"""
        {self.prices_table}
        | project
            x_SkuMeterId,
            x_SkuMeterName,
            x_SkuProductName,
            x_SkuServiceFamily,
            x_SkuPriceType,
            x_SkuTerm,
            ListUnitPrice,
            ContractedUnitPrice,
            x_EffectivePeriodStart,
            x_EffectivePeriodEnd
        """
        
        response = client.execute(self.database, query)
        df = pd.DataFrame(response.primary_results[0])
        return df
    
    def get_savings_summary(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get pre-aggregated savings summary from ADX"""
        client = self._get_client()
        
        # KQL query for comprehensive savings analysis
        query = f"""
        let StartDate = datetime({start_date.strftime('%Y-%m-%d')});
        let EndDate = datetime({end_date.strftime('%Y-%m-%d')});
        //
        {self.costs_table}
        | where ChargePeriodStart >= StartDate and ChargePeriodEnd <= EndDate
        | extend 
            SavingsCategory = case(
                PricingCategory == "Committed" and CommitmentDiscountCategory == "Usage", "Reserved Instance",
                PricingCategory == "Committed" and CommitmentDiscountCategory == "Spend", "Savings Plan",
                x_SkuDetails contains "AHB" or x_SkuDetails contains "HybridBenefit", "Azure Hybrid Benefit",
                SubAccountName contains "DevTest" or SubAccountName contains "Dev/Test", "Dev/Test Pricing",
                "Standard"
            )
        | summarize 
            BilledCost = sum(BilledCost),
            EffectiveCost = sum(EffectiveCost),
            ListCost = sum(ListCost)
            by SavingsCategory, ServiceCategory, bin(ChargePeriodStart, 1d)
        | extend 
            NegotiatedSavings = ListCost - BilledCost,
            CommitmentSavings = BilledCost - EffectiveCost
        """
        
        response = client.execute(self.database, query)
        df = pd.DataFrame(response.primary_results[0])
        return df


class StorageDataSource(DataSource):
    """Azure Storage data source (for Cost Management exports)"""
    
    def __init__(self, account_name: str, container_name: str, export_path: str):
        self.account_name = account_name
        self.container_name = container_name
        self.export_path = export_path
        self._container_client = None
    
    def _get_container_client(self):
        """Get or create the blob container client"""
        if self._container_client is None:
            from azure.storage.blob import ContainerClient
            from azure.identity import DefaultAzureCredential
            
            credential = DefaultAzureCredential()
            account_url = f"https://{self.account_name}.blob.core.windows.net"
            self._container_client = ContainerClient(
                account_url, 
                self.container_name, 
                credential=credential
            )
        return self._container_client
    
    def test_connection(self) -> bool:
        """Test connection to storage"""
        try:
            client = self._get_container_client()
            # Try to list blobs to verify access
            list(client.list_blobs(name_starts_with=self.export_path, results_per_page=1))
            return True
        except Exception as e:
            print(f"Storage connection failed: {e}")
            return False
    
    def get_costs(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Read cost exports from storage"""
        import io
        
        client = self._get_container_client()
        
        # List all export files in the path
        blobs = client.list_blobs(name_starts_with=self.export_path)
        
        dfs = []
        for blob in blobs:
            # Check if file is in date range based on filename pattern
            if blob.name.endswith('.parquet'):
                blob_client = client.get_blob_client(blob.name)
                data = blob_client.download_blob().readall()
                df = pd.read_parquet(io.BytesIO(data))
                dfs.append(df)
            elif blob.name.endswith('.csv'):
                blob_client = client.get_blob_client(blob.name)
                data = blob_client.download_blob().readall()
                df = pd.read_csv(io.BytesIO(data))
                dfs.append(df)
        
        if not dfs:
            return pd.DataFrame()
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter by date range
        if 'ChargePeriodStart' in combined_df.columns:
            combined_df['ChargePeriodStart'] = pd.to_datetime(combined_df['ChargePeriodStart'])
            combined_df = combined_df[
                (combined_df['ChargePeriodStart'] >= start_date) & 
                (combined_df['ChargePeriodStart'] <= end_date)
            ]
        
        return combined_df
    
    def get_prices(self) -> pd.DataFrame:
        """Read price sheet from storage"""
        # Price sheets are typically in a separate export
        # Implementation depends on your export configuration
        return pd.DataFrame()


class RetailPricesAPI:
    """Azure Retail Prices API client for comparison against public prices"""
    
    API_URL = "https://prices.azure.com/api/retail/prices"
    
    def __init__(self, cache_enabled: bool = True, cache_ttl_hours: int = 24):
        self.cache_enabled = cache_enabled
        self.cache_ttl_hours = cache_ttl_hours
        self._cache = {}
        self._cache_time = {}
    
    def get_retail_price(self, sku_id: str, region: str = "eastus") -> Optional[float]:
        """Get retail price for a specific SKU"""
        import requests
        
        cache_key = f"{sku_id}_{region}"
        
        # Check cache
        if self.cache_enabled and cache_key in self._cache:
            cache_age = datetime.now() - self._cache_time[cache_key]
            if cache_age < timedelta(hours=self.cache_ttl_hours):
                return self._cache[cache_key]
        
        # Query API
        filter_str = f"skuId eq '{sku_id}' and armRegionName eq '{region}'"
        params = {"$filter": filter_str}
        
        try:
            response = requests.get(self.API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Items"):
                price = data["Items"][0].get("retailPrice", 0)
                
                # Cache result
                if self.cache_enabled:
                    self._cache[cache_key] = price
                    self._cache_time[cache_key] = datetime.now()
                
                return price
        except Exception as e:
            print(f"Error fetching retail price: {e}")
        
        return None
    
    def get_prices_bulk(self, service_family: str = None, region: str = "eastus") -> pd.DataFrame:
        """Get retail prices for a service family"""
        import requests
        
        items = []
        next_page = self.API_URL
        
        params = {"armRegionName": region}
        if service_family:
            params["$filter"] = f"serviceFamily eq '{service_family}'"
        
        while next_page:
            try:
                response = requests.get(next_page, params=params if next_page == self.API_URL else None)
                response.raise_for_status()
                data = response.json()
                items.extend(data.get("Items", []))
                next_page = data.get("NextPageLink")
                
                # Limit to avoid too many API calls
                if len(items) > 10000:
                    break
            except Exception as e:
                print(f"Error fetching retail prices: {e}")
                break
        
        return pd.DataFrame(items)


def create_data_source(config: dict) -> DataSource:
    """Factory function to create the appropriate data source"""
    source_type = config.get("data_source", {}).get("type", "adx")
    
    if source_type == "adx":
        adx_config = config["data_source"]["adx"]
        return ADXDataSource(
            cluster_uri=adx_config["cluster_uri"],
            database=adx_config["database"],
            costs_table=adx_config.get("costs_table", "Costs"),
            prices_table=adx_config.get("prices_table", "Prices")
        )
    elif source_type == "storage":
        storage_config = config["data_source"]["storage"]
        return StorageDataSource(
            account_name=storage_config["account_name"],
            container_name=storage_config["container_name"],
            export_path=storage_config["export_path"]
        )
    else:
        raise ValueError(f"Unknown data source type: {source_type}")
