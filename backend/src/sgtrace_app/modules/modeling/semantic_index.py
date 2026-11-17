"""Source facts only from adopted OWL/R2RML; derived dependency sidecar is verified."""
from urllib.parse import unquote
from rdflib import Graph, Namespace, RDF, RDFS, OWL, SKOS
RR=Namespace('http://www.w3.org/ns/r2rml#')
NS='https://vocab.alita.dev/gongshang/'

def source_index(artifacts):
    ontology=Graph().parse(data=artifacts['ontology.ttl'],format='turtle')
    mapping=Graph().parse(data=artifacts['mapping.ttl'],format='turtle',publicID='urn:map:')
    bindings={b['id']:b for b in artifacts['pipeline']['bindings']}
    index={}
    for tm in mapping.subjects(RDF.type,RR.TriplesMap):
        binding_id=str(tm).split('#')[-1].removesuffix('Mapping')
        binding=bindings.get(binding_id)
        if binding is None: continue
        lt=mapping.value(tm,RR.logicalTable)
        table=str(mapping.value(lt,RR.tableName))
        if table!=binding['table_name']: continue
        for pom in mapping.objects(tm,RR.predicateObjectMap):
            pred=mapping.value(pom,RR.predicate)
            obj=mapping.value(pom,RR.objectMap)
            col=mapping.value(obj,RR.column)
            if pred is None or col is None or not any(ontology.triples((pred,RDF.type,None))): continue
            identifier=unquote(str(pred).removeprefix(NS))
            index.setdefault(identifier,[]).append(f'{binding["schema_name"]}.{table}.{col}')
    return ontology,index

def trace(artifacts,snapshot,field):
    ontology,index=source_index(artifacts)
    candidates=[]
    for item in snapshot['items']:
        iri=Namespace(NS)[item['id']]
        names={str(v) for p in (RDFS.label,SKOS.altLabel) for v in ontology.objects(iri,p)}
        if field.strip() not in names: continue
        sources=index.get(item['id'],[])
        if item['kind']=='calculated':
            # Derived properties must exist in OWL; every dependency must be in adopted R2RML.
            known={s for ss in index.values() for s in ss}
            sources=item['sources'] if set(item['sources'])<=known else []
        if sources: candidates.append({'field':field,'kind':item['kind'],'sources':sorted(set(sources)),'item':item})
    if len(candidates)==1: return {**candidates[0],'status':'located'}
    return {'field':field,'status':'ambiguous' if candidates else 'not_found','sources':[], 'candidates':candidates}
