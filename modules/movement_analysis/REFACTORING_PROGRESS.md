# Backend Module Refactoring Progress

## Completed Files ✅

### 1. helper_movement_analysis.py (NEW - Merged file)
- **Location**: `/modules/movement_analysis/helper_movement_analysis.py`
- **Source**: Merged from `config.py`, `csv_helper.py`, and `file_helper.py`
- **Status**: ✅ Created
- **Sections**:
  - Configuration settings (PROJECT_ROOT, DATA_DIR, PLOT_COLORS, etc.)
  - CSV template generation functions
  - CSV validation functions
  - File detection and analysis functions

### 2. data_load_movement_analysis.py (RENAMED)
- **Location**: `/modules/movement_analysis/data_load_movement_analysis.py`
- **Original**: `data_load_p2.py`
- **Status**: ✅ Created
- **Changes**: No import updates needed (file was self-contained)
- **Functions**: Cache management, file type identification, route loading, circuit mapping

### 3. data_filter_movement_analysis.py (RENAMED)
- **Location**: `/modules/movement_analysis/data_filter_movement_analysis.py`
- **Original**: `data_filter_p2.py`
- **Status**: ✅ Created
- **Import Updates**:
  - ✅ `from .data_load_p2` → `from .data_load_movement_analysis`
- **Functions**: Timestamp processing, route details, circuit data filtering, movement time calculations

## Pending Files 🔄

### 4. plot_movement_analysis.py (CREATED ✅)
- **Location**: `/modules/movement_analysis/plot_movement_analysis.py`
- **Original**: `plot_generator_phase2.py` (~1056 lines)
- **Status**: ✅ Created
- **Import Updates**:
  - ✅ `from .data_load_p2` → `from .data_load_movement_analysis`
  - ✅ `from .data_filter_p2` → `from .data_filter_movement_analysis`
- **Functions**: Plotly visualization generation with dark theme

### 5. routes_movement_analysis.py (TO BE CREATED)
- **Location**: `/modules/movement_analysis/routes_movement_analysis.py`
- **Original**: `routes_phase2.py` (~672 lines)
- **Required Import Updates**:
  - All relative imports from old module names
  - Template reference: `index_phase2.html` → `movement_analysis.html`
  - Import helper functions from new `helper_movement_analysis.py`
- **Functions**: Flask blueprint with 15 API endpoints

### 6. __init__.py (TO BE CREATED)
- **Location**: `/modules/movement_analysis/__init__.py`
- **Original**: `phase2_app/__init__.py`
- **Required Import Updates**:
  - `from .routes_phase2` → `from .routes_movement_analysis`
  - Update logger name
- **Functions**: Flask app factory initialization

## Main App Integration 📝

### app.py Update (PENDING)
Current:
```python
from modules.phase2_app.routes_phase2 import main as phase2_blueprint
app.register_blueprint(phase2_blueprint, url_prefix='/phase2')
```

Will become:
```python
from modules.movement_analysis.routes_movement_analysis import main as movement_analysis_blueprint
app.register_blueprint(movement_analysis_blueprint, url_prefix='/phase2')  # Keep /phase2 for backward compatibility
```

## Testing Checklist 📋

After all files are created:
1. ⬜ Start Flask application
2. ⬜ Test file upload interface at `/phase2/upload`
3. ⬜ Test route loading API at `/phase2/api/routes`
4. ⬜ Test visualization generation
5. ⬜ Test movement times display
6. ⬜ Verify all 15 API endpoints work
7. ⬜ Check browser console for JavaScript errors
8. ⬜ Verify template rendering (movement_analysis.html)

## Deletion Checklist 🗑️

After successful testing:
1. ⬜ Delete `/modules/phase2_app/` directory
2. ⬜ Delete `templates/upload_phase2.html`
3. ⬜ Delete `templates/index_phase2.html`
4. ⬜ Delete `static/phase2.js` (if exists)
5. ⬜ Delete `static/phase2.css` (if exists)
6. ⬜ Update any documentation references

## Next Steps 🎯

1. Create `plot_movement_analysis.py` (large file with visualization logic)
2. Create `routes_movement_analysis.py` (Flask blueprint with all endpoints)
3. Create `__init__.py` (module initialization)
4. Update `app.py` to use new module
5. Test all functionality
6. Delete old files after confirmation

## File Size Reference 📊

- helper_movement_analysis.py: ~450 lines (merged from 3 files)
- data_load_movement_analysis.py: ~296 lines
- data_filter_movement_analysis.py: ~643 lines
- plot_movement_analysis.py: ~1056 lines (pending)
- routes_movement_analysis.py: ~672 lines (pending)
- __init__.py: ~50 lines (estimated)

**Total**: ~3,167 lines of Python code to migrate
**Completed**: ~1,389 lines (44%)
**Remaining**: ~1,778 lines (56%)
