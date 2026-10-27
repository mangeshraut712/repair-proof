"""Independent bounded policy. This is NOT a sandbox."""
import ast
import difflib
import hashlib
from .schemas import Proposal

def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

ALLOWED_CALLS = {'len','range','sum','min','max','abs','sorted','reversed','enumerate','zip','list','tuple','set','dict','str','int','float','bool','round','all','any'}
ALLOWED_METHODS = {'fromkeys','lower','upper','strip','split','join','append','count','index','replace','startswith','endswith','get','items','keys','values'}
FORBIDDEN_NODES = (ast.Import,ast.ImportFrom,ast.With,ast.AsyncWith,ast.ClassDef,ast.Lambda,ast.Global,ast.Nonlocal,ast.Try,ast.Raise,ast.Delete,ast.Yield,ast.YieldFrom,ast.Await)

def validate(source: str, proposal: Proposal, evidence_ids: set[str]) -> dict:
    reasons=[]
    if not set(proposal.evidence_ids).issubset(evidence_ids): reasons.append('Unknown evidence citation')
    edit=proposal.edits[0]
    if edit.path != 'src/solution.py': reasons.append('Only registered src/solution.py may change; no paths, tests, workflows or manifests')
    if edit.original_sha256 != sha(source): reasons.append('Original hash mismatch')
    if '\0' in edit.replacement or not edit.replacement.isascii(): reasons.append('Binary/non-ASCII source rejected')
    if edit.replacement == source: reasons.append('No change proposed')
    diff=''.join(difflib.unified_diff(source.splitlines(True),edit.replacement.splitlines(True),fromfile='a/src/solution.py',tofile='b/src/solution.py'))
    if len(diff.encode())>8000 or len(edit.replacement.splitlines())>80: reasons.append('Patch exceeds size budget')
    try:
        tree=ast.parse(edit.replacement)
        if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef) or tree.body[0].name!='solve':
            reasons.append('Only one solve function is allowed')
        functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        if len(functions)!=1: reasons.append('Nested or multiple functions rejected')
        original=ast.parse(source).body[0]
        if functions and isinstance(original,ast.FunctionDef) and ast.dump(functions[0].args)!=ast.dump(original.args):
            reasons.append('Original solve signature must be preserved')
        for node in ast.walk(tree):
            if isinstance(node,FORBIDDEN_NODES): reasons.append('Disallowed Python construct: '+type(node).__name__)
            if isinstance(node,ast.FunctionDef) and (node.name!='solve' or node.decorator_list or node.args.defaults or node.args.kw_defaults): reasons.append('Function metadata or nested functions rejected')
            if isinstance(node,ast.Name) and node.id.startswith('_'): reasons.append('Private names rejected')
            if isinstance(node,ast.Attribute) and node.attr not in ALLOWED_METHODS: reasons.append('Attribute is not allowlisted')
            if isinstance(node,ast.Call):
                if not ((isinstance(node.func,ast.Name) and node.func.id in ALLOWED_CALLS) or (isinstance(node.func,ast.Attribute) and node.func.attr in ALLOWED_METHODS)):
                    reasons.append('Call is not allowlisted')
    except (SyntaxError,ValueError,RecursionError): reasons.append('Invalid Python source')
    return {'accepted':not reasons,'reasons':list(dict.fromkeys(reasons)),'diff':diff}
