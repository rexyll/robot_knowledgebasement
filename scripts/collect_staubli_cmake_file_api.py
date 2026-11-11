#!/usr/bin/env python3
"""Collect a normalized CMake File API codemodel-v2 snapshot."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

def read_json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"{path}: expected JSON object")
    return value

def collect(build_dir: Path, build_testing: bool, configuration: str|None, exports_file: Path|None, export_root: Path|None = None) -> dict[str,Any]:
    reply=build_dir/".cmake/api/v1/reply"
    indexes=sorted(reply.glob("index-*.json"),key=lambda p:p.stat().st_mtime_ns)
    if not indexes and (reply/"index.json").exists(): indexes=[reply/"index.json"]
    if not indexes: raise FileNotFoundError(f"no CMake File API index found in {reply}")
    index=read_json(indexes[-1])
    ref=index.get("reply",{}).get("codemodel-v2")
    if not isinstance(ref,dict) or not isinstance(ref.get("jsonFile"),str): raise ValueError("missing codemodel-v2 reply")
    model=read_json(reply/ref["jsonFile"])
    configs=model.get("configurations")
    if not isinstance(configs,list) or not configs: raise ValueError("codemodel has no configurations")
    selected=next((x for x in configs if configuration is None or x.get("name")==configuration),None)
    if selected is None: raise ValueError(f"configuration {configuration!r} not found")
    refs=selected.get("targets",[])
    if not isinstance(refs,list): raise ValueError("configuration.targets must be an array")
    raw=[]; ids={}
    for item in refs:
        if not isinstance(item,dict) or not isinstance(item.get("jsonFile"),str): raise ValueError("invalid target reference")
        target=read_json(reply/item["jsonFile"])
        tid=target.get("id",item.get("id")); name=target.get("name",item.get("name"))
        if not isinstance(tid,str) or not isinstance(name,str): raise ValueError("target requires string id and name")
        ids[tid]=name; raw.append((item,target))
    targets=[]
    for ref_item,target in raw:
        name=target.get("name",ref_item.get("name"))
        deps=target.get("dependencies",[])
        if not isinstance(deps,list): raise ValueError(f"{name}.dependencies must be an array")
        dep_names=sorted({ids[d["id"]] for d in deps if isinstance(d,dict) and isinstance(d.get("id"),str) and d["id"] in ids})
        includes=set(); defines=set()
        for group in target.get("compileGroups",[]):
            if not isinstance(group,dict): continue
            includes.update(x["path"] for x in group.get("includes",[]) if isinstance(x,dict) and isinstance(x.get("path"),str))
            defines.update(x["define"] for x in group.get("defines",[]) if isinstance(x,dict) and isinstance(x.get("define"),str))
        targets.append({"name":name,"type":target.get("type",ref_item.get("type","UNKNOWN")),"dependencies":dep_names,
                        "include_directories":sorted(includes),"compile_definitions":sorted(defines)})
    manifest=build_dir/"install_manifest.txt"
    install=[x.strip() for x in manifest.read_text(encoding="utf-8").splitlines() if x.strip()] if manifest.exists() else []
    if exports_file and export_root:
        raise ValueError("use only one of --exported-targets-file and --export-root")
    exports=[]
    export_sources=[]
    if exports_file:
        exports=[x.strip() for x in exports_file.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
        export_sources=[str(exports_file.resolve())]
    if export_root:
        prefix=export_root.resolve()
        if not prefix.is_dir():
            raise FileNotFoundError(f"export root is not a directory: {prefix}")
        import re
        pattern=re.compile(r"add_(?:library|executable)\s*\(\s*([A-Za-z0-9_.:+-]+)\s+(?:(?:UNKNOWN|STATIC|SHARED|MODULE|INTERFACE)\s+)?IMPORTED\b",re.IGNORECASE)
        candidates=list((prefix/"lib"/"cmake").rglob("*Targets.cmake")) if (prefix/"lib"/"cmake").exists() else []
        share=prefix/"share"
        if share.exists():
            candidates.extend(share.rglob("*Targets.cmake"))
        for path in sorted(set(candidates)):
            resolved=path.resolve()
            if not resolved.is_relative_to(prefix):
                continue
            relative=resolved.relative_to(prefix)
            if not (("lib" in relative.parts and "cmake" in relative.parts) or ("share" in relative.parts and "cmake" in relative.parts)):
                continue
            content=resolved.read_text(encoding="utf-8",errors="replace")
            names=pattern.findall(content)
            if names:
                exports.extend(names)
                export_sources.append(str(resolved))
    exports=sorted(set(exports))
    return {"schema_version":"1.0.0","configuration_id":str(selected.get("name") or build_dir.name),
            "build_testing":build_testing,"build_directory":str(build_dir.resolve()),"cmake_file_api_index":indexes[-1].name,
            "targets":sorted(targets,key=lambda x:x["name"]),"install_entries":sorted(set(install)),
            "exported_targets":sorted(set(exports)),"exported_target_sources":sorted(set(export_sources)),"collection_scope":"cmake_file_api_codemodel_v2",
            "limitations":["Exported targets come from an explicit list or constrained imported-target scan under the supplied install prefix; this is not a substitute for a downstream consumer test.",
                           "Missing install_manifest.txt yields an empty list and is not proof that install was executed."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build-dir",type=Path,required=True); p.add_argument("--build-testing",choices=("ON","OFF"),required=True)
    p.add_argument("--configuration"); p.add_argument("--exported-targets-file",type=Path); p.add_argument("--export-root",type=Path); p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        result=collect(a.build_dir,a.build_testing=="ON",a.configuration,a.exported_targets_file,a.export_root)
        encoded=json.dumps(result,indent=2,ensure_ascii=False)+"\n"; a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(encoded,encoding="utf-8"); print(encoded,end=""); return 0
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(f"collector input error: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
