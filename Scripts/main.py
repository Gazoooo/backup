import argparse
from view import View



parser = argparse.ArgumentParser(description='A Backup Program.')
parser.add_argument('--test', action='store_true', help="Activates test mode by setting the hostname to either 'test_win' or 'test_lin'.")
parser.add_argument('--fast', action='store_true', help='Actibvates fast mode by making backups tasks directly')
args = parser.parse_args()



if __name__ == "__main__":
    if args.test:
        # Test mode
        view = View(testing=True)
        view.start()
    elif args.fast:
        # Fast mode
        raise NotImplementedError("Fast mode is not implemented yet.")
        view = View(fast=True)
        view.start()
    else:
        # Normal mode
        view = View()
        view.start()