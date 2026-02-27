"""
Optimization Result Saver Utility

This module provides functionality to save optimization results to JSON files.
Separates the concern of result persistence from the optimization logic.
"""

import json
import os
import datetime
from src.config.constants import ShiftType, LineType


def _build_hierarchical_schedule(run_schedule):
    """
    Build hierarchical schedule structure: day → line → shift → products[]
    
    This provides an intuitive nested structure to quickly find production schedule
    for any specific day, line, and shift combination.
    
    Uses consistent key patterns for easy programmatic access:
    - day_1, day_2, day_3 (not dependent on date)
    - line_1, line_2, line_3 (globally unique line numbers)
    - shift_1, shift_2, shift_3 (not dependent on shift name)
    
    Args:
        run_schedule: List of schedule entries
        
    Returns:
        dict: Nested dictionary structure {day: {line: {shift: {products: [...]}}}}
    """
    schedule = {}
    
    # Build a global line mapping: (line_type_id, line_idx) → unique_line_number
    # This ensures consistent line numbering across all days
    line_mapping = {}
    line_counter = 1
    
    # First pass: build global line mapping
    for entry in run_schedule:
        line_tuple = (entry['line_type_id'], entry['line_idx'])
        if line_tuple not in line_mapping:
            line_mapping[line_tuple] = line_counter
            line_counter += 1
    
    # Second pass: build schedule structure
    for entry in run_schedule:
        day_key = f"day_{entry['day']}"
        # Use globally consistent line numbering
        line_tuple = (entry['line_type_id'], entry['line_idx'])
        global_line_num = line_mapping[line_tuple]
        line_key = f"line_{global_line_num}"
        shift_key = f"shift_{entry['shift']}"
        
        # Initialize day if not exists
        if day_key not in schedule:
            schedule[day_key] = {}
        
        # Initialize line if not exists
        if line_key not in schedule[day_key]:
            schedule[day_key][line_key] = {
                'line_type': LineType.get_name(entry['line_type_id']),
                'line_type_id': int(entry['line_type_id']),
                'line_idx': int(entry['line_idx'])
            }
        
        # Initialize shift if not exists
        if shift_key not in schedule[day_key][line_key]:
            schedule[day_key][line_key][shift_key] = {
                'shift_name': ShiftType.get_name(entry['shift']),
                'products': []
            }
        
        # Add product (skip if idle)
        if not entry['is_idle']:
            schedule[day_key][line_key][shift_key]['products'].append({
                'product': entry['product'],
                'run_hours': float(entry['run_hours']),
                'units': float(entry['units']),
                'employees': entry.get('employees', {})
            })
    
    return schedule


def save_optimization_result_to_json(optimizer, result):
    """
    Save optimization result to JSON file in docs/optimization_result folder
    
    This utility function handles the serialization and storage of optimization results,
    keeping the Optimizer class focused on optimization logic only.
    
    Args:
        optimizer: Optimizer instance (to access configuration data)
        result: Dictionary containing optimization results (with metadata)
        
    Returns:
        str: Path to the saved JSON file
        
    Raises:
        Exception: If JSON serialization or file writing fails
    """
    # Create timestamp for filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Prepare output directory
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        'docs', 
        'optimization_result'
    )
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract metadata from result
    metadata = result.get('metadata', {})
    
    # Prepare JSON-serializable data with clear separation of inputs and results
    json_result = {
        # ============================================================
        # METADATA: General information about the optimization run
        # ============================================================
        'metadata': {
            'optimization_timestamp': timestamp,
            'start_time': metadata.get('start_time'),
            'end_time': metadata.get('end_time'),
            'total_duration_seconds': metadata.get('duration_seconds'),
            'solver_time_seconds': metadata.get('solver_time_seconds'),
            'status': metadata.get('status', 'FEASIBLE'),
            'optimal_cost': result.get('objective'),
        },
        
        # ============================================================
        # INPUTS: Configuration, constraints, and input data
        # ============================================================
        'inputs': {
            # Time configuration
            'time_configuration': {
                'demand_start_date': str(optimizer.demand_start_date),
                'production_start_date': str(optimizer.production_start_date),
                'production_end_date': str(optimizer.production_end_date),
                'planning_days': optimizer.planning_days,
                'date_span': list(optimizer.date_span),
            },
            
            # Workforce constraints
            'workforce_constraints': {
                'employee_types': optimizer.employee_type_list,
                'active_shifts': optimizer.active_shift_list,
                'max_hours_per_shift': {str(k): v for k, v in optimizer.max_hours_shift.items()},
                'max_hour_per_person_per_day': optimizer.max_hour_per_person_per_day,
                'fixed_min_unicef_per_day': optimizer.fixed_min_unicef_per_day,
            },
            
            # Production capacity constraints
            'production_constraints': {
                'line_counts': optimizer.line_counts,
                'max_parallel_workers': {
                    str(k): v for k, v in optimizer.max_parallel_workers.items()
                },
            },
            
            # Demand (input data)
            'demand': {
                product: int(optimizer.demand_dictionary.get(product, 0))
                for product in result['weekly_production'].keys()
            },
        },
        
        # ============================================================
        # RESULTS: Optimization output
        # ============================================================
        'results': {
            # Production output
            'production': {
                'total_products_scheduled': len([p for p, u in result['weekly_production'].items() if u > 0]),
                'total_units_produced': int(sum(result['weekly_production'].values())),
                'by_product': {
                    product: {
                        'units_produced': int(units),
                        'demand': int(optimizer.demand_dictionary.get(product, 0)),
                        'fulfillment_rate': float(units / optimizer.demand_dictionary.get(product, 1) * 100) if optimizer.demand_dictionary.get(product, 0) > 0 else 0
                    }
                    for product, units in result['weekly_production'].items()
                },
            },
            
            # Schedule: hierarchical production plan (day → line → shift → products)
            'schedule': _build_hierarchical_schedule(result['run_schedule']),
            
            # Employee allocation: hierarchical structure (day → shift → employee_type)
            # Already in hierarchical format from optimizer
            'employee_allocation': result['employee_allocation'],
            
            # Cost breakdown: detailed cost analysis (calculated by optimizer)
            'cost_breakdown': result.get('cost_breakdown', {}),
            
            # Summary statistics
            'summary': {
                'total_products': len(optimizer.product_list),
                'products_with_production': len([p for p, u in result['weekly_production'].items() if u > 0]),
                'total_demand': int(sum(optimizer.demand_dictionary.values())),
                'total_production': int(sum(result['weekly_production'].values())),
                'demand_fulfillment_rate': float(
                    sum(result['weekly_production'].values()) / 
                    sum(optimizer.demand_dictionary.values()) * 100
                ) if sum(optimizer.demand_dictionary.values()) > 0 else 0,
            }
        }
    }
    
    # Save to JSON file
    output_file = os.path.join(output_dir, f'optimization_result_{timestamp}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Optimization result saved to JSON: {output_file}")
    return output_file

