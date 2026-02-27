from fpdf import FPDF
import pandas as pd
import datetime

class OptimizationReport(FPDF):
    def header(self):
        # Logo could go here
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Supply Roster Optimization Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_optimization_report(results):
    """
    Generate a PDF report from the optimization results.
    Returns the binary content of the PDF.
    """
    pdf = OptimizationReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. Weekly Summary ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. Weekly Performance Summary', 0, 1)
    
    # Extract metrics
    # Ensure simplified structure (copying logic from views for safety)
    if 'objective' in results:
        total_cost = results['objective']
    elif 'metadata' in results and 'optimal_cost' in results['metadata']:
        total_cost = results['metadata']['optimal_cost']
    else:
        total_cost = 0
        
    # Calculate total production
    weekly_production = results.get('weekly_production', {})
    if not weekly_production and 'results' in results and 'production' in results['results']:
         # Parse from new structure
         by_product = results['results']['production'].get('by_product', {})
         weekly_production = {k: v.get('units_produced', 0) for k, v in by_product.items()}
         
    total_production = sum(weekly_production.values())
    
    # Fulfillment rate
    # Note: Accessing config here might be tricky if paths are relative, 
    # but we are in the same environment.
    try:
        from src.config.optimization_config import get_demand_dictionary
        DEMAND_DICTIONARY = get_demand_dictionary()
        total_demand = sum(DEMAND_DICTIONARY.values())
        fulfillment_rate = (total_production / total_demand * 100) if total_demand > 0 else 0
    except Exception:
        total_demand = 0
        fulfillment_rate = 0

    cost_per_unit = total_cost / total_production if total_production > 0 else 0

    # Draw Summary Table (Simple Grid)
    pdf.set_font('Arial', '', 10)
    col_width = 45
    row_height = 8
    
    headers = ['Total Cost', 'Total Production', 'Fulfillment Rate', 'Cost per Unit']
    values = [f"{total_cost:,.2f} Euro", f"{total_production:,.0f} units", f"{fulfillment_rate:.1f}%", f"{cost_per_unit:.2f} Euro"]
    
    # Header Row
    pdf.set_fill_color(240, 240, 240)
    for h in headers:
            pdf.cell(col_width, row_height, h, 1, 0, 'C', 1)
    pdf.ln()
    
    # Value Row
    for v in values:
        pdf.cell(col_width, row_height, v, 1, 0, 'C')
    pdf.ln(15)

    # --- 2. Production vs Demand ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. Detailed Production Plan', 0, 1)

    # Load demand safely
    try:
        from src.config.optimization_config import get_demand_dictionary
        DEMAND_DICTIONARY = get_demand_dictionary()
    except Exception:
        DEMAND_DICTIONARY = {}
    
    pdf.set_font('Arial', 'B', 9) # Smaller font for table
    table_headers = ['Product', 'Production', 'Demand', 'Gap']
    w = [60, 40, 40, 40]
    
    for i, h in enumerate(table_headers):
        pdf.cell(w[i], 7, h, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 9)
    for product, production in weekly_production.items():
        demand = DEMAND_DICTIONARY.get(product, 0)
        gap = production - demand
        
        pdf.cell(w[0], 6, str(product), 1)
        pdf.cell(w[1], 6, str(int(production)), 1, 0, 'R')
        pdf.cell(w[2], 6, str(int(demand)), 1, 0, 'R')
        
        # Color the gap if negative
        if gap < 0:
            pdf.set_text_color(255, 0, 0)
        pdf.cell(w[3], 6, str(int(gap)), 1, 0, 'R')
        pdf.set_text_color(0, 0, 0) # Reset color
        pdf.ln()
    
    pdf.ln(10)
    
    # --- 3. Employee Allocation Details ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '3. Employee Allocation Details', 0, 1)
    
    # Extract employee counts 
    # Use 'employee_count_optimized' if available
    employee_data = []
    if 'results' in results and 'employee_count_optimized' in results['results']:
        employee_data = results['results']['employee_count_optimized']
    elif 'employee_count_optimized' in results:
        employee_data = results['employee_count_optimized']
        
    if employee_data:
        # Group by Day, Shift
        # Create a pivot-like structure for the PDF
        # We'll list rows: Day | Shift | UNICEF Count | Humanizer Count
        
        # Organize data
        allocation_map = {} # (Day, Shift) -> {Type: Count}
        for item in employee_data:
            key = (item['day'], item['shift_name'])
            if key not in allocation_map:
                allocation_map[key] = {}
            allocation_map[key][item['employee_type']] = item['employee_count']
            
        # Sort keys
        sorted_keys = sorted(allocation_map.keys(), key=lambda x: x[0]) # Sort by day
        
        pdf.set_font('Arial', 'B', 9)
        headers = ['Day', 'Shift', 'UNICEF Fixed term', 'Humanizer']
        w = [30, 40, 50, 50]
        
        for i, h in enumerate(headers):
             pdf.cell(w[i], 7, h, 1, 0, 'C', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 9)
        for day, shift in sorted_keys:
            counts = allocation_map[(day, shift)]
            unicef = counts.get('UNICEF Fixed term', 0)
            humanizer = counts.get('Humanizer', 0)
            
            # Skip if 0 workers? Maybe keep for completeness if it's a valid shift
            if unicef == 0 and humanizer == 0:
                continue

            pdf.cell(w[0], 6, f"Day {day}", 1)
            pdf.cell(w[1], 6, shift, 1)
            pdf.cell(w[2], 6, str(unicef), 1, 0, 'C')
            pdf.cell(w[3], 6, str(humanizer), 1, 0, 'C')
            pdf.ln()
            
    else:
        pdf.cell(0, 10, 'No employee allocation data available.', 0, 1)

    pdf.ln(10)
    
    # --- 4. Detailed Schedule (Optional - could be long) ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '4. Detailed Schedule (Overview)', 0, 1)
    
    # Flatten schedule logic
    schedule_items = []
    if 'run_schedule' in results:
        schedule_items = results['run_schedule']
    elif 'results' in results and 'schedule' in results['results']:
        # Reuse the parsing logic concept efficiently
        # Or simplistic parsing
        pass # Assuming run_schedule is usually populated by the compatibility layer in the app before passing here
             # But wait, we are passing 'results' directly from session_state in app.py.
             # The 'display_optimization_results' does the conversion.
             # We should probably do the conversion here too.
        
    # We'll assume the simple structure for now, if empty try to parse
    if not schedule_items and 'results' in results and 'schedule' in results['results']:
         # Quick re-implementation of flattened schedule
         raw_sched = results['results']['schedule']
         for day_k, day_v in raw_sched.items():
            day_id = day_v.get('day_id', str(day_k))
            for line_k, line_v in day_v.items():
                if line_k == 'day_id': continue
                line_type_id = line_v.get('line_type_id', 0)
                line_idx = line_v.get('line_idx', 0)
                for shift_k, shift_v in line_v.items():
                    if shift_k in ['line_type', 'line_type_id', 'line_idx']: continue
                    shift_name = shift_v.get('shift_name', str(shift_k))
                    for prod in shift_v.get('products', []):
                         schedule_items.append({
                             'day': day_id,
                             'line_type_id': line_type_id,
                             'line_idx': line_idx,
                             'shift_name': shift_name,
                             'product': prod.get('product', ''),
                             'run_hours': prod.get('run_hours', 0),
                             'units': prod.get('units', 0)
                         })

    if schedule_items:
        # Filter 0 activity
        schedule_items = [x for x in schedule_items if x['run_hours'] > 0 or x['units'] > 0]
        
        pdf.set_font('Arial', 'B', 8)
        headers = ['Day', 'Line', 'Shift', 'Product', 'Hours', 'Units']
        w = [20, 25, 30, 75, 20, 20]
        
        for i, h in enumerate(headers):
             pdf.cell(w[i], 6, h, 1, 0, 'C', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        # Limit rows to prevent massive PDFs? Let's show all for now but watch out.
        for item in schedule_items:
            line_str = f"Line {item.get('line_type_id', '?')}-{item.get('line_idx', '?')}"
            
            pdf.cell(w[0], 5, f"Day {item.get('day', '?')}", 1)
            pdf.cell(w[1], 5, line_str, 1)
            pdf.cell(w[2], 5, str(item.get('shift_name', item.get('shift', '?'))), 1)
            pdf.cell(w[3], 5, str(item.get('product', ''))[:40], 1) # Truncate long names
            pdf.cell(w[4], 5, f"{item.get('run_hours', 0):.1f}", 1, 0, 'R')
            pdf.cell(w[5], 5, f"{item.get('units', 0):.0f}", 1, 0, 'R')
            pdf.ln()
    else:
        pdf.cell(0, 10, 'No schedule data available.', 0, 1)

    return pdf.output(dest='S').encode('latin-1')
