"""Standard JSON parsing plus explicit metadata projection; no body inspection."""
import re
import uuid
from datetime import datetime, timezone

PROVIDERS={'codex','claude','process_wrapper','other'}
KINDS={'session.opened','session.closed','task.started','task.finished','task.resumed',
       'task.waiting_permission','tool.started','tool.finished','child.started','child.finished',
       'background.registered','background.finished'}
STARTS={'task.started','task.resumed','child.started','background.registered','task.waiting_permission'}
FINISHES={'task.finished','child.finished','background.finished'}
TOKEN=re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z')

class ContractError(ValueError):
    """Only fixed error codes; never interpolate rejected payloads."""

def identifier(value, optional=False):
    if value is None and optional:return None
    if not isinstance(value,str) or not TOKEN.fullmatch(value):raise ContractError('INVALID_METADATA')
    return value

def birth(value):
    if not isinstance(value,str) or not 1<=len(value)<=256 or any(ord(c)<32 for c in value):
        raise ContractError('INVALID_METADATA')
    return value

def owner(value, required=False):
    if value is None and not required:return None
    if not isinstance(value,dict):raise ContractError('INVALID_OWNER')
    pid=value.get('pid')
    if type(pid) is not int or pid<=0:raise ContractError('INVALID_OWNER')
    return dict(pid=pid,birth=birth(value.get('birth')))

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def normalize_event(value):
    if not isinstance(value,dict):raise ContractError('INVALID_EVENT')
    if value.get('schema')!='awm.event/1':raise ContractError('UNSUPPORTED_SCHEMA')
    kind=value.get('kind');provider=value.get('provider')
    if not isinstance(kind,str) or kind not in KINDS:raise ContractError('UNSUPPORTED_EVENT')
    if not isinstance(provider,str) or provider not in PROVIDERS:raise ContractError('UNSUPPORTED_PROVIDER')
    generation=value.get('generation',1)
    if type(generation) is not int or not 1<=generation<=2147483647:raise ContractError('INVALID_GENERATION')
    source=value.get('source','synthetic')
    if source not in ('official_hook','synthetic','explicit_wrapper'):raise ContractError('INVALID_SOURCE')
    stamp=value.get('occurred_at')
    if stamp is not None:
        try:
            d=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            if d.tzinfo is None:raise ValueError()
            stamp=d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        except (AttributeError,TypeError,ValueError):raise ContractError('INVALID_TIME') from None
    result=dict(schema='awm.event/1',event_id=identifier(value.get('event_id')),
        instance_id=identifier(value.get('instance_id')),provider=provider,kind=kind,
        session_id=identifier(value.get('session_id')),
        task_id=identifier(value.get('task_id'),optional=kind.startswith('session.')),
        generation=generation,parent_task_id=identifier(value.get('parent_task_id'),optional=True),
        tool_id=identifier(value.get('tool_id'),optional=not kind.startswith('tool.')),
        owner=owner(value.get('owner'),required=kind in STARTS),source=source,occurred_at=stamp)
    return result

def normalize_hook(value, *, instance_id, provider, owner, generation=1):
    if not isinstance(value,dict):raise ContractError('INVALID_HOOK')
    mapping={'SessionStart':'session.opened','SessionEnd':'session.closed',
        'UserPromptSubmit':'task.started','Stop':'task.finished','StopFailure':'task.finished',
        'Interrupt':'task.finished','PermissionRequest':'task.waiting_permission',
        'PreToolUse':'tool.started','PostToolUse':'tool.finished','PostToolUseFailure':'tool.finished',
        'SubagentStart':'child.started','SubagentStop':'child.finished'}
    name=value.get('hook_event_name')
    if not isinstance(name,str) or name not in mapping:raise ContractError('UNSUPPORTED_HOOK')
    kind=mapping[name];agent=value.get('agent_id')
    task=value.get('turn_id') or 'main'
    if name.startswith('Subagent') or agent is not None:
        task='agent:'+identifier(agent)
    return normalize_event(dict(schema='awm.event/1',event_id=value.get('event_id') or str(uuid.uuid4()),
        instance_id=instance_id,provider=provider,kind=kind,session_id=value.get('session_id'),
        task_id=None if kind.startswith('session.') else task,generation=generation,
        parent_task_id=value.get('turn_id') if kind.startswith('child.') else None,
        tool_id=value.get('tool_use_id'),owner=owner,source='official_hook'))

def normalize_config(value):
    if not isinstance(value,dict) or value.get('schema')!='awm.config/1':raise ContractError('INVALID_CONFIG')
    instances=value.get('instances')
    if not isinstance(instances,list):raise ContractError('INVALID_CONFIG')
    seen=set();result=[]
    for raw in instances:
        if not isinstance(raw,dict):raise ContractError('INVALID_CONFIG')
        iid=identifier(raw.get('id'));provider=raw.get('provider')
        if iid in seen:raise ContractError('DUPLICATE_INSTANCE')
        if not isinstance(provider,str) or provider not in PROVIDERS:raise ContractError('UNSUPPORTED_PROVIDER')
        enabled=raw.get('enabled',True)
        if type(enabled) is not bool:raise ContractError('INVALID_CONFIG')
        instance=dict(id=iid,provider=provider,enabled=enabled)
        path=raw.get('config_root')
        if path is not None:
            if not isinstance(path,str) or not 1<=len(path)<=4096 or '\x00' in path:raise ContractError('INVALID_CONFIG')
            instance['config_root']=path
        result.append(instance);seen.add(iid)
    return dict(schema='awm.config/1',instances=result)
