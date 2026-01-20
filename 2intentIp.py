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

    
    for k in range(1, nb_routeurs): #ne fonctionne pas pour toutes topologies
#fonctionne en topologie 6 routeurs
        host_left = f"R{k}"
        host_right = f"R{k+1}"
        
        if host_left in router_map and host_right in router_map:
            prefix_link = f"2001:{k}:{k}:{k}" #prefixe unique pour chaque cable
            
            ip_left = f"{prefix_link}::1/64"
            ip_right = f"{prefix_link}::2/64"

            intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['name'] and "::" not in iface['ipv6']), None) #cherche l'interface de gauche qui n'a pas d'adresse
            
            if not intf_left_obj:
                 intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['name']), None) #si tt les interfaces ont une @ elle prend l'interface dispo par defaut

            intf_right_obj = next((iface for iface in router_map[host_right]['interfaces'] if "Gigabit" in iface['name']), None)
            
            if intf_left_obj and intf_right_obj: #vérifie avant de continuer
                intf_left_obj['ipv6'] = ip_left
                intf_right_obj['ipv6'] = ip_right

    
    as_routers = {}
    for r in routers:
        asn = r.get('asn')
        if asn not in as_routers:
            as_routers[asn] = []
        as_routers[asn].append(r)
    

    for r in routers:
        if 'bgp_neighbors' in r:
            if not isinstance(r['bgp_neighbors'], list):
                r['bgp_neighbors'] = []
            
            asn = r.get('asn')
            hostname = r['hostname']
            

            for voisin in as_routers.get(asn, []):
                if voisin['hostname'] != hostname:  #n ajoute pas lui meme comme voisin
                    voisin_id = int(voisin['hostname'][1:])
                    voisin_loopback = f"{prefix_loopback}::{voisin_id}"
                    
                    neighbor_exists = any(n.get('ip') == voisin_loopback for n in r['bgp_neighbors'])
                    
                    if not neighbor_exists:
                        r['bgp_neighbors'].append({
                            'ip': voisin_loopback,
                            'remote_as': asn
                        })
            
            for neighbor in r['bgp_neighbors']:
                ip = neighbor.get('ip', '')
                if ip and '::' in ip and ip != f"{prefix_loopback}::{int(r['hostname'][1:])}":
                    match = re.search(r'::(\d+)', ip)
                    if match:
                        neighbor_id = match.group(1)
                        new_neighbor_ip = f"{prefix_loopback}::{neighbor_id}"
                        if neighbor['ip'] != new_neighbor_ip: #evite de reaffecter la meme ip
                            neighbor['ip'] = new_neighbor_ip
    
    for r in routers:
        asn = r.get('asn')
        hostname = r['hostname']
        
        if 'neighbors' in r and r['neighbors']:
            for neighbor in r['neighbors']:
                if isinstance(neighbor, list):
                    for n in neighbor:
                        neighbor_name = n.get('hostname') if isinstance(n, dict) else n
                        neighbor_intf_name = n.get('interface') if isinstance(n, dict) else None
                        
                        if neighbor_name in router_map:
                            neighbor_r = router_map[neighbor_name]
                            neighbor_asn = neighbor_r.get('asn')
                            
                            if neighbor_asn != asn and neighbor_asn is not None:
                                neighbor_intf_obj = None
                                if neighbor_intf_name:
                                    neighbor_intf_obj = next((i for i in neighbor_r['interfaces'] if i['name'] == neighbor_intf_name), None)
                                
                                if neighbor_intf_obj and neighbor_intf_obj.get('ipv6'):
                                    neighbor_bgp_ip = neighbor_intf_obj['ipv6'].split('/')[0] if '/' in neighbor_intf_obj['ipv6'] else neighbor_intf_obj['ipv6']
                                    
                                    neighbor_exists = any(n.get('ip') == neighbor_bgp_ip for n in r['bgp_neighbors'])
                                    
                                    if not neighbor_exists:
                                        r['bgp_neighbors'].append({
                                            'ip': neighbor_bgp_ip,
                                            'remote_as': neighbor_asn
                                        })
                                        
    with open(intent_file, 'w') as f: #ouvre fichier en mode ecriture et le modifie
        json.dump(data, f, indent=4)

    print(f"\nSuccess. {intent_file} a été modifié.")

if __name__ == "__main__":
    inject_ips_into_intent()

