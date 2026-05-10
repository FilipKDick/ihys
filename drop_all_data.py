#!/usr/bin/env python3
"""
Script to drop all data from Supabase tables for Who's That Seiyuu project.
⚠️  WARNING: This will DELETE ALL DATA from your tables!

Requirements:
- pip install supabase python-dotenv
- .env.backend file with SUPABASE_URL and SUPABASE_SERVICE_KEY
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv('.env.backend')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print('❌ Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env.backend file')
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Table names (in deletion order - respecting foreign key constraints)
TABLES_TO_CLEAR = [
    'character_actors',  # Junction table - delete first
    'characters',        # References anime - delete before anime
    'actors',           # Independent table
    'users',            # Independent table
    'anime'             # Referenced by characters - delete last
]


def get_table_count(table_name: str) -> int:
    """Get the number of records in a table."""
    try:
        result = supabase.table(table_name).select('id', count='exact').execute()
        return result.count or 0
    except Exception as e:
        print(f'⚠️  Could not count records in {table_name}: {e}')
        return 0


def show_table_status():
    """Display current record counts for all tables."""
    print('\n📊 Current table status:')
    print('=' * 40)
    total_records = 0
    
    for table in TABLES_TO_CLEAR:
        count = get_table_count(table)
        total_records += count
        print(f'  {table:<18}: {count:>6} records')
    
    print('=' * 40)
    print(f'  {"TOTAL":<18}: {total_records:>6} records')
    print()
    
    return total_records


def clear_table(table_name: str) -> bool:
    """Clear all data from a specific table."""
    try:
        print(f'🗑️  Clearing {table_name}...', end=' ')
        
        # Delete all records (Supabase doesn't support TRUNCATE)
        result = supabase.table(table_name).delete().neq('id', 0).execute()
        
        # Verify deletion
        final_count = get_table_count(table_name)
        if final_count == 0:
            print('✅ Done')
            return True
        else:
            print(f'⚠️  {final_count} records remain')
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False


def confirm_deletion(total_records: int) -> bool:
    """Get user confirmation for deletion."""
    if total_records == 0:
        print('ℹ️  All tables are already empty. Nothing to delete.')
        return False
    
    print(f'⚠️  WARNING: This will permanently delete {total_records} records!')
    print('⚠️  This action cannot be undone!')
    print()
    
    # Double confirmation for safety
    response1 = input('Are you sure you want to delete ALL data? (type "yes" to confirm): ').strip()
    if response1.lower() != 'yes':
        print('❌ Operation cancelled.')
        return False
    
    response2 = input(f'Really delete {total_records} records? (type "DELETE ALL" to confirm): ').strip()
    if response2 != 'DELETE ALL':
        print('❌ Operation cancelled.')
        return False
    
    return True


def clear_all_tables():
    """Clear all data from all tables."""
    print('\n🗑️  Starting deletion process...')
    print('=' * 40)
    
    success_count = 0
    failed_tables = []
    
    for table in TABLES_TO_CLEAR:
        if clear_table(table):
            success_count += 1
        else:
            failed_tables.append(table)
    
    print('=' * 40)
    print(f'✅ Successfully cleared: {success_count}/{len(TABLES_TO_CLEAR)} tables')
    
    if failed_tables:
        print(f'❌ Failed to clear: {", ".join(failed_tables)}')
        return False
    
    return True


def main():
    """Main function."""
    print('🗑️  Who\'s That Seiyuu Supabase Data Cleanup Tool')
    print('=' * 50)
    print(f'Database: {SUPABASE_URL}')
    print(f'Tables to clear: {", ".join(TABLES_TO_CLEAR)}')
    
    # Show current status
    total_records = show_table_status()
    
    # Get confirmation
    if not confirm_deletion(total_records):
        return
    
    # Perform deletion
    if clear_all_tables():
        print('\n✨ All data has been successfully deleted!')
        
        # Show final status
        print('\n📊 Final status:')
        show_table_status()
    else:
        print('\n❌ Some tables could not be cleared. Check the errors above.')


if __name__ == '__main__':
    main()