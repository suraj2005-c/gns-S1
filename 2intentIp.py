import json
import re
import os


def inject_ips_into_intent():
    intent_file= 'intent_file.json'
    
    if not os.path.exists(intent_file):
        print(f"Error: {intent_file} not found.")
        return

    with open(intent_file, 'r') as f: #ouvre le fichier en mode lecture et transforme le fichier en un dictionnaire phython
        data = json.load(f)
    
    routers = data['routeurs']
    nb_routeurs = len(routers)
    router_map = {r['hostname']: r for r in routers}  #crée un dico pour acceder directement au routeur

    prefix_loopback = "2001:100:100:100"
    

    #crée des adresses loopbacks pour chaque routeur
    for r in routers:
        router_id = int(r['hostname'][1:]) #garde l'id du routeur ex: R1
        ip_loopback = f"{prefix_loopback}::{router_id}/128"

        #associer addresse aux loopback
        for intf in r['interfaces']:
            if "Loopback" in intf['name']: #cherche +vite
                intf['ipv6'] = ip_loopback

        #rechrche des routeurs utilisant BGp ex R3 et R4
        if 'bgp_neighbors' in r and isinstance(r['bgp_neighbors'], list):
            r['router_id'] = f"{router_id}.{router_id}.{router_id}.{router_id}" #fixe le routeur id ex R1->1.1.1.1
            r['networks'] = [ip_loopback] #liste des reseaux annonncé via bgp

    link_counter = 1
    processed_links = set()
    
    for r in routers:
        hostname = r['hostname']
        
        if 'neighbors' in r and r['neighbors']:
            for neighbor in r['neighbors']:
                if isinstance(neighbor, list):
                    for n in neighbor:
                        neighbor_name = n.get('hostname') if isinstance(n, dict) else n
                        local_intf_name = n.get('interface') if isinstance(n, dict) else None
                        
                        if neighbor_name and local_intf_name and neighbor_name in router_map:
                            link_key = tuple(sorted([hostname, neighbor_name]))
                            
                            if link_key not in processed_links:
                                processed_links.add(link_key)
                                local_intf_obj = next((i for i in r['interfaces'] if i['name'] == local_intf_name), None)
                                neighbor_r = router_map[neighbor_name]
                                neighbor_intf_obj = None
                                
                                if 'neighbors' in neighbor_r and neighbor_r['neighbors']:
                                    for nb in neighbor_r['neighbors']:
                                        if isinstance(nb, list):
                                            for nb_n in nb:
                                                if nb_n.get('hostname') == hostname:
                                                    neighbor_intf_name = nb_n.get('interface')
                                                    if neighbor_intf_name:
                                                        neighbor_intf_obj = next((i for i in neighbor_r['interfaces'] if i['name'] == neighbor_intf_name), None)
                                                        break
                                
                                if local_intf_obj and neighbor_intf_obj:
                                    prefix_link = f"2001:{link_counter}:{link_counter}:{link_counter}"
                                    local_intf_obj['ipv6'] = f"{prefix_link}::1/64"
                                    neighbor_intf_obj['ipv6'] = f"{prefix_link}::2/64"
                                    link_counter += 1

    
    as_routers = {}
    for r in routers:
        asn = r.get('asn')
        if asn not in as_routers:
            as_routers[asn] = []
        as_routers[asn].append(r)
    

    for r in routers:
        if 'bgp_neighbors' in r:
            r['bgp_neighbors'] = []
        else:
            r['bgp_neighbors'] = []
    

    for r in routers:
        asn = r.get('asn')
        hostname = r['hostname']
        
        for voisin in as_routers.get(asn, []):
            if voisin['hostname'] != hostname:  
                voisin_id = int(voisin['hostname'][1:])
                voisin_loopback = f"{prefix_loopback}::{voisin_id}"
                
                r['bgp_neighbors'].append({
                    'ip': voisin_loopback,
                    'remote_as': asn
                })
    
    for r in routers:
        asn = r.get('asn')
        hostname = r['hostname']
        if 'neighbors' in r and r['neighbors']:
            for neighbor in r['neighbors']:
                if isinstance(neighbor, list):
                    for n in neighbor:
                        neighbor_name = n.get('hostname') if isinstance(n, dict) else n
                        local_intf_name = n.get('interface') if isinstance(n, dict) else None                  
                        if neighbor_name and neighbor_name in router_map:
                            neighbor_r = router_map[neighbor_name]
                            neighbor_asn = neighbor_r.get('asn')
                            if neighbor_asn != asn and neighbor_asn is not None:
                                if 'neighbors' in neighbor_r and neighbor_r['neighbors']:
                                    for nb in neighbor_r['neighbors']:
                                        if isinstance(nb, list):
                                            for nb_n in nb:
                                                if nb_n.get('hostname') == hostname:
                                                    neighbor_intf_name = nb_n.get('interface')
                                                    if neighbor_intf_name:
                                                        neighbor_intf_obj = next((i for i in neighbor_r['interfaces'] if i['name'] == neighbor_intf_name), None)
                                                        if neighbor_intf_obj and neighbor_intf_obj.get('ipv6'):
                                                            neighbor_bgp_ip = neighbor_intf_obj['ipv6'].split('/')[0] if '/' in neighbor_intf_obj['ipv6'] else neighbor_intf_obj['ipv6']
                                                            r['bgp_neighbors'].append({
                                                                'ip': neighbor_bgp_ip,
                                                                'remote_as': neighbor_asn
                                                            })
                                                        break
                                        
    with open(intent_file, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"\nSuccess. {intent_file} a été modifié.")

if __name__ == "__main__":
    inject_ips_into_intent()

