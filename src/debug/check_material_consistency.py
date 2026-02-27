import pandas as pd
import sys
import os
import yaml
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def read_csv_robust(path):
    """Try to read CSV with different encodings."""
    encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {path} with any of the attempted encodings: {encodings}")

def check_consistency():
    # Load paths configuration
    # Assuming this script is in src/debug/
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "src" / "config" / "paths.yaml"
    
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        paths_config = yaml.safe_load(f)

    # Construct absolute paths
    demand_path = project_root / paths_config['data']['csv']['demand']
    kit_composition_path = project_root / paths_config['data']['csv']['kit_composition']
    kits_calculation_path = project_root / paths_config['data']['csv']['kits_calculation']

    print(f"Using Demand Path: {demand_path}")
    print(f"Using Composition Path: {kit_composition_path}")
    print(f"Using Calculation Path: {kits_calculation_path}")

    print("Loading data...")
    try:
        df_demand = read_csv_robust(demand_path)
        df_composition = read_csv_robust(kit_composition_path)
        df_calculation = read_csv_robust(kits_calculation_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # Extract unique IDs
    # Demand uses "Material Number"
    # Ensure all are treated as strings and stripped of whitespace
    demand_materials = set(df_demand['Material Number'].astype(str).str.strip().unique())
    
    # Composition uses "kit_name"
    composition_kits = set(df_composition['kit_name'].astype(str).str.strip().unique())
    
    # Calculation uses "Kit"
    calculation_kits = set(df_calculation['Kit'].astype(str).str.strip().unique())

    print(f"Found {len(demand_materials)} unique materials in Demand.")
    print(f"Found {len(composition_kits)} unique kits in Composition.")
    print(f"Found {len(calculation_kits)} unique kits in Calculation.")
    print("-" * 50)

    # Results dictionary to store findings
    results = {
        'missing_in_composition': [],
        'missing_in_calculation': [],
        'comp_missing_in_calc': [],
        'calc_missing_in_comp': []
    }

    # Check 1: Demand Materials vs Kit Composition
    missing_in_composition = demand_materials - composition_kits
    if missing_in_composition:
        print(f"ERROR: {len(missing_in_composition)} materials from Demand are MISSING in Kit Composition:")
        for mat in sorted(missing_in_composition):
            print(f" - {mat}")
            results['missing_in_composition'].append(mat)
    else:
        print("SUCCESS: All demand materials are present in Kit Composition.")

    print("-" * 50)

    # Check 2: Demand Materials vs Kits Calculation
    missing_in_calculation = demand_materials - calculation_kits
    if missing_in_calculation:
        print(f"ERROR: {len(missing_in_calculation)} materials from Demand are MISSING in Kits Calculation:")
        for mat in sorted(missing_in_calculation):
            print(f" - {mat}")
            results['missing_in_calculation'].append(mat)
    else:
        print("SUCCESS: All demand materials are present in Kits Calculation.")
    
    # Check 3: Composition vs Calculation (Bidirectional)
    
    # 3a: In Composition but MISSING in Calculation
    comp_missing_in_calc = composition_kits - calculation_kits
    if comp_missing_in_calc:
        print(f"ERROR: {len(comp_missing_in_calc)} kits in Composition are MISSING in Calculation:")
        for kit in sorted(comp_missing_in_calc):
            results['comp_missing_in_calc'].append(kit)
    else:
        print("SUCCESS: All kits in Composition are present in Calculation.")
    
    # 3b: In Calculation but MISSING in Composition
    calc_missing_in_comp = calculation_kits - composition_kits
    if calc_missing_in_comp:
        print(f"ERROR: {len(calc_missing_in_comp)} kits in Calculation are MISSING in Composition:")
        for kit in sorted(calc_missing_in_comp):
            results['calc_missing_in_comp'].append(kit)
    else:
        print("SUCCESS: All kits in Calculation are present in Composition.")

    # ... (previous code) ...

    # Export results to Excel
    try:
        output_rel_path = paths_config.get('outputs', {}).get('reports', {}).get('consistency_check')
        if not output_rel_path:
            # Fallback if not configured
            output_rel_path = "data/reports/consistency_check_results.xlsx"
            
        # Add timestamp to filename
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        p = Path(output_rel_path)
        new_filename = f"{p.stem}_{timestamp}{p.suffix}"
        
        output_path = project_root / p.parent / new_filename
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Print clearer mapping for the user
        print("\n" + "="*50)
        print("DATA SOURCE MAPPING:")
        print(f" - Demand      : {demand_path.name}")
        print(f" - Composition : {kit_composition_path.name}")
        print(f" - Calculation : {kits_calculation_path.name}")
        print("="*50 + "\n")

        # Create a Pandas Excel writer using XlsxWriter as the engine
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # --- Sheet 0: README (Legend) ---
            # Create a dataframe for the legend
            readme_data = [
                {"Item": "Run Date", "Description": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"Item": "", "Description": ""},
                {"Item": "SHEET DESCRIPTIONS", "Description": ""},
                {"Item": "Missing_in_Kit_Composition", "Description": "Items missing in 'Kit Composition'. Sources: Demand (COOIS) or Kit Calculation."},
                {"Item": "Missing_in_Kit_Calculation", "Description": "Items missing in 'Kit Calculation'. Sources: Demand (COOIS) or Kit Composition."},
                {"Item": "", "Description": ""},
                {"Item": "NAMING CONVENTION", "Description": ""},
                {"Item": "kit composition", "Description": "Refers to file: " + kit_composition_path.name},
                {"Item": "kit__calculation", "Description": "Refers to file: " + kits_calculation_path.name},
                {"Item": "", "Description": ""},
                {"Item": "SOURCE FILES", "Description": ""},
                {"Item": "Demand File", "Description": demand_path.name},
                {"Item": "Composition File", "Description": kit_composition_path.name},
                {"Item": "Calculation File", "Description": kits_calculation_path.name},
            ]
            df_readme = pd.DataFrame(readme_data)
            df_readme.to_excel(writer, sheet_name='README', index=False)

            # Auto-adjust column width for README (simple approximation)
            worksheet = writer.sheets['README']
            worksheet.column_dimensions['A'].width = 35
            worksheet.column_dimensions['B'].width = 80

            # --- Data Sheets ---
            
            # Sheet 1: Missing in Kit Composition
            # Consolidate: (Demand -> Comp) AND (Calc -> Comp)
            data_missing_in_comp = []
            for item in results['missing_in_composition']:
                data_missing_in_comp.append({'ID': item, 'Missing In': 'kit composition', 'Source': 'Demand (COOIS)'})
            for item in results['calc_missing_in_comp']:
                data_missing_in_comp.append({'ID': item, 'Missing In': 'kit composition', 'Source': 'kit__calculation'})
            
            if data_missing_in_comp:
                df_miss_comp = pd.DataFrame(data_missing_in_comp)
                df_miss_comp.to_excel(writer, sheet_name='Missing_in_Kit_Composition', index=False)
            else:
                 pd.DataFrame({'Status': ['OK']}).to_excel(writer, sheet_name='Missing_in_Kit_Composition', index=False)

            # Sheet 2: Missing in Kit Calculation
            # Consolidate: (Demand -> Calc) AND (Comp -> Calc)
            data_missing_in_calc = []
            for item in results['missing_in_calculation']:
                 data_missing_in_calc.append({'ID': item, 'Missing In': 'kit__calculation', 'Source': 'Demand (COOIS)'})
            for item in results['comp_missing_in_calc']:
                 data_missing_in_calc.append({'ID': item, 'Missing In': 'kit__calculation', 'Source': 'kit composition'})

            if data_missing_in_calc:
                 df_miss_calc = pd.DataFrame(data_missing_in_calc)
                 df_miss_calc.to_excel(writer, sheet_name='Missing_in_Kit_Calculation', index=False)
            else:
                 pd.DataFrame({'Status': ['OK']}).to_excel(writer, sheet_name='Missing_in_Kit_Calculation', index=False)
        
        print("-" * 50)
        print(f"✅ Results exported to: {output_path}")

    except Exception as e:
        print(f"\n❌ Could not export results to Excel: {e}")
        print("Please check if 'openpyxl' is installed: pip install openpyxl")

if __name__ == "__main__":
    check_consistency()
