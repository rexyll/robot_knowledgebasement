#!/usr/bin/env python3
# ruff: noqa: E401, E501, E701, E702, I001
"""Query OSV for every exact Python package version in repository lockfiles."""
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, json, re, sys, tomllib, urllib.error, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; API="https://api.osv.dev/v1"
LINE=re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")
def norm(s:str)->str: return re.sub(r"[-_.]+","-",s).lower()
def add(items:dict,name:str,version:str,scope:str,source:str)->None:
 n=norm(name); x=items.setdefault((n,version),{"name":name,"normalized_name":n,"version":version,"purl":f"pkg:pypi/{urllib.parse.quote(n,safe='-.')}@{urllib.parse.quote(version,safe='')}","scopes":[],"sources":[]})
 if scope not in x["scopes"]: x["scopes"].append(scope)
 if source not in x["sources"]: x["sources"].append(source)
def parse_req(path:Path,scope:str,items:dict)->int:
 count=0
 for line in path.read_text(encoding="utf-8").splitlines():
  m=LINE.match(line.strip())
  if m: add(items,m.group(1),m.group(2),scope,path.name); count+=1
 if not count: raise RuntimeError(f"No exact package pins parsed from {path}")
 return count
def collect():
 items={}; counts={}; lock=tomllib.loads((ROOT/"uv.lock").read_text(encoding="utf-8"))
 for x in lock.get("package",[]): add(items,x["name"],x["version"],"project-uv-lock","uv.lock"); counts["uv.lock packages"]=counts.get("uv.lock packages",0)+1
 for x in lock.get("manifest",{}).get("build-constraints",[]):
  spec=x.get("specifier","")
  if not spec.startswith("=="): raise RuntimeError(f"Non-exact build constraint: {x}")
  add(items,x["name"],spec[2:],"pep517-build-constraints","uv.lock manifest.build-constraints"); counts["uv.lock build constraints"]=counts.get("uv.lock build constraints",0)+1
 counts["SBOM generator lock entries"]=parse_req(ROOT/"requirements-sbom-tools.txt","cyclonedx-generator-toolchain",items)
 counts["PEP 517 build lock entries"]=parse_req(ROOT/"requirements-build-tools.txt","pep517-build-toolchain",items)
 if not counts.get("uv.lock packages") or not counts.get("uv.lock build constraints"): raise RuntimeError("Project lock or build constraints parsed as empty")
 result=sorted(items.values(),key=lambda x:(x["normalized_name"],x["version"]))
 for x in result: x["scopes"].sort(); x["sources"].sort()
 return result,counts
def get_json(url,payload=None):
 data=None if payload is None else json.dumps(payload).encode(); headers={"Accept":"application/json","User-Agent":"robot-knowledgebase-osv-audit/1.0"}
 if data is not None: headers["Content-Type"]="application/json"
 req=urllib.request.Request(url,data=data,headers=headers); error=None
 for _ in range(3):
  try:
   with urllib.request.urlopen(req,timeout=40) as r:
    obj=json.loads(r.read().decode("utf-8"))
    if not isinstance(obj,dict): raise RuntimeError("Unexpected non-object OSV response")
    return obj
  except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc: error=exc
 raise RuntimeError(f"OSV request failed after 3 attempts: {url}: {error}")
def scan(packages):
 response=get_json(API+"/querybatch",{"queries":[{"package":{"purl":p["purl"]}} for p in packages]}); results=response.get("results")
 if not isinstance(results,list) or len(results)!=len(packages): raise RuntimeError("OSV querybatch response count mismatch")
 if any(x.get("next_page_token") for x in results): raise RuntimeError("OSV querybatch paginated; refusing incomplete scan")
 pairs=[]; ids=set()
 for package,result in zip(packages,results,strict=True):
  for v in result.get("vulns",[]):
   if not v.get("id"): raise RuntimeError("OSV result omitted advisory ID")
   pairs.append((package,v["id"])); ids.add(v["id"])
 def detail(vid): return vid,get_json(API+"/vulns/"+urllib.parse.quote(vid,safe=""))
 details={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for vid,obj in pool.map(detail,sorted(ids)): details[vid]=obj
 findings=[]
 for p,vid in pairs:
  v=details[vid]; affected=[a for a in v.get("affected",[]) if a.get("package",{}).get("ecosystem")=="PyPI" and norm(a.get("package",{}).get("name",""))==p["normalized_name"]]
  fixes={e["fixed"] for a in affected for r in a.get("ranges",[]) for e in r.get("events",[]) if e.get("fixed")}
  aliases=sorted(set(v.get("aliases",[]))); cves=sorted({a for a in aliases if a.startswith("CVE-")}|({vid} if vid.startswith("CVE-") else set()))
  findings.append({"package":p["name"],"normalized_package":p["normalized_name"],"version":p["version"],"purl":p["purl"],"scopes":p["scopes"],"sources":p["sources"],"advisory_id":vid,"aliases":aliases,"cve_ids":cves,"summary":v.get("summary"),"severity":v.get("severity",[]),"fix_versions":sorted(fixes),"published":v.get("published"),"modified":v.get("modified"),"references":[r.get("url") for r in v.get("references",[]) if r.get("url")]})
 findings.sort(key=lambda x:(x["normalized_package"],x["version"],x["advisory_id"])); return findings,len(ids)
def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--fail-on-findings",action="store_true"); args=ap.parse_args()
 report={"schema_version":"1.0","scanner":"repository-standard-library-osv-query","advisory_source":"OSV API","advisory_source_url":API,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"scan_error","scope":["uv.lock packages","uv.lock PEP 517 build constraints","requirements-sbom-tools.txt","requirements-build-tools.txt"],"excluded_scope":["ROS 2 packages","apt/dpkg","containers","GPU/CUDA/BSP/kernel/native system libraries","firmware/PLC/vendor SDKs/deployed product components","GitHub Actions and remote source files"]}
 try:
  packages,counts=collect(); findings,n=scan(packages); report.update(status="completed_with_findings" if findings else "completed_no_findings",package_version_count=len(packages),source_entry_counts=counts,unique_advisory_count=n,unique_cve_count=len({c for item in findings for c in item['cve_ids']}),finding_count=len(findings),packages=packages,findings=findings)
  args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  print(f"OSV completed: {len(packages)} package versions; {n} advisories; {len(findings)} findings.")
  return 1 if args.fail_on_findings and findings else 0
 except Exception as exc:
  report["error"]=f"{type(exc).__name__}: {exc}"; args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  print("OSV scan failed; no clean result asserted: "+report["error"],file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
