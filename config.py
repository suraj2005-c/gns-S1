import json
import re
import os
import random

def inject_ips_into_intent():
    intent_file= 'intent_file.json'
    
    if not os.path.exists(intent_file):
        print(f"Error: {intent_file} not found.")
        return

    with open(intent_file, 'r') as f:
        data = json.load(f)
    
    routers = data['routers']
    nb_routeurs = len(routers)
    router_map = {r['hostname']: r for r in routers}

    prefix_loopback = "2001:100:100:100"
    
    print("--- Loopbacks ---")
    for r in routers:
        digits = re.findall(r'\d+', r['hostname'])
        if not digits: continue
        router_id = int(digits[0])

        ip_loopback = f"{prefix_loopback}::{router_id}/128"
        
        for intf in r['interfaces']:
            if "Loopback" in intf['nom']:
                intf['ipv6'] = ip_loopback
                print(f"{r['hostname']} Loopback0 : {ip_loopback}")
        
        if 'bgp_config' in r:
            r['bgp_config']['router_id'] = f"{router_id}.{router_id}.{router_id}.{router_id}"
            r['bgp_config']['networks'] = [ip_loopback]

    print("\n--- Physical Links ---")
    
    for k in range(1, nb_routeurs):

        host_left = f"R{k}"
        host_right = f"R{k+1}"
        
        if host_left in router_map and host_right in router_map:
            prefix_link = f"2001:{k}:{k}:{k}"
            
            ip_left = f"{prefix_link}::1/64"
            ip_right = f"{prefix_link}::2/64"

            intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['nom'] and "::" not in iface['ipv6']), None)
            
            if not intf_left_obj:
                 intf_left_obj = next((iface for iface in router_map[host_left]['interfaces'] if "Gigabit" in iface['nom']), None)

            intf_right_obj = next((iface for iface in router_map[host_right]['interfaces'] if "Gigabit" in iface['nom']), None)
            
            if intf_left_obj and intf_right_obj:
                intf_left_obj['ipv6'] = ip_left
                intf_right_obj['ipv6'] = ip_right
                
                print(f"Link #{k} ({host_left} <-> {host_right}) :")
                print(f"  {host_left} (Left)  : {ip_left}")
                print(f"  {host_right} (Right) : {ip_right}")


    print("\n--- BGP Neighbors ---")
    for r in routers:
        if 'bgp_neighbors' in r:
            for neighbor in r['bgp_neighbors']:
                old_ip = neighbor['ip']

                match = re.search(r'::(\d+)', old_ip)
                if match:
                    neighbor_id = match.group(1)

                    new_neighbor_ip = f"{prefix_loopback}::{neighbor_id}"
                    neighbor['ip'] = new_neighbor_ip

    with open(intent_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"\nSuccess. {intent_file} updated with topology rules.")

if __name__ == "__main__":
    inject_ips_into_intent()
