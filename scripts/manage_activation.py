#!/usr/bin/env python3
"""Small CLI to activate/deactivate employees and clients.

Usage examples:
  # Deactivate employee 5, but fail if they supervise active clients
  python scripts/manage_activation.py employee deactivate 5

  # Deactivate employee 5 and also deactivate their clients
  python scripts/manage_activation.py employee deactivate 5 --cascade-clients

  # Reactivate client 12
  python scripts/manage_activation.py client activate 12

Options:
  --force: skip safety checks (use with care)
  --cascade-clients: when operating on an employee, also operate on their clients

This script imports the Flask app and runs inside app.app_context() so it works the same as
the web code (same models and DB session).
"""
import argparse
import sys
from app import app, db
from app.models import Employee, Client, Invoice


def deactivate_employee(employee_id: int, cascade_clients: bool = False, force: bool = False) -> int:
    emp = Employee.query.get(employee_id)
    if not emp:
        print(f"Employee with id={employee_id} not found.")
        return 2

    # Check active clients supervised by this employee
    active_clients = Client.query.filter_by(supervisor_id=emp.id, is_active=True).all()
    if active_clients and not (cascade_clients or force):
        print(f"Employee supervises {len(active_clients)} active client(s). Use --cascade-clients to deactivate them or --force to ignore this check.")
        return 3

    try:
        emp.is_active = False
        print(f"Deactivated employee {emp.firstname} {emp.lastname} (id={emp.id})")

        if cascade_clients:
            for c in active_clients:
                c.is_active = False
                print(f"  -> Deactivated client {c.firstname} {c.lastname} (id={c.id})")

        db.session.commit()
        return 0
    except Exception as e:
        db.session.rollback()
        print("Error while deactivating employee:", e)
        return 1


def activate_employee(employee_id: int) -> int:
    emp = Employee.query.get(employee_id)
    if not emp:
        print(f"Employee with id={employee_id} not found.")
        return 2

    try:
        emp.is_active = True
        db.session.commit()
        print(f"Reactivated employee {emp.firstname} {emp.lastname} (id={emp.id})")
        return 0
    except Exception as e:
        db.session.rollback()
        print("Error while reactivating employee:", e)
        return 1


def deactivate_client(client_id: int, force: bool = False) -> int:
    client = Client.query.get(client_id)
    if not client:
        print(f"Client with id={client_id} not found.")
        return 2

    # Check for unpaid invoices
    unpaid = Invoice.query.filter_by(client_id=client.id).filter(Invoice.status != 'Paid').count()
    if unpaid and not force:
        print(f"Client has {unpaid} unpaid invoice(s). Use --force to deactivate anyway.")
        return 3

    try:
        client.is_active = False
        db.session.commit()
        print(f"Deactivated client {client.firstname} {client.lastname} (id={client.id})")
        return 0
    except Exception as e:
        db.session.rollback()
        print("Error while deactivating client:", e)
        return 1


def activate_client(client_id: int) -> int:
    client = Client.query.get(client_id)
    if not client:
        print(f"Client with id={client_id} not found.")
        return 2

    try:
        client.is_active = True
        db.session.commit()
        print(f"Reactivated client {client.firstname} {client.lastname} (id={client.id})")
        return 0
    except Exception as e:
        db.session.rollback()
        print("Error while reactivating client:", e)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Activate/deactivate employees and clients")
    subparsers = parser.add_subparsers(dest='entity', required=True)

    # Employee parser
    ep = subparsers.add_parser('employee', help='Operate on employees')
    ep.add_argument('action', choices=['activate', 'deactivate'], help='Action')
    ep.add_argument('id', type=int, help='Employee id')
    ep.add_argument('--cascade-clients', action='store_true', help='When deactivating an employee, also deactivate their active clients')
    ep.add_argument('--force', action='store_true', help='Skip safety checks')

    # Client parser
    cp = subparsers.add_parser('client', help='Operate on clients')
    cp.add_argument('action', choices=['activate', 'deactivate'], help='Action')
    cp.add_argument('id', type=int, help='Client id')
    cp.add_argument('--force', action='store_true', help='Skip safety checks')

    args = parser.parse_args(argv)

    with app.app_context():
        if args.entity == 'employee':
            if args.action == 'deactivate':
                return_code = deactivate_employee(args.id, cascade_clients=args.cascade_clients, force=args.force)
                sys.exit(return_code)
            else:
                return_code = activate_employee(args.id)
                sys.exit(return_code)

        elif args.entity == 'client':
            if args.action == 'deactivate':
                return_code = deactivate_client(args.id, force=args.force)
                sys.exit(return_code)
            else:
                return_code = activate_client(args.id)
                sys.exit(return_code)


if __name__ == '__main__':
    main()
