
import os
import yaml
import logging
from pathlib import Path
import sys

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.excel_to_csv_converter import convert_excel_to_csv, analyze_excel_structure
from src.preprocess.kit_composition_cleaner import KitCompositionCleaner
from src.preprocess.hierarchy_parser import KitHierarchyParser
from src.preprocess.preprocess_demand import preprocess_demand_data
from src.debug.check_material_consistency import check_consistency

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataPipeline")

def load_paths_config(config_path="src/config/paths.yaml"):
    """Load paths configuration to verify outputs."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

import argparse

def run_pipeline():
    """
    Execute the data pipeline. 
    By default runs all steps unless specific flags are provided.
    """
    parser = argparse.ArgumentParser(description="SD Roster Data Pipeline Orchestrator")
    
    # Define flags
    parser.add_argument("--all", action="store_true", help="Run all steps (default if no other flags provided)")
    parser.add_argument("--excel-to-csv", action="store_true", help="Step 1: Convert Excel to Raw CSV")
    parser.add_argument("--kit", action="store_true", help="Step 2: Clean Kit Composition")
    parser.add_argument("--hierarchy", action="store_true", help="Step 3: Generate Kit Hierarchy")
    parser.add_argument("--demand", action="store_true", help="Step 4: Preprocess Demand Data")
    parser.add_argument("--consistency", action="store_true", help="Step 5: Check Material Consistency")
    parser.add_argument("--verify", action="store_true", help="Step 6: Verify Paths")
    
    args = parser.parse_args()
    
    # Determine if we run all (default behavior)
    # If no specific step flags are set, run ALL
    if not (args.excel_to_csv or args.kit or args.hierarchy or args.demand or args.consistency or args.verify):
        run_all = True
    else:
        run_all = args.all
        
    logger.info(f"🚀 Starting Data Pipeline Execution (Run All: {run_all})")
    
    # --- Configuration ---
    base_dir = Path(project_root)
    excel_source = base_dir / "data/real_data_excel/AI Project document.xlsx"
    raw_csv_dir = base_dir / "data/raw_csv"
    production_data_dir = base_dir / "data/real_data_excel/production_data"
    hierarchy_dir = base_dir / "data/hierarchy_exports"
    
    # Ensure directories exist
    raw_csv_dir.mkdir(parents=True, exist_ok=True)
    production_data_dir.mkdir(parents=True, exist_ok=True)
    hierarchy_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Excel to CSV ---
    if run_all or args.excel_to_csv:
        logger.info("--- Step 1: converting Excel to Raw CSV ---")
        if not excel_source.exists():
            logger.error(f"❌ Source Excel file not found: {excel_source}")
            return
        # Using the existing utility to convert all sheets
        convert_excel_to_csv(str(excel_source), str(raw_csv_dir))
    
    # --- Step 2: Clean Kit Composition ---
    if run_all or args.kit:
        logger.info("--- Step 2: Cleaning Kit Composition ---")
        kit_input = raw_csv_dir / "Kit_Composition_and_relation.csv"
        kit_output = production_data_dir / "Kit_Composition_and_relation_cleaned_with_line_type.csv"
        
        if kit_input.exists():
            cleaner = KitCompositionCleaner(str(kit_input), str(kit_output))
            cleaner.load_data()
            cleaner.process_master_kits()
            cleaner.process_sub_kits()
            cleaner.process_prepacks()
            cleaner.concatenate_and_save()
        else:
            logger.warning(f"⚠️ Kit composition raw file missing: {kit_input}")

    # --- Step 3: Generate Hierarchy ---
    if run_all or args.hierarchy:
        logger.info("--- Step 3: Generating Kit Hierarchy ---")
        kit_input = raw_csv_dir / "Kit_Composition_and_relation.csv" # Re-define locally just in case
        try:
            parser = KitHierarchyParser(csv_path=str(kit_input))
            hierarchy = parser.parse_hierarchy()
            
            # Save output manually to ensure it goes where we expect
            output_json = hierarchy_dir / "kit_hierarchy.json"
            import json
            with open(output_json, 'w') as f:
                json.dump(hierarchy, f, indent=4)
            logger.info(f"✅ Hierarchy saved to {output_json}")
            
        except Exception as e:
            logger.error(f"❌ Error generating hierarchy: {e}")

    # --- Step 4: Preprocess Demand ---
    if run_all or args.demand:
        logger.info("--- Step 4: Preprocessing Demand Data ---")
        # Strategy: Look for the specific 'COOIS_Planned_and_Released.csv' generated in Step 1
        demand_input = raw_csv_dir / "COOIS_Planned_and_Released.csv"
        
        # Output path - matching what is likely in paths.yaml or a standard name
        # Using a generic name for the 'active' file to avoid constant config updates
        demand_output = production_data_dir / "COOIS_Planned_and_Released_processed.csv"
        
        if demand_input.exists():
            preprocess_demand_data(str(demand_input), str(demand_output))
        else:
            logger.warning(f"⚠️ Raw demand file missing: {demand_input}")
        
    # --- Step 5: Consistency Check ---
    if run_all or args.consistency:
        logger.info("--- Step 5: Material Consistency Check ---")
        try:
            check_consistency()
            logger.info("✅ Consistency check completed")
        except Exception as e:
            logger.error(f"❌ Error during consistency check: {e}")

    # --- Step 6: Verify Paths ---
    if run_all or args.verify:
        logger.info("--- Step 6: Verifying Configuration Paths ---")
        paths_config = load_paths_config(base_dir / "src/config/paths.yaml")
        
        # Check if critical files defined in paths.yaml exist
        critical_files = [
            ('demand', paths_config['data']['csv']['demand']),
            ('kit_composition', paths_config['data']['csv']['kit_composition']),
            ('kit_hierarchy', paths_config['data']['hierarchy']['kit_hierarchy'])
        ]
        
        all_valid = True
        for name, relative_path in critical_files:
            full_path = base_dir / relative_path
            if not full_path.exists():
                logger.error(f"❌ Missing file referenced in paths.yaml [{name}]: {relative_path}")
                all_valid = False
            else:
                logger.info(f"✅ Verified {name}: {relative_path}")
                
        if all_valid:
            logger.info("🎉 Pipeline execution completed successfully!")
        else:
            logger.warning("⚠️ Pipeline completed with missing files.")


if __name__ == "__main__":
    run_pipeline()
