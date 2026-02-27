
import pandas as pd
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def preprocess_demand_data(input_path: str, output_path: str = None):
    """
    Preprocess the demand data (COOIS Planned and Released).
    
    Steps:
    1. Read CSV.
    2. Convert dates to standard format.
    3. Clean numeric columns (remove commas).
    4. Save to output path.
    """
    
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return

    logger.info(f"Reading demand data from: {input_path}")
    
    try:
        # Read CSV
        df = pd.read_csv(input_path)
        
        # Date Columns to fix
        date_cols = ['Basic start date', 'Basic finish date']
        
        for col in date_cols:
            if col in df.columns:
                # Convert to datetime (handling different formats)
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                # Format back to string YYYY-MM-DD
                df[col] = df[col].dt.strftime('%Y-%m-%d')
        
        # Calculate 'Basic end date' if needed (Logic from notebook implies it's just finish date)
        if 'Basic finish date' in df.columns:
             df['Basic end date'] = df['Basic finish date']

        # Clean "Order quantity (GMEIN)"
        qty_col = 'Order quantity (GMEIN)'
        if qty_col in df.columns:
            # Handle string conversion if it's object type
            if df[qty_col].dtype == 'object':
                df[qty_col] = df[qty_col].str.replace(',', '')
                # Handle potential empty strings or NaNs
                df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce').fillna(0).astype(int)
            else:
                 df[qty_col] = df[qty_col].fillna(0).astype(int)

        # Output logic
        if output_path is None:
            # Default to overwriting or saving in production_data if not specified
            # But let's be safe and require output_path or derive it
            output_dir = Path("data/real_data_excel/production_data")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / Path(input_path).name
            
        logger.info(f"Saving processed data to: {output_path}")
        df.to_csv(output_path, index=False)
        logger.info("Processing complete.")
        
    except Exception as e:
        logger.error(f"Error processing demand data: {e}")
        raise

def main():
    # Define default paths based on current workflow observations
    # Input: supposedly comes from raw_csv or a specific update folder
    input_file = "data/raw_csv/demand_updates/COOIS_Planned_and_Released_260115.csv" 
    
    # Output: Goes to the active production directory
    output_file = "data/real_data_excel/production_data/COOIS_Planned_and_Released_260115.csv"
    
    # Check if input exists, otherwise fallbacks or warn
    if not os.path.exists(input_file):
        logger.warning(f"Default input file {input_file} not found.")
        # Try finding the file in raw_csv directly?
        # For now, let's just use the hardcoded path from the notebook logic
    
    preprocess_demand_data(input_file, output_file)

if __name__ == "__main__":
    main()
