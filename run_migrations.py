#!/usr/bin/env python3
"""
Simple migration runner for the ABA Services app.
Executes all migration files in order.
"""
import sys
import os
from pathlib import Path
from app import create_app, db
import importlib.util
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending migrations."""
    app = create_app()
    
    with app.app_context():
        # Get the versions directory
        migrations_dir = Path(__file__).parent / 'migrations' / 'versions'
        
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return False
        
        # Get all migration files in order
        migration_files = sorted([
            f for f in migrations_dir.glob('*.py')
            if f.is_file() and not f.name.startswith('__')
        ])
        
        if not migration_files:
            logger.info("No migrations found.")
            return True
        
        logger.info(f"Found {len(migration_files)} migration file(s)")
        
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            
            try:
                # Load the module
                spec = importlib.util.spec_from_file_location("migration", migration_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Run the upgrade function
                if hasattr(module, 'upgrade'):
                    # Create an Alembic-like context for the migration
                    from sqlalchemy.schema import SchemaItem
                    from alembic.operations import Operations
                    from alembic.migration import MigrationContext
                    
                    ctx = MigrationContext.configure(db.engine)
                    op = Operations(ctx)
                    
                    # Execute the upgrade
                    module.upgrade()
                    
                    logger.info(f"✓ Successfully applied: {migration_file.name}")
                else:
                    logger.warning(f"Migration {migration_file.name} has no upgrade() function")
            except Exception as e:
                logger.error(f"✗ Failed to apply {migration_file.name}: {str(e)}")
                return False
        
        logger.info("All migrations completed successfully!")
        return True

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)
