"""
fleet-gateway CLI entry point.

Usage:
  python -m fleet_gateway            # start the gateway server
  python -m fleet_gateway setup      # interactive setup wizard
  python -m fleet_gateway doctor     # check keys and connectivity
  python -m fleet_gateway models     # list available models
  python -m fleet_gateway call <model> <prompt>   # quick one-shot call
"""
import sys


def main():
    args = sys.argv[1:]

    if not args or args[0] == "serve":
        from fleet_gateway.server import main as serve
        serve()

    elif args[0] == "setup":
        from fleet_gateway.setup_wizard import run_setup
        run_setup()

    elif args[0] == "doctor":
        from fleet_gateway.setup_wizard import run_doctor
        run_doctor()

    elif args[0] == "models":
        from fleet_gateway import Fleet
        fleet = Fleet()
        for m in fleet.models():
            status = "✓" if m.get("available") else "✗"
            print(f"  {status}  {m['backend']}/{m['id']:30s}  {', '.join(m.get('capabilities', []))}")

    elif args[0] == "call" and len(args) >= 3:
        from fleet_gateway import call
        result = call(args[1], " ".join(args[2:]))
        print(result or "(no response)")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
