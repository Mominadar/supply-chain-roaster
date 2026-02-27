#!/usr/bin/env python3
"""
Kit Hierarchy Parser - Converts CSV hierarchy data to optimized formats

This module provides functions to:
1. Parse Kit_Composition_and_relation.csv
2. Generate JSON hierarchy structure  
3. Create production order CSV
4. Build DAG for optimization constraints
"""

import pandas as pd
import json
from typing import Dict, List, Tuple, Set
from collections import defaultdict, deque


class KitHierarchyParser:
    """
    Parses kit composition data and creates hierarchy structures
    for production order optimization.
    """
    
    def __init__(self, csv_path: str = None):
        if csv_path:
             self.csv_path = csv_path
        else:
             # Load from paths.yaml
             try:
                 _config_dir = __import__("pathlib").Path(__file__).parent.parent.parent / "src" / "config"
                 _paths_file = _config_dir / "paths.yaml"
                 # Fallback if specific config loading is needed, but let's try direct hardcoded path relative to project root for simplicity if the yaml load is complex here
                 # Or better, replicate the loading logic from extract.py
                 import yaml
                 root_dir = __import__("pathlib").Path(__file__).parent.parent.parent
                 with open(root_dir / "src/config/paths.yaml", 'r') as f:
                     paths = yaml.safe_load(f)
                 self.csv_path = str(root_dir / paths['data']['hierarchy']['kit_hierarchy_source'])
             except Exception as e:
                 print(f"Warning: Could not load path from config, using default. Error: {e}")
                 self.csv_path = "data/raw_csv/Kit_Composition_and_relation.csv"
        
        self.df = None
        self.hierarchy_json = {}
        self.production_order_csv = []
        self.dependency_graph = {'nodes': set(), 'edges': set()}
        
    def load_data(self):
        """Load and clean the CSV data"""
        try:
            self.df = pd.read_csv(self.csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            print("UTF-8 decode failed, trying latin-1...")
            self.df = pd.read_csv(self.csv_path, encoding='latin-1')
            
        print(f"Loaded {len(self.df)} rows from {self.csv_path}")
        
    def parse_hierarchy(self) -> Dict:
        """
        Parse the hierarchy from CSV into JSON structure
        Returns: Nested dictionary representing the hierarchy
        """
        if self.df is None:
            self.load_data()
            
        # Get unique relationships
        relationships = self.df[['Master Kit', 'Master Kit  Description', 
                                'Sub kit', 'Sub kit description', 
                                'Prepack', 'Prepack Description']].drop_duplicates()
        
        hierarchy = defaultdict(lambda: {
            'name': '',
            'type': 'master',
            'subkits': defaultdict(lambda: {
                'name': '',
                'type': 'subkit', 
                'prepacks': [],
                'dependencies': []
            }),
            'dependencies': []
        })
        
        for _, row in relationships.iterrows():
            master_id = row['Master Kit']
            master_desc = row['Master Kit  Description']
            subkit_id = row['Sub kit'] 
            subkit_desc = row['Sub kit description']
            prepack_id = row['Prepack']
            prepack_desc = row['Prepack Description']
            
            if pd.notna(master_id):
                # Set master info
                hierarchy[master_id]['name'] = master_desc if pd.notna(master_desc) else ''
                
                if pd.notna(subkit_id):
                    # Set subkit info
                    hierarchy[master_id]['subkits'][subkit_id]['name'] = subkit_desc if pd.notna(subkit_desc) else ''
                    
                    # Add subkit to master dependencies
                    if subkit_id not in hierarchy[master_id]['dependencies']:
                        hierarchy[master_id]['dependencies'].append(subkit_id)
                    
                    if pd.notna(prepack_id):
                        # Set prepack info
                        if prepack_id not in hierarchy[master_id]['subkits'][subkit_id]['prepacks']:
                            hierarchy[master_id]['subkits'][subkit_id]['prepacks'].append(prepack_id)
                        
                        # Add prepack to subkit dependencies
                        if prepack_id not in hierarchy[master_id]['subkits'][subkit_id]['dependencies']:
                            hierarchy[master_id]['subkits'][subkit_id]['dependencies'].append(prepack_id)
                            
                elif pd.notna(prepack_id):
                    # Handle direct master-prepack relationship (no subkit)
                    # Add direct_prepacks list to hierarchy if it doesn't exist
                    if 'direct_prepacks' not in hierarchy[master_id]:
                        hierarchy[master_id]['direct_prepacks'] = []
                    
                    # Add prepack directly to master
                    if prepack_id not in hierarchy[master_id]['direct_prepacks']:
                        hierarchy[master_id]['direct_prepacks'].append(prepack_id)
                    
                    # Add prepack to master dependencies
                    if prepack_id not in hierarchy[master_id]['dependencies']:
                        hierarchy[master_id]['dependencies'].append(prepack_id)
        
        # Convert defaultdict to regular dict for JSON serialization
        self.hierarchy_json = json.loads(json.dumps(hierarchy, default=dict))
        return self.hierarchy_json



def sort_products_by_hierarchy(product_list: List[str], 
                                kit_levels: Dict[str, int], 
                                kit_dependencies: Dict[str, List[str]]) -> List[str]:
    """
    Sort products by hierarchy levels and dependencies using topological sorting.
    Returns products in optimal production order: prepacks → subkits → masters
    Dependencies within the same level are properly ordered.
    
    Args:
        product_list: List of product names to sort
        kit_levels: Dictionary mapping product names to hierarchy levels (0=prepack, 1=subkit, 2=master)
        kit_dependencies: Dictionary mapping product names to their dependencies (products that must be made first)
    
    Returns:
        List of products sorted in production order (dependencies first)
    """
    # Filter products that are in our production list and have hierarchy data
    products_with_hierarchy = [p for p in product_list if p in kit_levels]
    products_without_hierarchy = [p for p in product_list if p not in kit_levels]
    
    if products_without_hierarchy:
        print(f"[HIERARCHY] Products without hierarchy data: {products_without_hierarchy}")
    
    # Build dependency graph for products in our list
    graph = defaultdict(list)  # product -> [dependents]
    in_degree = defaultdict(int)  # product -> number of dependencies
    
    # Initialize all products
    for product in products_with_hierarchy:
        in_degree[product] = 0
    
    for product in products_with_hierarchy:
        deps = kit_dependencies.get(product, [])  # dependencies = products that has to be packed first
        for dep in deps:
            if dep in products_with_hierarchy:  # Only if dependency is in our production list
                # REVERSE THE RELATIONSHIP: 
                # kit_dependencies says: "product needs dep"
                # graph says: "dep is needed by product"
                graph[dep].append(product)  # dep -> product (reverse the relationship!)
                in_degree[product] += 1
    
    # Topological sort with hierarchy level priority
    sorted_products = []
    # queue = able to remove from both sides
    queue = deque()
    
    # Start with products that have no dependencies
    for product in products_with_hierarchy:
        if in_degree[product] == 0:
            queue.append(product)
    
    while queue:
        current = queue.popleft()
        sorted_products.append(current)
        
        # Process dependents - sort by hierarchy level first
        for dependent in sorted(graph[current], key=lambda p: (kit_levels.get(p, 999), p)):
            in_degree[dependent] -= 1  # decrement the in_degree of the dependent
            if in_degree[dependent] == 0:  # if the in_degree of the dependent is 0, add it to the queue so that it can be processed
                queue.append(dependent)
    
    # Check for cycles (shouldn't happen with proper hierarchy)
    if len(sorted_products) != len(products_with_hierarchy):
        remaining = [p for p in products_with_hierarchy if p not in sorted_products]
        print(f"[HIERARCHY] WARNING: Potential circular dependencies detected in: {remaining}")
        # Add remaining products sorted by level as fallback
        remaining_sorted = sorted(remaining, key=lambda p: (kit_levels.get(p, 999), p))
        sorted_products.extend(remaining_sorted)
    
    # Add products without hierarchy information at the end
    sorted_products.extend(sorted(products_without_hierarchy))
    
    print(f"[HIERARCHY] Dependency-aware production order: {len(sorted_products)} products")
    for i, p in enumerate(sorted_products[:10]):  # Show first 10
        level = kit_levels.get(p, "unknown")
        # Import here to avoid circular dependency
        try:
            from src.config.constants import KitLevel
            level_name = KitLevel.get_name(level)
        except:
            level_name = f"level_{level}"
        deps = kit_dependencies.get(p, [])
        deps_in_list = [d for d in deps if d in products_with_hierarchy]
        print(f"  {i+1}. {p} (level {level}={level_name}, deps: {len(deps_in_list)})")
        if deps_in_list:
            print(f"      Dependencies: {deps_in_list}")
    
    if len(sorted_products) > 10:
        print(f"  ... and {len(sorted_products) - 10} more products")
    
    return sorted_products


def main():
    """Demo the hierarchy parser"""
    parser = KitHierarchyParser()
    
    print("🔄 Parsing kit hierarchy...")
    hierarchy = parser.parse_hierarchy()

    #export to json
    with open('data/hierarchy_exports/kit_hierarchy.json', 'w') as f:
        json.dump(hierarchy, f,indent=4)
    
    print(f"📊 Found {len(hierarchy)} master kits")
    


if __name__ == "__main__":
    main()
