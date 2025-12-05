# Azure Savings Realization Report - Architecture Documentation

## Overview

The Azure Savings Realization Report Generator is a lightweight, open-source tool designed to provide customers with comprehensive visibility into their Azure cost savings. It consolidates fragmented cost data from Azure Cost Management into a single, unified report that demonstrates the tangible value of:

- Enterprise Agreement (EA) / Microsoft Customer Agreement (MCA) negotiated pricing
- Azure Hybrid Benefit (AHB) for Windows and SQL Server
- Dev/Test subscription pricing
- Reserved Instances (RI)
- Savings Plans

## Problem Statement

```mermaid
flowchart LR
    subgraph "Current State - Fragmented Data"
        A[Cost Analysis] 
        B[Price Sheets]
        C[Advisor Workbooks]
        D[Reservation Details]
        E[Savings Plan Reports]
    end
    
    subgraph "Customer Need"
        F[Single Unified<br/>Savings Report]
    end
    
    A --> |Manual Process| F
    B --> |Manual Process| F
    C --> |Manual Process| F
    D --> |Manual Process| F
    E --> |Manual Process| F
    
    style F fill:#107c10,color:#fff
```

**The Gap**: Azure portal provides pieces of savings information across multiple views, but there is no single report that stitches together the complete savings story for customers.

## Solution Architecture

```mermaid
flowchart TB
    subgraph "Data Sources"
        ADX[(Azure Data Explorer<br/>FinOps Hub)]
        STORAGE[(Azure Storage<br/>Cost Exports)]
        RETAIL[Azure Retail<br/>Prices API]
    end
    
    subgraph "Data Layer"
        DS[Data Source<br/>Abstraction]
        ADX --> DS
        STORAGE --> DS
        RETAIL --> DS
    end
    
    subgraph "Processing Layer"
        CALC[Savings Calculator]
        DS --> CALC
        
        subgraph "Savings Categories"
            NEG[Negotiated<br/>Discount]
            RI[Reserved<br/>Instances]
            SP[Savings<br/>Plans]
            AHB[Azure Hybrid<br/>Benefit]
            DT[Dev/Test<br/>Pricing]
        end
        
        CALC --> NEG
        CALC --> RI
        CALC --> SP
        CALC --> AHB
        CALC --> DT
    end
    
    subgraph "Output Layer"
        GEN[Report Generator]
        NEG --> GEN
        RI --> GEN
        SP --> GEN
        AHB --> GEN
        DT --> GEN
        
        HTML[HTML Report]
        EXCEL[Excel Report]
        GEN --> HTML
        GEN --> EXCEL
    end
    
    subgraph "Delivery"
        CUSTOMER[Customer<br/>Presentation]
        HTML --> CUSTOMER
        EXCEL --> CUSTOMER
    end
    
    style ADX fill:#0078d4,color:#fff
    style CUSTOMER fill:#107c10,color:#fff
```

## Component Details

### 1. Data Sources

```mermaid
classDiagram
    class DataSource {
        <<abstract>>
        +get_costs(start_date, end_date) DataFrame
        +get_prices() DataFrame
        +test_connection() bool
    }
    
    class ADXDataSource {
        -cluster_uri: str
        -database: str
        -costs_table: str
        -prices_table: str
        +get_costs() DataFrame
        +get_prices() DataFrame
        +get_savings_summary() DataFrame
        +test_connection() bool
    }
    
    class StorageDataSource {
        -account_name: str
        -container_name: str
        -export_path: str
        +get_costs() DataFrame
        +get_prices() DataFrame
        +test_connection() bool
    }
    
    class RetailPricesAPI {
        -cache_enabled: bool
        -cache_ttl_hours: int
        +get_retail_price(sku_id, region) float
        +get_prices_bulk(service_family) DataFrame
    }
    
    DataSource <|-- ADXDataSource
    DataSource <|-- StorageDataSource
    ADXDataSource ..> RetailPricesAPI : uses
```

### 2. Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Tool
    participant DS as Data Source
    participant ADX as Azure Data Explorer
    participant Calc as Savings Calculator
    participant Gen as Report Generator
    
    User->>CLI: generate --customer "Contoso" --months 3
    CLI->>CLI: Load configuration
    CLI->>DS: Create data source
    DS->>ADX: Test connection
    ADX-->>DS: Connection OK
    
    CLI->>DS: get_costs(start_date, end_date)
    DS->>ADX: Execute KQL query
    ADX-->>DS: Cost records
    DS-->>CLI: DataFrame
    
    CLI->>Calc: Create calculator with costs
    Calc->>Calc: Categorize savings
    Calc->>Calc: Calculate negotiated savings
    Calc->>Calc: Calculate RI savings
    Calc->>Calc: Calculate SP savings
    Calc->>Calc: Calculate AHB savings
    Calc->>Calc: Calculate Dev/Test savings
    
    CLI->>Calc: generate_report()
    Calc-->>CLI: SavingsReport object
    
    CLI->>Gen: generate_html_report(report)
    Gen-->>CLI: HTML file path
    
    CLI->>Gen: generate_excel_report(report)
    Gen-->>CLI: Excel file path
    
    CLI-->>User: Reports generated successfully
```

### 3. Savings Calculation Logic

```mermaid
flowchart TD
    subgraph "Input Data - FOCUS Schema"
        LC[ListCost<br/>Retail Price × Quantity]
        BC[BilledCost<br/>Negotiated Price × Quantity]
        EC[EffectiveCost<br/>After Commitment Discounts]
        PC[PricingCategory<br/>Standard / Committed]
        CDC[CommitmentDiscountCategory<br/>Usage / Spend]
    end
    
    subgraph "Savings Calculations"
        NS[Negotiated Savings<br/>= ListCost - BilledCost]
        CS[Commitment Savings<br/>= BilledCost - EffectiveCost]
        TS[Total Savings<br/>= ListCost - EffectiveCost]
    end
    
    LC --> NS
    BC --> NS
    BC --> CS
    EC --> CS
    LC --> TS
    EC --> TS
    
    subgraph "Categorization"
        CAT{Categorize by<br/>PricingCategory &<br/>CommitmentDiscountCategory}
        
        RI_CAT[Reserved Instance<br/>Committed + Usage]
        SP_CAT[Savings Plan<br/>Committed + Spend]
        AHB_CAT[Azure Hybrid Benefit<br/>SKU contains AHB]
        DT_CAT[Dev/Test<br/>Subscription name match]
        NEG_CAT[Negotiated Rate<br/>Standard pricing]
    end
    
    PC --> CAT
    CDC --> CAT
    CAT --> RI_CAT
    CAT --> SP_CAT
    CAT --> AHB_CAT
    CAT --> DT_CAT
    CAT --> NEG_CAT
    
    style TS fill:#107c10,color:#fff
```

### 4. Report Structure

```mermaid
flowchart TB
    subgraph "HTML Report"
        HEADER[Header<br/>Customer Name & Period]
        
        subgraph "Executive Summary"
            KPI1[Retail Cost]
            KPI2[Effective Cost]
            KPI3[Total Savings]
        end
        
        subgraph "Savings Breakdown"
            PIE[Pie Chart by Category]
            CARDS[Category Cards<br/>with Values]
        end
        
        subgraph "Details"
            SVC[By Service Table]
            SUB[By Subscription Table]
            TREND[Monthly Trend Chart]
            TOP[Top Resources Table]
        end
        
        FOOTER[Generated Timestamp]
    end
    
    HEADER --> KPI1
    HEADER --> KPI2
    HEADER --> KPI3
    KPI1 --> PIE
    KPI2 --> PIE
    KPI3 --> PIE
    PIE --> CARDS
    CARDS --> SVC
    SVC --> SUB
    SUB --> TREND
    TREND --> TOP
    TOP --> FOOTER
```

## FOCUS Data Schema

The tool relies on the **FinOps Open Cost and Usage Specification (FOCUS)** schema for standardized cost data:

```mermaid
erDiagram
    COSTS {
        datetime ChargePeriodStart
        datetime ChargePeriodEnd
        string BillingAccountId
        string BillingAccountName
        string SubAccountId
        string SubAccountName
        string ResourceId
        string ResourceName
        string ResourceType
        string ServiceName
        string ServiceCategory
        string Region
        string PricingCategory
        string ChargeCategory
        decimal BilledCost
        decimal EffectiveCost
        decimal ListCost
        decimal ListUnitPrice
        decimal ContractedUnitPrice
        decimal PricingQuantity
        string PricingUnit
        string CommitmentDiscountCategory
        string CommitmentDiscountId
        string CommitmentDiscountName
        string Tags
    }
    
    PRICES {
        string x_SkuMeterId
        string x_SkuMeterName
        string x_SkuProductName
        string x_SkuServiceFamily
        string x_SkuPriceType
        string x_SkuTerm
        decimal ListUnitPrice
        decimal ContractedUnitPrice
        datetime x_EffectivePeriodStart
        datetime x_EffectivePeriodEnd
    }
    
    COSTS ||--o{ PRICES : "joins on SkuMeterId"
```

## Key Cost Fields Explained

| Field | Description | Used For |
|-------|-------------|----------|
| `ListCost` | Retail/public price × quantity | Calculating what customer would pay without any discounts |
| `BilledCost` | Negotiated EA/MCA price × quantity | Actual invoice amount before commitment discounts |
| `EffectiveCost` | Cost after RI/SP benefits applied | True cost after all discounts |
| `PricingCategory` | "Standard" or "Committed" | Identifying commitment discount usage |
| `CommitmentDiscountCategory` | "Usage" (RI) or "Spend" (SP) | Distinguishing RI vs Savings Plan |
| `ListUnitPrice` | Per-unit retail price | Price comparison analysis |
| `ContractedUnitPrice` | Per-unit negotiated price | Negotiated discount calculation |

## Deployment Options

```mermaid
flowchart LR
    subgraph "Option 1: Local CLI"
        LOCAL[Developer Machine]
        LOCAL --> |pip install| RUN1[Run locally]
    end
    
    subgraph "Option 2: Azure Automation"
        AA[Azure Automation<br/>Runbook]
        AA --> |Schedule| RUN2[Weekly reports]
        RUN2 --> BLOB[Store in Blob]
    end
    
    subgraph "Option 3: Azure Functions"
        AF[Azure Function<br/>Timer Trigger]
        AF --> |Monthly| RUN3[Generate reports]
        RUN3 --> EMAIL[Email to customer]
    end
    
    subgraph "Option 4: Container"
        ACI[Azure Container<br/>Instance]
        ACI --> |On-demand| RUN4[Generate reports]
    end
```

## Security Considerations

```mermaid
flowchart TB
    subgraph "Authentication"
        CLI_AUTH[Azure CLI<br/>az login]
        MI[Managed Identity]
        SP[Service Principal]
    end
    
    subgraph "Authorization"
        RBAC[Azure RBAC]
        ADX_PERM[ADX Database<br/>Viewer Role]
        STORAGE_PERM[Storage Blob<br/>Data Reader]
    end
    
    CLI_AUTH --> RBAC
    MI --> RBAC
    SP --> RBAC
    
    RBAC --> ADX_PERM
    RBAC --> STORAGE_PERM
    
    subgraph "Data Protection"
        TRANSIT[TLS 1.2+<br/>In Transit]
        REST[Encrypted<br/>At Rest]
        LOCAL[Reports stored<br/>locally only]
    end
    
    ADX_PERM --> TRANSIT
    STORAGE_PERM --> TRANSIT
```

## Integration with FinOps Hub

```mermaid
flowchart TB
    subgraph "FinOps Hub Architecture"
        EXPORTS[Cost Management<br/>Exports]
        ADF[Azure Data Factory<br/>Pipeline]
        STORAGE[(Azure Storage<br/>Data Lake)]
        ADX[(Azure Data Explorer)]
        
        EXPORTS --> ADF
        ADF --> STORAGE
        ADF --> ADX
    end
    
    subgraph "Savings Report Tool"
        TOOL[This Tool]
    end
    
    ADX --> |KQL Queries| TOOL
    STORAGE --> |Parquet Files| TOOL
    
    subgraph "Output"
        HTML[HTML Report]
        EXCEL[Excel Report]
        DASHBOARD[ADX Dashboard]
    end
    
    TOOL --> HTML
    TOOL --> EXCEL
    TOOL --> DASHBOARD
    
    style TOOL fill:#0078d4,color:#fff
```

## Error Handling

```mermaid
flowchart TD
    START[Start Report Generation]
    
    START --> CONFIG{Config<br/>Valid?}
    CONFIG -->|No| ERR1[Error: Config file not found<br/>Copy config.example.yaml]
    CONFIG -->|Yes| CONN{Connection<br/>OK?}
    
    CONN -->|No| ERR2[Error: Cannot connect to ADX<br/>Check cluster URI and permissions]
    CONN -->|Yes| DATA{Data<br/>Found?}
    
    DATA -->|No| ERR3[Warning: No cost data<br/>Check date range and scope]
    DATA -->|Yes| CALC[Calculate Savings]
    
    CALC --> VALID{Valid<br/>Calculations?}
    VALID -->|No| ERR4[Warning: Missing ListCost<br/>Some savings may be estimated]
    VALID -->|Yes| GEN[Generate Reports]
    
    GEN --> SUCCESS[Success: Reports Generated]
    
    style SUCCESS fill:#107c10,color:#fff
    style ERR1 fill:#d13438,color:#fff
    style ERR2 fill:#d13438,color:#fff
    style ERR3 fill:#ff8c00,color:#fff
    style ERR4 fill:#ff8c00,color:#fff
```

## Future Enhancements

```mermaid
timeline
    title Roadmap
    
    section Phase 1 - Current
        Core Features : ADX Integration
                     : HTML/Excel Reports
                     : 5 Savings Categories
    
    section Phase 2 - Near Term
        Enhancements : PDF Export
                    : Spot VM Savings
                    : Azure Advisor Integration
                    : Email Delivery
    
    section Phase 3 - Future
        Advanced : Web UI Dashboard
                : Multi-tenant Support
                : Forecasting
                : What-If Analysis
```

## Summary

This tool provides a **simple, focused solution** to a real customer pain point: demonstrating the value of their Azure investments. Unlike the full FinOps Toolkit which has many dependencies and complexity, this tool:

- **Does one thing well**: Generates savings realization reports
- **Minimal dependencies**: ~8 Python packages
- **Works with existing infrastructure**: Uses your FinOps Hub ADX database
- **Customer-ready output**: Professional HTML reports with charts
- **Open source**: Extend and customize as needed
