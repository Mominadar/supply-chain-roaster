# 🏗️ Supply Roster Optimization Tool - Architecture Diagram

## 📋 System Overview

This document provides a comprehensive architectural overview of the Supply Roster Optimization Tool, including all system components, data flows, and interconnections.

---

## 🎯 High-Level Architecture

```mermaid
graph TB
    subgraph "🚀 Entry Points"
        MAIN[main.py<br/>Main Entry Point]
        APP[ui/app.py<br/>Streamlit App]
    end

    subgraph "🎨 UI Layer - Streamlit Pages"
        CONFIG[config_page.py<br/>Settings & Configuration]
        RESULTS[optimization_results.py<br/>Results Visualization]
        VALIDATION[demand_validation_viz.py<br/>Data Validation]
    end

    subgraph "🧮 Core Logic"
        OPTIMIZER[optimizer_real.py<br/>OR-Tools Optimization<br/>CBC Solver]
        FILTER[demand_filtering.py<br/>Demand Filtering Logic]
    end

    subgraph "⚙️ Configuration"
        OPT_CONFIG[optimization_config.py<br/>Dynamic Configuration<br/>Parameters & Settings]
        CONSTANTS[constants.py<br/>Enums & Constants<br/>ShiftType, LineType, KitLevel]
        PATHS[paths.yaml<br/>File Path Configuration]
    end

    subgraph "🔄 Data Preprocessing"
        CONVERTER[excel_to_csv_converter.py<br/>Excel → CSV]
        EXTRACT[extract.py<br/>Data Reading Functions]
        TRANSFORM[transform.py<br/>Data Transformation]
        HIERARCHY[hierarchy_parser.py<br/>Kit Hierarchy Parser]
        CLEANER[kit_composition_cleaner.py<br/>Data Cleaning]
        PREPROCESS[data_preprocess.py<br/>Main Preprocessing]
    end

    subgraph "📊 Data Sources"
        EXCEL[(Excel Files<br/>AI Project document.xlsx)]
        CSV[(CSV Files<br/>30+ Data Files)]
        HIERARCHY_JSON[(kit_hierarchy.json<br/>Kit Dependencies)]
    end

    subgraph "📈 Visualization"
        PLOTLY[Plotly Charts<br/>Interactive Visualizations]
        HIERARCHY_DASH[hierarchy_dashboard.py<br/>Hierarchy Visualization]
        KIT_REL[kit_relationships.py<br/>Kit Relationships]
    end

    %% Entry Points Flow
    MAIN --> APP
    APP --> CONFIG
    APP --> RESULTS
    APP --> VALIDATION

    %% UI to Core Logic
    CONFIG -->|User Settings| OPT_CONFIG
    CONFIG -->|Run Optimization| OPTIMIZER
    RESULTS -->|Display Results| PLOTLY
    VALIDATION -->|Validate Data| FILTER

    %% Configuration Flow
    OPT_CONFIG --> CONSTANTS
    OPT_CONFIG --> PATHS
    OPT_CONFIG --> EXTRACT
    OPTIMIZER --> OPT_CONFIG

    %% Preprocessing Flow
    EXCEL -->|Convert| CONVERTER
    CONVERTER --> CSV
    CSV --> EXTRACT
    EXTRACT --> TRANSFORM
    EXTRACT --> HIERARCHY
    TRANSFORM --> PREPROCESS
    HIERARCHY -->|Parse| HIERARCHY_JSON
    HIERARCHY_JSON --> OPT_CONFIG
    CLEANER --> CSV

    %% Data to Optimization
    CSV --> EXTRACT
    EXTRACT -->|Read Data| OPT_CONFIG
    HIERARCHY_JSON -->|Dependencies| OPT_CONFIG
    OPT_CONFIG -->|Parameters| OPTIMIZER

    %% Optimization to Results
    OPTIMIZER -->|Results| RESULTS
    FILTER -->|Filtered Data| VALIDATION

    %% Visualization
    RESULTS --> PLOTLY
    RESULTS --> HIERARCHY_DASH
    RESULTS --> KIT_REL

    %% Styling
    classDef entryPoint fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef ui fill:#2196F3,stroke:#1565C0,color:#fff
    classDef core fill:#FF9800,stroke:#E65100,color:#fff
    classDef config fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef preprocess fill:#00BCD4,stroke:#006064,color:#fff
    classDef data fill:#607D8B,stroke:#37474F,color:#fff
    classDef viz fill:#E91E63,stroke:#880E4F,color:#fff

    class MAIN,APP entryPoint
    class CONFIG,RESULTS,VALIDATION ui
    class OPTIMIZER,FILTER core
    class OPT_CONFIG,CONSTANTS,PATHS config
    class CONVERTER,EXTRACT,TRANSFORM,HIERARCHY,CLEANER,PREPROCESS preprocess
    class EXCEL,CSV,HIERARCHY_JSON data
    class PLOTLY,HIERARCHY_DASH,KIT_REL viz
```

---

## 🔄 Data Flow Details

```mermaid
flowchart LR
    subgraph "1️⃣ Data Ingestion"
        A1[Excel Files] -->|excel_to_csv_converter.py| A2[CSV Files]
        A2 -->|hierarchy_parser.py| A3[kit_hierarchy.json]
    end

    subgraph "2️⃣ Data Processing"
        B1[extract.py<br/>Read Functions]
        B2[transform.py<br/>Transform Logic]
        B3[data_preprocess.py<br/>Main Processing]
        
        A2 --> B1
        B1 --> B2
        B2 --> B3
        A3 --> B1
    end

    subgraph "3️⃣ Configuration"
        C1[optimization_config.py]
        C2[Dynamic Parameters:<br/>- Products<br/>- Demand<br/>- Employees<br/>- Costs<br/>- Hierarchy]
        
        B3 --> C1
        C1 --> C2
    end

    subgraph "4️⃣ Optimization"
        D1[optimizer_real.py]
        D2[OR-Tools CBC Solver]
        D3[Variables:<br/>- Assignment<br/>- Hours<br/>- Units<br/>- Employee Count]
        D4[Constraints:<br/>- Demand<br/>- Capacity<br/>- Dependencies<br/>- Staffing]
        
        C2 --> D1
        D1 --> D2
        D2 --> D3
        D3 --> D4
    end

    subgraph "5️⃣ Results"
        E1[Optimization Results:<br/>- Schedule<br/>- Production<br/>- Costs<br/>- Headcount]
        E2[Visualization:<br/>- Charts<br/>- Tables<br/>- Analysis]
        
        D4 --> E1
        E1 --> E2
    end

    style A1 fill:#607D8B,color:#fff
    style A2 fill:#607D8B,color:#fff
    style A3 fill:#607D8B,color:#fff
    style B1 fill:#00BCD4,color:#fff
    style B2 fill:#00BCD4,color:#fff
    style B3 fill:#00BCD4,color:#fff
    style C1 fill:#9C27B0,color:#fff
    style C2 fill:#9C27B0,color:#fff
    style D1 fill:#FF9800,color:#fff
    style D2 fill:#FF9800,color:#fff
    style D3 fill:#FF9800,color:#fff
    style D4 fill:#FF9800,color:#fff
    style E1 fill:#2196F3,color:#fff
    style E2 fill:#E91E63,color:#fff
```

---

## 📦 Key Data Files & Their Purpose

```mermaid
mindmap
  root((Data Sources))
    Raw Excel
      AI Project document.xlsx
        30+ sheets of data
        Production orders
        Workforce info
        Kit compositions
    CSV Files
      Demand Data
        COOIS_Planned_and_Released.csv
        Active_Kit_overview.csv
        Order_management_Gui.csv
      Workforce Data
        WH_Workforce_Hourly_Pay_Scale.csv
        workforce_info.csv
        Fixed_Workstation_manning.csv
      Production Data
        Kits__Calculation.csv
        Kit_Composition_and_relation.csv
        Material_Master_WMS.csv
      Capacity Data
        Work_Centre_Capacity.csv
        work_shift_timing.csv
        Bagging_Workcenters.csv
        Long_line_Workcenters.csv
        Short_line_Workcenters.csv
    Hierarchy Data
      kit_hierarchy.json
        Master → Subkit → Prepack
        Dependencies
        Production order
```

---

## 🧮 Optimization Model Components

```mermaid
graph TD
    subgraph "📥 Input Parameters"
        I1[Products & Demand<br/>What to produce & how much]
        I2[Workforce<br/>Available employees by type]
        I3[Production Lines<br/>Long lines, Short lines]
        I4[Costs<br/>Hourly rates by shift]
        I5[Kit Hierarchy<br/>Dependencies & levels]
    end

    subgraph "🎯 Optimization Variables"
        V1[Assignment Variables<br/>Product → Line × Shift × Day]
        V2[Hours Variables<br/>Production time per assignment]
        V3[Units Variables<br/>Production quantity]
        V4[Employee Count Variables<br/>Workers needed per shift]
    end

    subgraph "⚖️ Constraints"
        C1[Demand Constraints<br/>Must meet exact demand]
        C2[Capacity Constraints<br/>Line & worker limits]
        C3[Hierarchy Constraints<br/>Dependencies first]
        C4[Staffing Constraints<br/>Min UNICEF employees]
        C5[Shift Ordering<br/>Overtime rules]
        C6[Line Compatibility<br/>Product-line matching]
    end

    subgraph "🎯 Objective Function"
        O1[Minimize Total Labor Cost<br/>Cost = Σ employees × hours × hourly_rate]
    end

    subgraph "✅ Output Results"
        R1[Production Schedule<br/>Day × Line × Shift × Product]
        R2[Employee Allocation<br/>Type × Shift × Day × Count]
        R3[Cost Breakdown<br/>Total cost & per employee type]
        R4[Production Metrics<br/>Units produced & fulfillment %]
    end

    I1 --> V1
    I2 --> V4
    I3 --> V1
    I4 --> O1
    I5 --> C3

    V1 --> C1
    V1 --> C2
    V1 --> C6
    V2 --> C2
    V2 --> C5
    V3 --> C1
    V4 --> C4

    C1 --> O1
    C2 --> O1
    C3 --> O1
    C4 --> O1
    C5 --> O1
    C6 --> O1

    O1 --> R1
    O1 --> R2
    O1 --> R3
    O1 --> R4

    classDef input fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef variable fill:#2196F3,stroke:#1565C0,color:#fff
    classDef constraint fill:#FF9800,stroke:#E65100,color:#fff
    classDef objective fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef output fill:#E91E63,stroke:#880E4F,color:#fff

    class I1,I2,I3,I4,I5 input
    class V1,V2,V3,V4 variable
    class C1,C2,C3,C4,C5,C6 constraint
    class O1 objective
    class R1,R2,R3,R4 output
```

---

## 🎨 UI Components & User Flow

```mermaid
journey
    title User Journey Through the Application
    section 1. Launch
      Run main.py: 5: User
      Streamlit starts: 5: System
      App loads: 5: System
    section 2. Configuration
      Navigate to Settings: 5: User
      Select date range: 5: User
      Configure workforce: 4: User
      Set cost rates: 4: User
      Choose shifts: 4: User
    section 3. Optimization
      Click Optimize: 5: User
      Load data: 5: System
      Run OR-Tools: 3: System
      Generate solution: 3: System
    section 4. Results
      View weekly summary: 5: User
      Explore daily breakdown: 4: User
      Check line schedules: 4: User
      Analyze costs: 4: User
    section 5. Validation
      Review demand data: 4: User
      Check input data: 4: User
      Validate results: 5: User
```

---

## 🔍 Module Dependency Graph

```mermaid
graph LR
    subgraph "UI Modules"
        UI1[app.py]
        UI2[config_page.py]
        UI3[optimization_results.py]
        UI4[demand_validation_viz.py]
    end

    subgraph "Model Modules"
        M1[optimizer_real.py]
        M2[demand_filtering.py]
    end

    subgraph "Config Modules"
        C1[optimization_config.py]
        C2[constants.py]
        C3[paths.yaml]
    end

    subgraph "Preprocess Modules"
        P1[extract.py]
        P2[transform.py]
        P3[hierarchy_parser.py]
        P4[data_preprocess.py]
        P5[excel_to_csv_converter.py]
    end

    subgraph "Visualization Modules"
        V1[hierarchy_dashboard.py]
        V2[kit_relationships.py]
    end

    UI1 --> UI2
    UI1 --> UI3
    UI1 --> UI4
    UI2 --> C1
    UI2 --> M1
    UI3 --> C1
    UI3 --> V1
    UI3 --> V2
    UI4 --> M2

    M1 --> C1
    M1 --> C2
    M1 --> P1
    M2 --> P1

    C1 --> C2
    C1 --> C3
    C1 --> P1
    C1 --> P3

    P1 --> C3
    P2 --> P1
    P3 --> P1
    P4 --> P1
    P4 --> P2

    V1 --> P3
    V2 --> P3

    classDef ui fill:#2196F3,stroke:#1565C0,color:#fff
    classDef model fill:#FF9800,stroke:#E65100,color:#fff
    classDef config fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef preprocess fill:#00BCD4,stroke:#006064,color:#fff
    classDef viz fill:#E91E63,stroke:#880E4F,color:#fff

    class UI1,UI2,UI3,UI4 ui
    class M1,M2 model
    class C1,C2,C3 config
    class P1,P2,P3,P4,P5 preprocess
    class V1,V2 viz
```

---

## 📊 Kit Hierarchy System

```mermaid
graph TD
    subgraph "Kit Hierarchy Levels"
        L0[Level 0: Prepack<br/>Base components<br/>No dependencies]
        L1[Level 1: Subkit<br/>Intermediate assembly<br/>Depends on prepacks]
        L2[Level 2: Master<br/>Final products<br/>Depends on subkits]
    end

    subgraph "Production Order"
        P1[1st: Produce Prepacks]
        P2[2nd: Assemble Subkits]
        P3[3rd: Complete Masters]
    end

    subgraph "Dependency Rules"
        D1[Dependencies must be<br/>produced before or<br/>at the same time]
        D2[Topological sorting<br/>ensures correct order]
        D3[Constraint in optimizer:<br/>dep_completion ≤ product_completion]
    end

    L0 --> P1
    L1 --> P2
    L2 --> P3
    P1 --> P2
    P2 --> P3

    P1 --> D1
    P2 --> D1
    P3 --> D1
    D1 --> D2
    D2 --> D3

    classDef level fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef order fill:#2196F3,stroke:#1565C0,color:#fff
    classDef rule fill:#FF9800,stroke:#E65100,color:#fff

    class L0,L1,L2 level
    class P1,P2,P3 order
    class D1,D2,D3 rule
```

---

## 🚀 Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant Main as main.py
    participant App as Streamlit App
    participant Config as Config Page
    participant OptConfig as optimization_config.py
    participant Extract as extract.py
    participant Optimizer as optimizer_real.py
    participant Results as Results Page

    User->>Main: python main.py
    Main->>App: Launch Streamlit
    App->>Config: Show Settings Page
    
    User->>Config: Configure parameters
    Config->>OptConfig: Update settings
    
    User->>Config: Click Optimize
    Config->>Extract: Load CSV data
    Extract-->>Config: Return data
    
    Config->>OptConfig: Get all parameters
    OptConfig-->>Config: Return config
    
    Config->>Optimizer: Optimizer().run_optimization()
    
    Optimizer->>OptConfig: Get products
    Optimizer->>OptConfig: Get demand
    Optimizer->>OptConfig: Get employees
    Optimizer->>OptConfig: Get costs
    Optimizer->>OptConfig: Get hierarchy
    
    Optimizer->>Optimizer: Build OR-Tools model
    Optimizer->>Optimizer: Add constraints
    Optimizer->>Optimizer: Set objective
    Optimizer->>Optimizer: Solve with CBC
    
    Optimizer-->>Config: Return results
    Config->>App: Store in session_state
    
    User->>App: Navigate to Results
    App->>Results: Display results
    Results->>Results: Generate charts
    Results-->>User: Show visualizations
```

---

## 🔑 Key Technologies & Libraries

```mermaid
mindmap
  root((Tech Stack))
    Python 3.10
      Core Language
    Streamlit
      Web UI Framework
      Interactive Dashboard
      Session State Management
    OR-Tools
      Optimization Engine
      CBC Solver
      Linear Programming
    Data Processing
      Pandas
        CSV/Excel handling
        Data transformation
      NumPy
        Numerical operations
    Visualization
      Plotly
        Interactive charts
        Bar charts
        Pie charts
        Timeline charts
    File Formats
      CSV
        Data storage
      JSON
        Hierarchy storage
      YAML
        Configuration
```

---

## 📝 Configuration Files

### paths.yaml
Centralized file path management:
- CSV file paths
- Excel file paths
- Hierarchy JSON paths

### optimization_config.py
Dynamic optimization parameter management:
- Product list (`get_product_list()`)
- Demand data (`get_demand_dictionary()`)
- Employee types (`get_employee_type_list()`)
- Cost information (`get_cost_list_per_emp_shift()`)
- Kit hierarchy (`KIT_LEVELS`, `KIT_DEPENDENCIES`)
- Line configuration (`get_line_list()`, `get_line_cnt_per_type()`)
- Shift configuration (`get_active_shift_list()`)

### constants.py
Constants and Enum definitions:
- `ShiftType`: Regular(1), Evening(2), Overtime(3)
- `LineType`: Long Line(6), Short Line(7)
- `KitLevel`: Prepack(0), Subkit(1), Master(2)

---

## 💡 Key Features

### 1. Dynamic Configuration
- All parameters can be dynamically configured from the UI
- State management with session state
- Real-time data loading

### 2. Hierarchy-Based Optimization
- 3-level hierarchy structure (Prepack → Subkit → Master)
- Automatic dependency constraint application
- Production order determined by topological sorting

### 3. Multi-Shift Scheduling
- Support for Regular, Evening, and Overtime shifts
- Different cost rates per shift
- Bulk/Partial payment mode selection

### 4. Comprehensive Visualization
- Weekly production summary
- Daily employee allocation
- Line-by-line schedules
- Cost analysis
- Hierarchy structure visualization

### 5. Data Validation
- Demand data verification
- Input data validation
- Feasibility checks

---

## 🎯 Optimization Objective

**Goal**: Minimize Total Labor Cost

```
Minimize: Σ (employee_type, shift, day) [ 
    hourly_rate × hours_worked × employees_count 
]
```

**Subject to Constraints**:
1. **Demand Fulfillment**: Must produce exactly the weekly demand for each product
2. **Capacity Limits**: Line and shift hour limitations
3. **Hierarchy Constraints**: Dependencies must be produced first
4. **Staffing Constraints**: Daily employee availability limits by type
5. **Line Compatibility**: Product-line type matching
6. **Shift Ordering**: Overtime only when Regular is at 90%+ capacity
7. **Minimum Staffing**: Guaranteed minimum UNICEF employees

---

## 📈 Performance Considerations

### OR-Tools CBC Solver
- **Pros**: Free open-source, commercial-use allowed, reasonable performance
- **Cons**: Can be slow on large-scale problems
- **Optimizations**: 
  - Minimize variable count
  - Efficient constraint formulation
  - Pre-filtering to eliminate unnecessary combinations

### Data Loading
- **CSV Caching**: Use Streamlit `@st.cache_data`
- **Session State**: Store optimization results
- **Lazy Loading**: Load only required data

---

## 🔧 Future Enhancement Opportunities

1. **Database Integration**: CSV → PostgreSQL/MySQL
2. **Advanced Solver**: CBC → Gurobi/CPLEX for faster solving
3. **Real-time Updates**: WebSocket for live optimization status
4. **Machine Learning**: Demand forecasting, production time prediction
5. **Multi-objective**: Consider completion time, resource utilization beyond cost
6. **Parallel Processing**: Run multiple scenarios simultaneously
7. **Export Features**: PDF reports, Excel result exports

---

## 📚 Documentation Structure

```
SD_roster_real/
├── README.md                    # Project overview and quick start
├── ARCHITECTURE_DIAGRAM.md      # This file - architecture diagrams
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
│
├── main.py                      # Main entry point
│
├── ui/                          # Streamlit UI
│   ├── app.py                   # Main app
│   └── pages/                   # Page components
│
├── src/                         # Core business logic
│   ├── config/                  # Configuration management
│   ├── models/                  # Optimization models
│   ├── preprocess/              # Data preprocessing
│   └── visualization/           # Chart generation
│
├── data/                        # Data files
│   ├── real_data_excel/         # Original Excel files
ㄱ│   │   └── production_data/       # Converted CSV files
│   └── hierarchy_exports/       # Hierarchy JSON structures
│
└── notebook/                    # Jupyter notebooks (for analysis)
```

---

## 🎓 Learning Path

Recommended order for understanding this project:

1. **Start**: `README.md` - Project overview
2. **Run**: `main.py` → `ui/app.py` - Run the application
3. **UI**: `ui/pages/config_page.py` - Understand UI structure
4. **Config**: `src/config/optimization_config.py` - Configuration system
5. **Data**: `src/preprocess/extract.py` - Data loading
6. **Core**: `src/models/optimizer_real.py` - Optimization logic
7. **Results**: `ui/pages/optimization_results.py` - Results visualization
8. **Architecture**: This file - Big picture understanding

---

## 📞 Component Interaction Summary

| Layer | Components | Purpose | Key Technologies |
|-------|-----------|---------|-----------------|
| **Entry** | main.py, app.py | Application launch | Python, Streamlit |
| **UI** | config_page, optimization_results, demand_validation_viz | User interface | Streamlit, Plotly |
| **Core** | optimizer_real, demand_filtering | Business logic | OR-Tools, NumPy |
| **Config** | optimization_config, constants, paths | Configuration | Python, YAML |
| **Preprocess** | extract, transform, hierarchy_parser | Data preparation | Pandas, JSON |
| **Data** | CSV files, JSON files | Data storage | CSV, JSON |
| **Viz** | Plotly charts, hierarchy_dashboard | Visualization | Plotly, Matplotlib |

---

## ✅ Conclusion

The Supply Roster Optimization Tool features:

- **Modular Architecture**: Clear separation of layers
- **Dynamic Configuration**: All parameters adjustable from UI
- **Powerful Optimization**: Complex constraints handled by OR-Tools
- **Intuitive Visualization**: Clear result presentation with Plotly
- **Extensible Design**: Easy to add new features

The entire system operates as a pipeline: **Data Collection → Preprocessing → Configuration → Optimization → Result Display**
