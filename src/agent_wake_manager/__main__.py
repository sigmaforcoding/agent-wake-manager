"""Development-only public CLI; requires an explicit isolated data directory."""
import argparse
import json
import sys
from pathlib import Path
from .contracts import ContractError, normalize_config
from .core import Store

def read_json(text):
    try:return json.loads(text.decode('utf-8') if isinstance(text,bytes) else text)
    except (ValueError,TypeError):raise ContractError('INVALID_JSON') from None

def main(argv=None):
    parser=argparse.ArgumentParser(description='Isolated Agent Wake Manager development core')
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--config',type=Path)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('status','event','pause','resume'):sub.add_parser(name)
    reset=sub.add_parser('reset',help='Clear task records; explicit confirmation required')
    reset.add_argument('--confirm',action='store_true')
    args=parser.parse_args(argv)
    try:
        config=normalize_config(read_json(args.config.read_text()) if args.config else
            {'schema':'awm.config/1','instances':[]})
        data=args.data_dir.expanduser().resolve()
        store=Store(data/'state.sqlite3',config)
        if args.command=='event':
            raw=sys.stdin.buffer.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ContractError('INPUT_TOO_LARGE')
            store.apply(read_json(raw))
        elif args.command=='pause':store.pause()
        elif args.command=='resume':store.resume()
        elif args.command=='reset':
            if not args.confirm:
                print('RESET_CONFIRMATION_REQUIRED: reset clears all instance task records; use reset --confirm.',file=sys.stderr)
                return 2
            print('RESET_CLEARS_TASKS: clearing all instance task records; pause state is unchanged.',file=sys.stderr)
            store.reset(confirm=True)
        # Export only the canonical metadata journal, never raw input or exception text.
        audit=data/'audit.jsonl'
        with audit.open('w') as stream:
            for event in store.events():stream.write(json.dumps(event,sort_keys=True)+'\n')
        audit.chmod(0o600)
        print(json.dumps(store.status(),sort_keys=True))
        return 0
    except ContractError as error:
        print(str(error),file=sys.stderr);return 2
    except Exception:
        print('CORE_IO_ERROR',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
