import json
import re
import os
import random

def inject_ips_into_intent():
    intent_file= 'intent_file.json'
    
    if not os.path.exists(intent_file):
        print(f"Error: {intent_file} not found.")
        return

    with open(intent_file, 'r') as f: #ouvre le fichier en mode lecture et transforme le fichier en un dictionnaire phython
        data = json.load(f)
    
    routers = data['routers']
    nb_routeurs = len(routers)
    router_map = {r['hostname']: r for r in routers}  #crée un dico pour acceder directement au routeur

    prefix_loopback = "2001:100:100:100"
    
    print("--- Loopbacks ---")

    #crée des adresses loopbacks pour chaque routeur
    for r in routers:
        router_id = int(r['hostname'][1:]) #garde l'id du routeur ex: R1
        ip_loopback = f"{prefix_loopback}::{router_id}/128"

        #associer addresse aux loopback
        for intf in r['interfaces']:
            if "Loopback" in intf['nom']: #cherche +vite
                intf['ipv6'] = ip_loopback
                print(f"{r['hostname']} Loopback0 : {ip_loopback}")

        #rechrche des routeurs utilisant BGp ex R3 et R4
        if 'bgp_config' in r:
            r['bgp_config']['router_id'] = f"{router_id}.{router_id}.{router_id}.{router_id}" #fixe le routeur id ex R1->1.1.1.1
            r['bgp_config']['networks'] = [ip_loopback] #liste des reseaux annonncé via bgp

    print("\n--- Physical Links ---")
    
    for k in range(1, nb_routeurs): #ne fonctionne pas pour toutes topologies
#fonctionne en topologie 6 routeurs
        host_left = f"R{k}"
        host_right = f"R{k+1}"
        
        if host_left in router_map and host_right in router_map:
            prefix_link = f"2001:{k}:{k}:{k}" #prefixe unique pour chaque cable
            
            ip_left = f"{prefix_link}::1/64"
            ip_right = f"{prefix_link}::2/64"

            intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['nom'] and "::" not in iface['ipv6']), None) #cherche l'interface de gauche qui n'a pas d'adresse
            
            if not intf_left_obj:
                 intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['nom']), None) #si tt les interfaces ont une @ elle prend l'interface dispo par defaut

            intf_right_obj = next((iface for iface in router_map[host_right]['interfaces'] if "Gigabit" in iface['nom']), None)
            
            if intf_left_obj and intf_right_obj: #vérifie avant de continuer
                intf_left_obj['ipv6'] = ip_left
                intf_right_obj['ipv6'] = ip_right
                
                print(f"Link #{k} ({host_left} <-> {host_right}) :")
                print(f"  {host_left} (Left)  : {ip_left}")
                print(f"  {host_right} (Right) : {ip_right}")


    print("\n--- BGP Neighbors ---")
    for r in routers:
        if 'bgp_config' in r:
            for neighbor in r['bgp_config'].get('neighbors', []): #parcour la liste des voisins bgp 
                old_ip = neighbor['ip'] #recupere l'@ ip temporaire qui est dans le json

                match = re.search(r'::(\d+)', old_ip) #prend le dernier num de @ ip
                if match:
                    neighbor_id = match.group(1) 

                    new_neighbor_ip = f"{prefix_loopback}::{neighbor_id}" #reconstruit l'ip du voisin 
                    neighbor['ip'] = new_neighbor_ip #met a jour le fichier json

    with open(intent_file, 'w') as f: #ouvre fichier en mode ecriture et le modifie
        json.dump(data, f, indent=4)
    
    print(f"\nSuccess. {intent_file} updated with topology rules.")

if __name__ == "__main__":
    inject_ips_into_intent()


