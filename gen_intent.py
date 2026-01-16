import json
import re
import os
import random

def inject_ips_into_intent():
    intent_file = 'intent_file.json'
    
    if not os.path.exists(intent_file):
        print(f"Error: {intent_file} not found.")
        return

    with open(intent_file, 'r') as f:
        data = json.load(f)
    
    routers = data['routers']
    nb_routeurs = len(routers)
    router_map = {r['hostname']: r for r in routers}

    # 1. ADRESSES LOOPBACK
    # Regle : 2001:100:100:100::i/128
    prefix_loopback = "2001:100:100:100"
    
    print("--- Loopbacks ---")
    for r in routers:
        digits = re.findall(r'\d+', r['hostname'])
        if not digits: continue
        router_id = int(digits[0])

        ip_loopback = f"{prefix_loopback}::{router_id}/128"
        
        # Mise a jour de l'interface Loopback
        for intf in r['interfaces']:
            if "Loopback" in intf['name']:
                intf['ipv6'] = ip_loopback
                print(f"{r['hostname']} Loopback0 : {ip_loopback}")
        
        # Mise a jour BGP (Router ID et Network)
        if 'bgp_config' in r:
            r['bgp_config']['router_id'] = f"{router_id}.{router_id}.{router_id}.{router_id}"
            r['bgp_config']['networks'] = [ip_loopback]

    # 2. ADRESSES D'INTERFACES PHYSIQUES
    # Regle : 2001:k:k:k::1 (gauche) et 2001:k:k:k::2 (droite)
    print("\n--- Physical Links ---")
    
    # On parcourt les liaisons k de 1 a N-1
    for k in range(1, nb_routeurs):
        # Identification des routeurs concernes (Gauche = Ri, Droite = Ri+1)
        host_left = f"R{k}"
        host_right = f"R{k+1}"
        
        if host_left in router_map and host_right in router_map:
            # Construction du prefixe de la liaison k : 2001:k:k:k
            prefix_link = f"2001:{k}:{k}:{k}"
            
            ip_left = f"{prefix_link}::1/64"
            ip_right = f"{prefix_link}::2/64"

            # Pour R_left, on cherche la premiere interface Gigabit non configuree (ou la suivante dispo)
            # Simplification : On prend GigabitEthernet1/0 pour le lien vers la droite si k=1, etc.
            # Ici on cherche dynamiquement une interface Gigabit
            intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['name'] and "::" not in iface['ipv6']), None)
            
            # Si pas d'interface vide trouvée (cas ou le script a deja tourne), on prend celle qui match le pattern ou la derniere
            if not intf_left_obj:
                 intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['name']), None)

            # Idem pour R_right
            intf_right_obj = next((iface for iface in router_map[host_right]['interfaces'] if "Gigabit" in iface['name']), None)

            # Note : Cette selection d'interface est basique. 
            # Dans un cas complexe, il faudrait definir les liaisons explicitement dans le JSON.
            
            if intf_left_obj and intf_right_obj:
                intf_left_obj['ipv6'] = ip_left
                intf_right_obj['ipv6'] = ip_right
                
                print(f"Link #{k} ({host_left} <-> {host_right}) :")
                print(f"  {host_left} (Left)  : {ip_left}")
                print(f"  {host_right} (Right) : {ip_right}")

    # 3. MISE A JOUR DES VOISINS BGP
    # On met a jour les IP des voisins pour qu'elles correspondent aux nouvelles Loopbacks
    print("\n--- BGP Neighbors ---")
    for r in routers:
        if 'bgp_config' in r:
            for neighbor in r['bgp_config'].get('neighbors', []):
                old_ip = neighbor['ip']
                # On recupere l'ID du voisin (ex: le '3' dans ...::3)
                match = re.search(r'::(\d+)', old_ip)
                if match:
                    neighbor_id = match.group(1)
                    # On reconstruit l'IP cible selon la regle Loopback
                    new_neighbor_ip = f"{prefix_loopback}::{neighbor_id}"
                    neighbor['ip'] = new_neighbor_ip

    with open(intent_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"\nSuccess. {intent_file} updated with topology rules.")

if __name__ == "__main__":
    inject_ips_into_intent()