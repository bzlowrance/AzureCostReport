# Azure Cost Report

A lightweight, open-source tool to generate comprehensive Azure savings reports for customers, demonstrating the value of their MACC/ACD agreements and optimization strategies.

## Quick Start

```powershell
cd azure-savings-report

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure your data source
cp config.example.yaml config.yaml
# Edit config.yaml with your ADX cluster or storage account details

# Generate report
python generate_report.py generate --customer "Contoso" --months 3
```

## Sample Reports

See what the generated reports look like before connecting your data:

| Sample | Description |
|--------|-------------|
| [HTML Report](azure-savings-report/examples/sample_report_contoso_20251204.html) | Interactive HTML report with charts |
| [Excel Report](azure-savings-report/examples/sample_report_contoso_20251204.xlsx) | Detailed Excel workbook with multiple sheets |

## Documentation

| Document | Description |
|----------|-------------|
| [README](azure-savings-report/README.md) | Project overview and quick start guide |
| [Architecture](azure-savings-report/docs/ARCHITECTURE.md) | System design, components, and data flow diagrams |
| [User Guide](azure-savings-report/docs/USER_GUIDE.md) | Step-by-step instructions for generating reports |
| [API Reference](azure-savings-report/docs/API_REFERENCE.md) | Python module and function documentation |
| [Examples](azure-savings-report/examples/README.md) | Sample report files and data |

## Project Structure

```
AzureCostReport/
├── README.md                         # This file
└── azure-savings-report/
    ├── README.md                     # Detailed project documentation
    ├── requirements.txt              # Python dependencies
    ├── config.example.yaml           # Configuration template
    ├── generate_report.py            # CLI entry point
    ├── src/                          # Source code
    │   ├── data_sources.py           # ADX & Storage connectors
    │   ├── savings_calculator.py     # Savings calculation logic
    │   ├── report_generator.py       # HTML & Excel report generation
    │   └── kql_queries.py            # Pre-built KQL queries
    ├── dashboards/
    │   └── adx_dashboard.kql         # Ready-to-use ADX dashboard queries
    ├── examples/
    │   ├── README.md                 # Sample files documentation
    │   ├── sample_report_*.html      # Example HTML report
    │   └── sample_report_*.xlsx      # Example Excel report
    └── docs/
        ├── ARCHITECTURE.md           # System architecture
        ├── USER_GUIDE.md             # User instructions
        └── API_REFERENCE.md          # API documentation
```

## What This Report Shows

| Savings Category | Description |
|-----------------|-------------|
| **Negotiated Discount** | Retail (List) Price vs EA/MCA Negotiated Price |
| **Reserved Instances** | 1-year or 3-year compute reservation savings |
| **Savings Plans** | Flexible compute commitment savings |
| **Azure Hybrid Benefit** | Windows/SQL Server license savings |
| **Dev/Test Pricing** | Dev/Test subscription discounts |

## License

MIT License - Use freely for your customers
