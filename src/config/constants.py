"""
Constants module for Supply Roster Optimization Tool
Replaces hard-coded magic numbers with meaningful named constants
"""
from datetime import datetime
from src.preprocess import extract
from datetime import timedelta

class ShiftType:
    """
    Shift type constants to replace magic numbers
    1 = Regular, 2 = Evening, 3 = Overtime
    """
    REGULAR = 1
    EVENING = 2 
    OVERTIME = 3
    
    # All available shifts
    ALL_SHIFTS = [REGULAR, EVENING, OVERTIME]
    
    # Common shift combinations
    REGULAR_AND_OVERTIME = [REGULAR, OVERTIME]  # Normal mode (no evening)
    
    @classmethod
    def get_name(cls, shift_id):
        """Get human-readable name for shift ID"""
        names = {
            cls.REGULAR: "Regular",
            cls.EVENING: "Evening", 
            cls.OVERTIME: "Overtime"
        }
        return names.get(shift_id, "Unknown")
    
    @classmethod
    def get_all_names(cls):
        """Get dictionary mapping shift IDs to names"""
        return {
            cls.REGULAR: "Regular",
            cls.EVENING: "Evening", 
            cls.OVERTIME: "Overtime"
        }

class LineType:
    """
    Line type constants to replace magic numbers
    6 = Long Line, 7 = Mini Load
    """
    LONG_LINE = 6
    MINI_LOAD = 7
    
    # All available line types
    ALL_LINE_TYPES = [LONG_LINE, MINI_LOAD]
    
    @classmethod
    def get_name(cls, line_id):
        """Get human-readable name for line type ID"""
        names = {
            cls.LONG_LINE: "Long Line",
            cls.MINI_LOAD: "Mini Load"
        }
        return names.get(line_id, "Unknown")
    
    @classmethod
    def get_all_names(cls):
        """Get dictionary mapping line type IDs to names"""
        return {
            cls.LONG_LINE: "Long Line",
            cls.MINI_LOAD: "Mini Load"
        }

class KitLevel:
    """
    Kit hierarchy level constants
    0 = Prepack, 1 = Subkit, 2 = Master
    """
    PREPACK = 0
    SUBKIT = 1
    MASTER = 2
    
    # All available levels
    ALL_LEVELS = [PREPACK, SUBKIT, MASTER]
    
    @classmethod
    def get_name(cls, level_id):
        """Get human-readable name for kit level ID"""
        names = {
            cls.PREPACK: "prepack",
            cls.SUBKIT: "subkit", 
            cls.MASTER: "master"
        }
        return names.get(level_id, "unknown")
    
    @classmethod
    def get_all_names(cls):
        """Get dictionary mapping level IDs to names"""
        return {
            cls.PREPACK: "prepack",
            cls.SUBKIT: "subkit", 
            cls.MASTER: "master"
        }
    
    # Removed get_timing_weight method - no longer needed
    # Dependency ordering is now handled by topological sorting

class PaymentMode:
    """
    Payment mode constants
    """
    BULK = "bulk"
    PARTIAL = "partial"
    
    @classmethod
    def get_all_modes(cls):
        """Get all available payment modes"""
        return [cls.BULK, cls.PARTIAL]

# Default configurations using constants
class DefaultConfig:
    """Default configuration values using constants. This works for the default of the session state
    We use session state as the single source of truth for the following values.
    """
    
    # Default date/time configurations
    # Demand filtering date
    DEFAULT_DEMAND_START_DATE = datetime(2026, 1, 5)
    
    # Production period dates
    DEFAULT_PRODUCTION_START_DATE = datetime(2026, 1, 5)
    DEFAULT_PRODUCTION_END_DATE = datetime(2026, 1, 9)
    
    # Planning days (calculated from production dates)
    DEFAULT_PLANNING_DAYS = (DEFAULT_PRODUCTION_END_DATE - DEFAULT_PRODUCTION_START_DATE).days + 1
    DEFAULT_DATE_SPAN = list(range(1, DEFAULT_PLANNING_DAYS + 1))
    
    # Default payment modes by shift
    PAYMENT_MODE_CONFIG = {
        ShiftType.REGULAR: PaymentMode.BULK,
        ShiftType.EVENING: PaymentMode.BULK,
        ShiftType.OVERTIME: PaymentMode.PARTIAL
    }
    
    # Default max hours per shift per person
    MAX_HOUR_PER_SHIFT_PER_PERSON = {
        ShiftType.REGULAR: 7.5,
        ShiftType.EVENING: 7.5,
        ShiftType.OVERTIME: 5
    }
    
    # Default max parallel workers per line type
    MAX_PARALLEL_WORKERS = {
        LineType.LONG_LINE: 15,
        LineType.MINI_LOAD: 15
    }
    
    # Default minimum UNICEF fixed-term employees per day
    FIXED_MIN_UNICEF_PER_DAY = 2
    
    # Default line counts
    LINE_COUNT_LONG_LINE = 3
    LINE_COUNT_MINI_LOAD = 2
    
    # Default max parallel workers per line (for UI)
    MAX_PARALLEL_WORKERS_LONG_LINE = 15
    MAX_PARALLEL_WORKERS_MINI_LOAD = 15
    
    # Default cost rates (example values)
    DEFAULT_COST_RATES = {
        "UNICEF Fixed term": {
            ShiftType.REGULAR: 43.27,
            ShiftType.EVENING: 43.27,
            ShiftType.OVERTIME: 64.91
        },
        "Humanizer": {
            ShiftType.REGULAR: 27.94,
            ShiftType.EVENING: 27.94,
            ShiftType.OVERTIME: 41.91
        }
    }
    
    # ============================================================
    # EMPLOYEE TYPES (Infrastructure - Hardcoded)
    # Source: workforce_info.csv
    # These values rarely change and are hardcoded for performance
    # Verified: 2025-01 - ['Humanizer', 'UNICEF Fixed term']
    # ============================================================
    EMPLOYEE_TYPE_LIST = [
        "UNICEF Fixed term",  # ID: 1
        "Humanizer"           # ID: 2
    ]
    
    # ============================================================
    # OPERATIONAL CONFIGURATION
    # ============================================================
    
    # Default schedule type
    SCHEDULE_TYPE = "weekly"
    
    # Default fixed staff mode
    FIXED_STAFF_MODE = "priority"
    
    # Default hourly rates for UI (simplified)
    UNICEF_RATE_SHIFT_1 = 12.5
    UNICEF_RATE_SHIFT_2 = 15.0
    UNICEF_RATE_SHIFT_3 = 18.75
    HUMANIZER_RATE_SHIFT_1 = 10.0
    HUMANIZER_RATE_SHIFT_2 = 12.0
    HUMANIZER_RATE_SHIFT_3 = 15.0
    # Lazily-derived from data; avoid hard failure at import time (e.g., in Cloud Run without LFS)
    try:
        _pack_df = extract.read_packaging_line_data()
        LINE_LIST = _pack_df["id"].unique().tolist()
        LINE_CNT_PER_TYPE = _pack_df.set_index("id")["line_count"].to_dict()
    except Exception as e:
        # Fallback to empty defaults; runtime getters in optimization_config should be used instead
        print(f"[DefaultConfig] Warning: could not load packaging line data at import: {e}")
        LINE_LIST = []
        LINE_CNT_PER_TYPE = {}

    # Default time padding between tasks (minutes)
    DEFAULT_TIME_PADDING = 20


    # Number of days to handle the given demand
    
    
    # Dynamic method to get max employee per type on day
    @staticmethod
    def get_max_employee_per_type_on_day(date_span):
        """Get max employee per type configuration for given date span"""
        return {
            "UNICEF Fixed term": {
                t: 8 for t in date_span
            },
            "Humanizer": {
                t: 10 for t in date_span
            }
        }
    MAX_UNICEF_PER_DAY = 20
    MAX_HUMANIZER_PER_DAY = 20
    MAX_HOUR_PER_PERSON_PER_DAY = 14
    KIT_LEVELS, KIT_DEPENDENCIES, PRODUCTION_PRIORITY_ORDER = extract.get_production_order_data()

