# Parent Details Update Summary

## Overview
This update enhances the client parent/guardian information capture by:
1. Splitting parent name into first and last name
2. Adding phone number for first parent (in addition to email)
3. Adding complete information for a second parent (first name, last name, email, phone)
4. Maintaining backward compatibility with existing records

## Database Schema Changes

### New Columns Added to `clients` Table
```sql
parent_firstname VARCHAR(51)     -- Parent 1 first name
parent_lastname VARCHAR(51)      -- Parent 1 last name
parent_email VARCHAR(120)        -- Parent 1 email
parent_cell VARCHAR(10)          -- Parent 1 phone number

parent2_firstname VARCHAR(51)    -- Parent 2 first name (optional)
parent2_lastname VARCHAR(51)     -- Parent 2 last name (optional)
parent2_email VARCHAR(120)       -- Parent 2 email (optional)
parent2_cell VARCHAR(10)         -- Parent 2 phone number (optional)
```

### Legacy Columns (Kept for Backward Compatibility)
```sql
parentname VARCHAR(101)   -- Single name field (deprecated)
parentemail VARCHAR(120)  -- First parent email (deprecated)
parentemail2 VARCHAR(120) -- Second parent email (deprecated)
parentcell VARCHAR(10)    -- First parent phone (deprecated)
```

## Migration
**File:** `migrations/versions/005_add_parent_details.py`

Run migration:
```bash
flask db upgrade
```

## Model Changes (`app/models.py`)

### New Fields
- `parent_firstname`, `parent_lastname`, `parent_email`, `parent_cell` - First parent details
- `parent2_firstname`, `parent2_lastname`, `parent2_email`, `parent2_cell` - Second parent details

### Helper Methods
```python
def get_parent1_name()   # Returns first parent full name
def get_parent1_email()  # Returns first parent email
def get_parent1_phone()  # Returns first parent phone
```

## Form Changes (`app/clients/forms.py`)

### AddClientForm & UpdateClientForm
Replaced:
- `parentname` → `parent_firstname` + `parent_lastname` (both fields)
- Added `parent_email` (explicitly named)
- Renamed `parentcell` → `parent_cell`
- Replaced `parentemail2` with `parent2_email`

Added second parent fields:
- `parent2_firstname`
- `parent2_lastname`
- `parent2_email`
- `parent2_cell`

**Note:** All parent 2 fields are optional (use `Optional()` validator)

## View Changes (`app/clients/views.py`)

### add_client()
- Processes new parent fields
- Creates legacy `parentname` field for backward compatibility
- Normalizes phone numbers to digits-only

### update_client()
- On GET: Populates form by preferring new fields, falls back to legacy fields
  - If `parent_firstname` exists, uses it
  - Otherwise, splits `parentname` if it contains a space
- On POST: 
  - Updates both new and legacy fields simultaneously
  - Ensures all records remain accessible via legacy fields

## Template Changes

### `app/clients/templates/add.html` & `update.html`
- Split parent section into "Parent 1 Information" and "Parent 2 Information"
- Parent 1 section: firstname, lastname, email, phone (all required)
- Parent 2 section: firstname, lastname, email, phone (all optional, marked with "Optional" badge)
- Better visual organization with Bootstrap cards

## Backward Compatibility

### For Existing Records
When updating an existing client record:
1. Form detects old data in `parentname` field
2. Automatically splits name on space: `f"{firstname} {lastname}"`
3. Populates new `parent_firstname` and `parent_lastname` fields
4. User can edit and save the structured data
5. System updates both new and legacy fields

### Legacy Field Sync
After any client update:
- `parentname` = `"{parent_firstname} {parent_lastname}"`
- `parentemail` = `parent_email`
- `parentemail2` = `parent2_email`
- `parentcell` = `parent_cell`

This ensures:
- Existing code referencing legacy fields continues to work
- Reports and emails using `client.parentname` remain unchanged
- Email templates don't need updates

## Usage

### Adding a New Client
1. Enter client information
2. Enter Parent 1: first name, last name, email, phone
3. Optionally enter Parent 2 information
4. Submit - data is saved in both new and legacy fields

### Updating an Existing Client
1. Open client record in update form
2. System auto-populates Parent 1 fields from either:
   - New fields (if already migrated)
   - Legacy `parentname` split into first/last (if old record)
3. Edit as needed
4. Submit - updates both new and legacy fields

## Deployment Steps

1. **Backup Database** (recommended)
2. **Run Migration**
   ```bash
   flask db upgrade
   ```
3. **Test**
   - Add a new client - verify all parent fields save correctly
   - Update an existing client - verify name splitting works
   - Check that email recipients include both parents

## Affected Components
- Client Management (Add/Update forms)
- Invoice Generation (uses `parentname` - no change needed)
- Email Notifications (uses `parentemail`, `parentemail2` - fallback available)
- Reports (can be updated to use new fields if desired)

## Future Enhancements
- Email template updates to separately greet parent 1 and parent 2
- Invoice PDF updates to show both parents if available
- Reports to include second parent email/phone columns
- API endpoints to return structured parent data
