"""
Quick fix for the 2 remaining tables
Handles Product_id -> product_id column mapping
"""
import os
import django
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ecom.settings')
os.environ['DEBUG'] = 'False'
django.setup()

from django.conf import settings

# Connect to databases
print("\n" + "="*60)
print("🔧 Fixing remaining 2 tables")
print("="*60 + "\n")

sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cur = sqlite_conn.cursor()

db_settings = settings.DATABASES['default']
pg_conn = psycopg2.connect(
    host=db_settings['HOST'],
    database=db_settings['NAME'],
    user=db_settings['USER'],
    password=db_settings['PASSWORD'],
    port=db_settings['PORT'],
    **db_settings.get('OPTIONS', {})
)
pg_cur = pg_conn.cursor()

print("✔ Connected to both databases\n")

def get_actual_pg_columns(table_name):
    """Get actual PostgreSQL column names"""
    pg_cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    return [row[0] for row in pg_cur.fetchall()]

def migrate_with_mapping(sqlite_table, pg_table, column_renames):
    """
    Migrate table with column name mapping
    column_renames: dict of {sqlite_name: pg_name}
    """
    try:
        # Get SQLite columns
        sqlite_cur.execute(f"PRAGMA table_info('{sqlite_table}')")
        sqlite_columns = [col[1] for col in sqlite_cur.fetchall()]
        
        # Get actual PostgreSQL columns
        actual_pg_columns = get_actual_pg_columns(pg_table)
        
        # Build column mapping
        mapped_columns = []
        for sqlite_col in sqlite_columns:
            if sqlite_col in column_renames:
                mapped_columns.append(column_renames[sqlite_col])
            else:
                # Try lowercase
                mapped_columns.append(sqlite_col.lower())
        
        # Verify all columns exist in PostgreSQL
        for pg_col in mapped_columns:
            if pg_col not in actual_pg_columns:
                print(f"❌ Column '{pg_col}' not found in {pg_table}")
                print(f"   Available: {actual_pg_columns}")
                return False
        
        # Fetch data
        sqlite_cur.execute(f"SELECT * FROM '{sqlite_table}'")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            print(f"⚪ {sqlite_table}: No data")
            return True
        
        # Prepare INSERT
        placeholders = ', '.join(['%s'] * len(mapped_columns))
        columns_str = ', '.join([f'"{col}"' for col in mapped_columns])
        
        insert_query = f'''
            INSERT INTO "{pg_table}" ({columns_str}) 
            VALUES ({placeholders}) 
            ON CONFLICT DO NOTHING
        '''
        
        # Insert
        execute_batch(pg_cur, insert_query, rows, page_size=100)
        pg_conn.commit()
        
        # Get count
        pg_cur.execute(f'SELECT COUNT(*) FROM "{pg_table}"')
        count = pg_cur.fetchone()[0]
        
        print(f"✔ {sqlite_table}: {len(rows)} rows → {pg_table} (total: {count})")
        return True
        
    except Exception as e:
        print(f"❌ {sqlite_table}: {e}")
        import traceback
        traceback.print_exc()
        pg_conn.rollback()
        return False

print("Migrating Shop_favourite...")
success1 = migrate_with_mapping(
    'Shop_favourite',
    'shop_favourite',
    {'Product_id': 'product_id'}  # Rename Product_id to product_id
)

print("\nMigrating Shop_orderitem...")
success2 = migrate_with_mapping(
    'Shop_orderitem',
    'shop_orderitem',
    {'Product_id': 'product_id'}  # Rename Product_id to product_id
)

print("\n" + "="*60)
print("🔧 Fixing sequences...")
print("="*60 + "\n")

# Fix sequences
pg_cur.execute("""
    SELECT table_name, column_name, 
           pg_get_serial_sequence(quote_ident(table_name), column_name) as seq
    FROM information_schema.columns
    WHERE table_schema = 'public' 
    AND column_default LIKE 'nextval%'
""")

fixed = 0
for table, column, seq in pg_cur.fetchall():
    if seq:
        try:
            pg_cur.execute(f'SELECT MAX("{column}") FROM "{table}"')
            max_val = pg_cur.fetchone()[0]
            if max_val:
                pg_cur.execute(f"SELECT setval('{seq}', {max_val}, true)")
                pg_conn.commit()
                print(f"  ✔ {table}.{column} → {max_val}")
                fixed += 1
        except Exception as e:
            pass

print(f"\n✔ Fixed {fixed} sequences")

# Close
sqlite_conn.close()
pg_cur.close()
pg_conn.close()

print("\n" + "="*60)
if success1 and success2:
    print("🎉 SUCCESS! All tables migrated!")
    print("="*60)
    print("\n✅ Next steps:")
    print("   1. Test with PostgreSQL: Set DEBUG=False in .env")
    print("   2. Run: python manage.py runserver")
    print("   3. Check products, orders, favourites")
    print("   4. Deploy to Render: git push origin main\n")
else:
    print("⚠️  Some tables failed")
    print("="*60 + "\n")