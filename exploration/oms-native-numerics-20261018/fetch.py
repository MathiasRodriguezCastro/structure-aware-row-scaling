"""Freeze candidate metadata and fetch original MPS/DEC without optimizer calls."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request

HERE=Path(__file__).resolve().parent
URL='https://miplib.zib.de/'
KNOWN={'control','network_design','neos-pseudoapplication-89','neos-pseudoapplication-25',
       'neos-pseudoapplication-72','neos-pseudoapplication-11','ustun'}


def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=60) as response:return response.read()


class Table(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,t,a):
        if t=='tr':self.row=[]
        if t=='td':self.cell=[]
    def handle_data(self,d):
        if self.cell is not None:self.cell.append(d)
    def handle_endtag(self,t):
        if t=='td' and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if t=='tr' and self.row:self.rows.append(self.row);self.row=None


def main():
    source=HERE/'sources';source.mkdir(exist_ok=True)
    if (source/'manifest.json').exists():
        for entry in json.loads((source/'manifest.json').read_text()):
            assert sha((source/entry['file']).read_bytes())==entry['sha256']
        print('Frozen native sources verified; no download needed')
        return
    design_path=HERE/'selection.json'
    if not design_path.exists():
        content=get(URL+'tag_numerics.html');p=Table();p.feed(content.decode())
        inventory=[]
        for r in p.rows:
            if len(r)!=12:continue
            item=dict(name=r[0],status=r[1],variables=int(r[2]),binaries=int(r[3]),integers=int(r[4]),
                continuous=int(r[5]),rows=int(r[6]),nonzeros=int(r[7]),submitter=r[8],group=r[9],
                objective_metadata=r[10],tags=r[11].split())
            inventory.append(item)
        assert len(inventory)==193
        eligible=[r for r in inventory if r['continuous'] and r['binaries']+r['integers']
            and r['variables']<=60000 and r['rows']<=100000 and r['nonzeros']<=400000
            and not any(s in r['objective_metadata'].lower() for s in ('infeasible','unbounded'))]
        representatives={}
        for r in sorted(eligible,key=lambda r:(r['nonzeros'],r['name'])):
            key=r['group'] if r['group']!='–' else 'unknown:'+r['name']
            if key not in KNOWN and 'decomposition' in r['tags'] and key not in representatives:
                representatives[key]=r
        selected=[dict(r,stratum='new-decomposition-group') for r in list(representatives.values())[:8]]
        by_name={r['name']:r for r in inventory}
        for name in ('gasprod1-2','cmflsp50-24-10-4','minutedispatchstrategy','ta2-UUE'):
            selected.append(dict(by_name[name],stratum='known-group-new-instance' if name=='ta2-UUE' else 'industrial-energy'))
        assert len({r['name'] for r in selected})==12
        dump(source/'inventory.json',inventory)
        dump(design_path,dict(source=URL+'tag_numerics.html',source_sha256=sha(content),
            protocol_sha256=sha((HERE/'PROTOCOL.md').read_bytes()),previous_groups=sorted(KNOWN),
            selected=selected,optimizer_calls_before_selection=0))
    selected=json.loads(design_path.read_text())['selected']
    jobs=[(r['name'],kind) for r in selected for kind in ('mps','dec')]
    def download(job):
        name,kind=job
        url=URL+('WebData/instances/'+name+'.mps.gz' if kind=='mps' else 'WebData/decomps_orig/'+name+'.dec')
        filename=name+('.mps.gz' if kind=='mps' else '.dec');p=source/filename
        if not p.exists():
            body=get(url)
            if kind=='mps':assert gzip.decompress(body).lstrip().startswith((b'NAME',b'*'))
            else:assert b'BLOCK' in body
            p.write_bytes(body)
        body=p.read_bytes()
        print(name,kind,len(body),flush=True)
        return dict(file=filename,url=url,bytes=len(body),sha256=sha(body))
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(download,jobs))
    dump(source/'manifest.json',records)


if __name__=='__main__':main()
