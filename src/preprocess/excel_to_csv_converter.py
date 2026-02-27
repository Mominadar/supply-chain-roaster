import pandas as pd
import os
from pathlib import Path

class ExcelToCsvConverter:
    """
    Convert an Excel file to CSV files.
    """
    
    def __init__(self, excel_path, output_dir=None):
        self.excel_path = excel_path
        self.output_dir = output_dir
    

    def convert_excel_to_csv(excel_path, output_dir=None):
        """
        Convert each sheet of an Excel file to a separate CSV file.
        
        Args:
            excel_path (str): Path to the Excel file
            output_dir (str): Output directory for CSV files. If None, uses same directory as Excel file
        """
        try:
            # Set up output directory
            if output_dir is None:
                output_dir = os.path.dirname(excel_path)
            
            # Create output directory if it doesn't exist
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Read Excel file
            excel_file = pd.ExcelFile(excel_path)
            converted_files = []
            
            for i, sheet_name in enumerate(excel_file.sheet_names, 1):
                # Read the sheet
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Create a safe filename for the CSV
                safe_filename = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                #for specific sheet name, save the file name and use it later
                self.sheet_name = sheet_name
                self.safe_filename = safe_filename
                safe_filename = safe_filename.replace(' ', '_')
                csv_filename = f"{safe_filename}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                
                # Save as CSV
                df.to_csv(csv_path, index=False, encoding='utf-8')
                converted_files.append(csv_path)
                
                print(f"✅ {i}. '{sheet_name}' → {csv_filename}")
                print(f"   - Saved {len(df)} rows, {len(df.columns)} columns")
            
            print(f"\n🎉 Successfully converted {len(converted_files)} sheets to CSV files!")
            return converted_files
            
        except Exception as e:
            print(f"❌ Error converting Excel to CSV: {e}")
            return None


    def convert_specific_sheet_to_csv(excel_path, sheet_name, output_dir=None):
        """
        Convert a specific sheet of an Excel file to a CSV file.
        """
        if output_dir is None:
            output_dir = os.path.dirname(excel_path)
            
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        safe_filename = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.replace(' ', '_')
        csv_filename = f"{safe_filename}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"✅ {sheet_name} → {csv_filename}")

        return csv_path

    def main():
        """Main function to analyze and convert Excel file"""
        
        # Define paths
        excel_path = "data/real_data_excel/AI Project document.xlsx"
        output_dir = "data/real_data_excel/production_data"
        
        # Check if Excel file exists
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found: {excel_path}")
            return
        
        print("=" * 60)
        print("📊 EXCEL TO CSV CONVERTER")
        print("=" * 60)
        
        # Step 1: Analyze Excel structure
        sheet_info = analyze_excel_structure(excel_path)
        
        if sheet_info is None:
            return
        
        # Step 2: Convert to CSV
        converted_files = convert_excel_to_csv(excel_path, output_dir)
        
        if converted_files:
            print("\n📂 Converted files:")
            for file_path in converted_files:
                print(f"   - {file_path}")

if __name__ == "__main__":
    main() 