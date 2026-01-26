import json
import os

def inject_ips_into_intent():
    intent_file="intent_file.json"

    if not os.path.exists(intent_file):
        print(f"Erreur: {intent_file} n'existe pas.")
        return
    
    with open(intent_file, 'r') as file:
        data=json.load(file)

    plages=data.get("plages_ip", {})
    prefixe_physiques=plages["physiques"]
    prefixe_loopback=plages["loopback"]
    routeurs=data.get("routeurs", [])
    routeurs_map={r['hostname']: r for r in routeurs}

    processed_links=set()

    for r in routeurs:
        id=int(r['hostname'][1:])
        hostname=r['hostname']

        ip_loopback=f"{prefixe_loopback}::{id}/128"
        for intf in r['interfaces']:
            if "Loopback" in intf['name']:
                intf['ipv6']=ip_loopback

        if 'bgp_neighbors' in r:
            r['router_id']=f"{id}.{id}.{id}.{id}"
            r['networks']=[ip_loopback]
        
        if 'neighbors' in r :
            for neigh_group in r['neighbors']:
                for n in neigh_group:
                    neighbor_name=n['hostname']
                    local_intf_name=n['interface']

                    if neighbor_name and neighbor_name in routeurs_map:
                        n_id=int(neighbor_name[1:])
                        id_lien=sorted([id,n_id])
                        cle_lien=tuple(sorted([hostname, neighbor_name]))

                        if cle_lien not in processed_links:
                            processed_links.add(cle_lien)
                            indice_lien=f"{id_lien[0]}{id_lien[1]}"
                            prefixe_lien=f"{prefixe_physiques}:{indice_lien}"
                            
                            local_intf_obj = next((i for i in r['interfaces'] if i['name'] == local_intf_name), None)

                            neighbor_r=routeurs_map[neighbor_name]
                            neighbor_intf_obj= None

                            if neighbor_r.get('neighbors'):
                                for nb_groupe in neighbor_r['neighbors']:
                                    for nb_item in nb_groupe:
                                        if nb_item['hostname']== hostname:
                                            nom_intf_cible=nb_item['interface']
                                            neighbor_intf_obj=next(i for i in neighbor_r['interfaces'] if i['name']== nom_intf_cible)
                            
                            if local_intf_obj and neighbor_intf_obj:
                                if id<n_id:
                                    local_intf_obj['ipv6']=f"{prefixe_lien}::1/64"
                                    neighbor_intf_obj['ipv6']=f"{prefixe_lien}::2/64"
                                else:
                                    local_intf_obj['ipv6']=f"{prefixe_lien}::2/64"
                                    neighbor_intf_obj['ipv6']=f"{prefixe_lien}::1/64"

    as_routeurs={}
    for r in routeurs:
        asn=r['asn']
        if asn not in as_routeurs:
            as_routeurs[asn]=[]
        as_routeurs[asn].append(r)

        if 'bgp_neighbors' in r:
            pass
            r['bgp_neighbors']=[]

    for r in routeurs:
        asn_r = r['asn']
        id_r=int(r['hostname'][1:])
        for paire in as_routeurs[asn_r]:
            if paire['hostname']!=r['hostname']:
                id_paire=int(paire['hostname'][1:])
                loopback_paire=f"{prefixe_loopback}::{id_paire}"
                r['bgp_neighbors'].append({
                    'ip': loopback_paire,
                    'remote_as':asn_r
                })
                
        if 'neighbors' in r :
            for neigh_groupe in r['neighbors']:
                for n in neigh_groupe:
                    neighbor_name=n['hostname']
                    if neighbor_name in routeurs_map:
                        neighbor_r=routeurs_map[neighbor_name]

                        if neighbor_r['asn']!=r['asn']:
                            nom_intf_cible=None
                            for nb_groupe in neighbor_r['neighbors']:
                                for nb_item in nb_groupe:
                                    if nb_item['hostname']== r['hostname']:
                                        nom_intf_cible=nb_item['interface']

                            #relationship = relation(r['hostname'], neighbor_name, neighbor_r['asn'])
                            #addPolicies(r['asn'], relationship)
                            
                
                            if nom_intf_cible:
                                intf_neighbor=next((i for i in neighbor_r['interfaces'] if i['name']==nom_intf_cible), None)
                                if intf_neighbor and 'ipv6' in intf_neighbor:
                                    ip_neighbor=intf_neighbor['ipv6'].split('/')[0]
                                    # On demande la relation MAINTENANT
                                    rel = relation(r['hostname'], neighbor_name, neighbor_r['asn'])
                                    
                                    if rel == "STOP":
                                        continue # On saute ce voisin si STOP
                                    # On récupère les infos de politique
                                    policy_infos = addPolicies(r['asn'], rel)

                                    # On crée l'objet FINAL fusionné
                                    neighbor_info = {
                                        'ip': ip_neighbor,
                                        'remote_as': neighbor_r['asn']
                                    }
                                    # On ajoute les clés de la politique dans l'objet voisin
                                    neighbor_info.update(policy_infos)

                                    # 4. On ajoute le tout dans la liste en UNE fois
                                    r['bgp_neighbors'].append(neighbor_info)


        with open(intent_file,'w') as f:
            json.dump(data,f,indent=4)

    print(f"\nSuccess. {intent_file} a été modifié.")


def get_community(asn, relationship):
    if relationship == "customer":
        return f"{asn}:100"
    elif relationship == "peer":
        return f"{asn}:200"
    elif relationship == "provider":
        return f"{asn}:300"
    return None


def relation(r_name, neighbor_name, neighbor_as):
    
    while True:
        print(f"\n[BGP] Configuration de {r_name} vers {neighbor_name} (AS {neighbor_as})")
        relationship = input("Relationship? (ex : 'peer', 'provider', 'customer') ou STOP : ")
        if relationship == "STOP":
            return "STOP"
        elif relationship in ["peer", "provider", "customer"]:
            return relationship
        else:
            print("relationship unknown. Please enter 'peer', 'provider', 'customer' or 'STOP'.")

        # Implémentation des politiques de routage à ajouter ici
def addPolicies(asn, relationship):
         
        if relationship=="provider":
            data = {}
            local_pref_value = 50
            data={
                "relationship" : relationship,
                "local_pref_val": local_pref_value,
                "community": get_community(asn, relationship)
            }
        elif relationship=="customer":
                local_pref_value = 200
                data={
                "relationship" : relationship,
                "local_pref_val": local_pref_value,
                "community": get_community(asn, relationship)
                }
        elif relationship=="peer":
                local_pref_value = 100
                data={
                    "relationship" : relationship,
                    "local_pref_val": local_pref_value,
                    "community": get_community(asn, relationship)
                }   
        

        else:
            print("relationship unknown. Please enter 'peer', 'provider', 'customer' or 'STOP'.")
        return data


if __name__ == "__main__":
    inject_ips_into_intent()    

    
