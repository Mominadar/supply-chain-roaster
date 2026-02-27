"""
Kit Composition Data Cleaner

This script converts the Kit_Composition_and_relation.csv file into a cleaned format
with line types according to the following rules:

1. Master Kits:
   - If appears only once (non_virtual master): line_type = "long line"
   - If appears multiple times: line_type = "" (empty/theoretical)

2. Sub Kits:
   - All sub kits get line_type = "long line"

3. Prepacks:
   - All prepacks get line_type = "miniload"

The output includes columns: kit_name, kit_description, kit_type, line_type
"""

import pandas as pd
import os
from typing import Tuple


class KitCompositionCleaner:
    """
    Cleans and processes kit composition data with line type assignments.
    
    This class maintains state across processing steps, allowing for:
    - Single data load
    - Step-by-step processing
    - Intermediate result storage
    """
    
    def __init__(self, input_file: str, output_file: str = None):
        """
        Initialize the cleaner with file paths.
        
        Args:
            input_file: Path to input CSV file (Kit_Composition_and_relation.csv)
            output_file: Path to output CSV file (optional, can be set later)
        """
        self.input_file = input_file
        self.output_file = output_file
        
        # State variables for processing pipeline
        self.df = None
        self.master_df = None
        self.subkit_df = None
        self.prepack_df = None
        self.final_df = None
        
    def load_data(self) -> pd.DataFrame:
        """Load the Kit Composition and relation CSV file."""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"File not found: {self.input_file}")
        
        self.df = pd.read_csv(self.input_file, encoding='cp1252')
        print(f"Loaded {len(self.df)} rows from {self.input_file}")
        return self.df
    
    def process_master_kits(self) -> pd.DataFrame:
        """
        Process Master Kits according to business rules:
        - Non virtual masters (no subkits/prepacks, only components): line_type = "long line"
        - Virtual masters (have subkits/prepacks): line_type = "" (empty - no production needed)
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print("Processing Master Kits...")
        
        # Identify masters with hierarchy (subkits or prepacks)
        masters_with_subkits = set(self.df[self.df['Sub kit'].notna()]['Master Kit'].unique())
        masters_with_prepacks = set(self.df[self.df['Prepack'].notna()]['Master Kit'].unique())
        masters_with_hierarchy = masters_with_subkits
        
        # All masters
        all_masters = set(self.df['Master Kit'].unique())
        
        # Non virtual masters are those WITHOUT subkits (only have components)
        non_virtual_masters = all_masters - masters_with_hierarchy
        
        print(f"Total unique Master Kits: {len(all_masters)}")
        print(f"Masters with subkits/prepacks: {len(masters_with_hierarchy)}")
        print(f"Non virtual masters (only components): {len(non_virtual_masters)}")
        
        # Create master kit records
        master_data = []
        
        # Get unique master kits with descriptions
        unique_masters = self.df[['Master Kit', 'Master Kit  Description']].drop_duplicates()
        
        for _, row in unique_masters.iterrows():
            master_kit = row['Master Kit']
            master_desc = row['Master Kit  Description']
            
            # Determine line_type based on virtual status
            if master_kit in non_virtual_masters:
                line_type = "long line"
            else:
                line_type = ""  # Empty for virtual (theoretical)
            
            master_data.append({
                'kit_name': master_kit,
                'kit_description': master_desc,
                'kit_type': 'master',
                'line_type': line_type
            })
        
        self.master_df = pd.DataFrame(master_data)

        
        return self.master_df
    
    def process_sub_kits(self) -> pd.DataFrame:
        """
        Process Sub Kits according to business rules:
        - All sub kits get line_type = "long line"
        - Remove duplicates
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print("Processing Sub Kits...")
        
        # Filter rows that have sub kits
        subkit_df = self.df[self.df['Sub kit'].notna()].copy()
        
        if len(subkit_df) == 0:
            print("No sub kits found")
            self.subkit_df = pd.DataFrame(columns=['kit_name', 'kit_description', 'kit_type', 'line_type'])
            return self.subkit_df
        
        # Get unique sub kits with descriptions
        unique_subkits = subkit_df[['Sub kit', 'Sub kit description']].drop_duplicates()
        
        subkit_data = []
        for _, row in unique_subkits.iterrows():
            subkit_data.append({
                'kit_name': row['Sub kit'],
                'kit_description': row['Sub kit description'],
                'kit_type': 'subkit',
                'line_type': 'long line'
            })
        
        self.subkit_df = pd.DataFrame(subkit_data)
        print(f"Created {len(self.subkit_df)} sub kit records")
        
        return self.subkit_df
    
    def process_prepacks(self) -> pd.DataFrame:
        """
        Process Prepacks according to business rules:
        - All prepacks get line_type = "miniload"
        - Remove duplicates
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print("Processing Prepacks...")
        
        # Filter rows that have prepacks
        prepack_df = self.df[self.df['Prepack'].notna()].copy()
        
        if len(prepack_df) == 0:
            print("No prepacks found")
            self.prepack_df = pd.DataFrame(columns=['kit_name', 'kit_description', 'kit_type', 'line_type'])
            return self.prepack_df
        
        # Get unique prepacks with descriptions
        unique_prepacks = prepack_df[['Prepack', 'Prepack Description']].drop_duplicates()
        
        prepack_data = []
        for _, row in unique_prepacks.iterrows():
            prepack_data.append({
                'kit_name': row['Prepack'],
                'kit_description': row['Prepack Description'],
                'kit_type': 'prepack',
                'line_type': 'miniload'
            })
        
        self.prepack_df = pd.DataFrame(prepack_data)
        print(f"Created {len(self.prepack_df)} prepack records")
        
        return self.prepack_df
    
    def concatenate_and_save(self, output_path: str = None) -> pd.DataFrame:
        """
        Concatenate all processed dataframes and save to output file.
        
        Args:
            output_path: Path to save the output file (uses self.output_file if not provided)
        """
        if self.master_df is None or self.subkit_df is None or self.prepack_df is None:
            raise ValueError("Processing not complete. Run process_master_kits(), process_sub_kits(), and process_prepacks() first.")
        
        print("Concatenating results...")
        
        # Concatenate all dataframes
        self.final_df = pd.concat([self.master_df, self.subkit_df, self.prepack_df], ignore_index=True)
        
        # Ensure empty strings instead of NaN for line_type
        self.final_df['line_type'] = self.final_df['line_type'].fillna('')
        
        # Sort by kit_type for better organization
        self.final_df = self.final_df.sort_values(['kit_type', 'kit_name']).reset_index(drop=True)
        
        print(f"Final dataset contains {len(self.final_df)} records:")
        print(f"  - Masters: {len(self.master_df)}")
        print(f"  - Subkits: {len(self.subkit_df)}")
        print(f"  - Prepacks: {len(self.prepack_df)}")
        
        # Determine output path
        save_path = output_path or self.output_file
        if save_path is None:
            raise ValueError("No output path provided. Specify output_path parameter or set self.output_file")
        
        # Save to file (keep empty strings as empty, not NaN)
        self.final_df.to_csv(save_path, index=False, na_rep='')
        print(f"Saved cleaned data to: {save_path}")
        
        return self.final_df


def main():
    """Main function to execute the kit composition cleaning process."""
    # Define file paths
    # base_dir = "/Users/halimjun/Coding_local/SD_roster_real"
    path_input = "/Users/halimjun/Coding_local/SD_roster_real/data/raw_csv"
    input_file = os.path.join(path_input, "Kit_Composition_and_relation.csv")
    path_output = "/Users/halimjun/Coding_local/SD_roster_real/data/real_data_excel/production_data/"
    output_file = os.path.join(path_output, "Kit_Composition_and_relation_cleaned_with_line_type.csv")
    
    try:
        # Initialize cleaner with class
        if not os.path.exists(output_file):
            open(output_file, 'w').close()
        cleaner = KitCompositionCleaner(input_file, output_file)
        
        # Execute pipeline step by step
        cleaner.load_data()
        cleaner.process_master_kits()
        cleaner.process_sub_kits()
        cleaner.process_prepacks()
        final_df = cleaner.concatenate_and_save()
        
        # Display summary statistics
        print("Line type distribution:")
        print(final_df['line_type'].value_counts(dropna=False))
        print("\nKit type distribution:")
        print(final_df['kit_type'].value_counts())
        
        print("\nSample of final data:")
        print(final_df.head(10))

    except Exception as e:
        print(f"❌ Error processing kit composition data: {e}")
        raise


if __name__ == "__main__":
    main()
