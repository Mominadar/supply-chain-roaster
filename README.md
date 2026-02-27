---
title: Supply Roster Optimization
emoji: 📊
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.28.0"
app_file: ui/app.py
pinned: false
---

# Warehouse Workforce Roster Optimizer

<div align="center">

[![README](https://img.shields.io/badge/📖_README-4A90E2?style=for-the-badge)](#warehouse-workforce-roster-optimizer)
[![Quick Start](https://img.shields.io/badge/🚀_Quick_Start-50C878?style=for-the-badge)](#-quick-start)
[![Project Structure](https://img.shields.io/badge/📁_Project_Structure-9B59B6?style=for-the-badge)](#-project-structure)
[![Development](https://img.shields.io/badge/🛠️_Development-E67E22?style=for-the-badge)](#️-development--work-in-progress)

</div>

---

Application for optimizing supply roster management using OR-Tools specifically tailored to UNICEF supply division.
The objective of this tool is to calculate the operation planning for minimized labor cost.

Detail on the pipeline and model can be found in the ![modelcard](docs/modelcard.md)


## 🚀 Quick Start

### Option 1: Docker (Recommended)


**Prerequisites:** 
- Docker Desktop ([Download here](https://www.docker.com/products/docker-desktop))

<details>
<summary>📦 How to install Docker Desktop (Click to expand)</summary>

1. **Download and Install:**
   - [macOS](https://docs.docker.com/desktop/install/mac-install/)
   - [Windows](https://docs.docker.com/desktop/install/windows-install/)
   - [Linux](https://docs.docker.com/desktop/install/linux/)

2. **Verify Installation:**
   ```bash
   docker --version
   docker compose version
   ```

3. **Start Docker Desktop:**
   - Look for the Docker whale icon in your system tray/menu bar
   - Wait until it shows "Docker Desktop is running"

</details>

<!-- <details> -->
<!-- <summary>📦 How to install Git LFS (Click to expand)</summary>

**macOS:**
```bash
brew install git-lfs
git lfs install
```

**Windows:**
```bash
# Download from https://git-lfs.github.com/
# Or using Chocolatey:
choco install git-lfs
git lfs install
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install git-lfs
git lfs install
```

**Verify:**
```bash
git lfs version
```

</details> -->


#### Clone the repository (Git LFS will download large files automatically)
```
git clone https://github.com/UNICEF-Ventures/SupplyDivision_Roster_Management
```
#### Change directory to master directory
```
cd SupplyDivision_Roster_Management
```
#### Start the application
```
docker-compose up
```
#### Access application through web browser. If does not launch automatically, copy the following URL into a browser.
```
http://localhost:8501
```
#### Tear down the container
```
docker-compose down #If you want to remove the container and volumne and leave image for faster implementation later.
or
docker-compose down -v #If you want to remove the container, volumne and image
```

<!-- <details> 
<summary> 2. Clone without LFS (if Git LFS is not available) </summary> 

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/UNICEF-Ventures/SupplyDivision_Roster_Management
cd SupplyDivision_Roster_Management
```

Download LFS files later (after installing Git LFS)
```
git lfs pull
```
</details>  -->

### Option 2: Local Python Installation (For development)

**Prerequisites:** Python 3.10 or 3.11

**Installation:**
#### 1. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate   # Windows
```

#### 2. Install dependencies
```
pip install -r requirements.txt
pip install -e .
```

**Run:**
```bash
supply-roster              # Using CLI
# OR
python main.py            # Using main entry point
# OR  
streamlit run ui/app.py   # Direct Streamlit
```

**Access:** `http://localhost:8501`




## 📁 Project Structure

```
SupplyDivision_Roster_Management/
├── main.py                          # Main entry point
├── README.md                        
├── requirements.txt                 # Python dependencies
├── setup.py                         # Package setup 
├── Dockerfile                       # Docker image 
├── docker-compose.yml               # Docker Compose 
├── .dockerignore                    # Docker build 
│
├── src/                             # Core business logic
│   ├── config/                      # Configuration 
│   │   ├── constants.py
│   │   ├── optimization_config.py
│   │   └── paths.yaml
│   ├── models/                      # Optimization models
│   │   └── optimizer_real.py
│   ├── preprocess/                  # Data preprocessing
│   │   ├── data_preprocess.py
│   │   ├── extract.py
│   │   ├── transform.py
│   │   └── ...
│   └── visualization/               # Chart generation
│       ├── hierarchy_dashboard.py
│       └── kit_relationships.py
│
├── ui/                              # Streamlit UI 
│   ├── app.py                       # Main Streamlit app
│   ├── pages/                       # Page components
│   │   ├── config_page.py           # Settings page
│   │   ├── optimization_results.py  # Results page
│   │   └── __init__.py
│   └── components/                  # Reusable UI components
│       └── __init__.py
│
├── data/                            # Data files
├── notebook/                        # Jupyter notebooks
└── venv/                            # Virtual environment 
```

### Pipeline structure and features (Work in progress)


1. **Settings Page**: Configure optimization parameters such as workforce limits, and cost rates.
2. **Demand Validation**: Validate input data and identify potential issues
3. **Optimization Results**: View detailed results with charts and analysis

## 🛠️ Development

### Architecture

![System Architecture](images/architecture.png)

### Technology Stack
- **Backend**: Python 3.10+, OR-Tools
- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, NetworkX
- **Configuration**: PyYAML
- **Deployment**: Docker, Docker Compose
- **File monitoring** : Watchdog

