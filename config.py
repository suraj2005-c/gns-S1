import json
import os
import re

def genere_config():
    intent_file='intent_file.json'
    output_dir='configs'
    try:
        with open(intent_file,'r') as f:
            data=json.load(f)
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{intent_file}' est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de lire le fichier '{intent_file}'. Vérifiez la syntaxe JSON. ")
        return
    protocoles_dict = {p['nom'].lower(): p for p in data.get('protocoles',[])}
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for r in data['routeurs']:
        hostname=r['hostname']
        lines=[]
        lines.append("!")
        lines.append(f"hostname {hostname}")
        lines.append("ipv6 unicast-routing")
        lines.append("!")
        protocoles_a_activer= set()
        for interface in r['interfaces']:
            lines.append(f"interface {interface['name']}")
            lines.append(f" ipv6 address {interface['ipv6']}")
            lines.append(" ipv6 enable")
            lines.append(" no shutdown")
            protocoles_actifs=interface.get('protocole',[])
            for proto in protocoles_actifs:
                protocoles_a_activer.add(proto)
                if proto.lower() == 'rip':
                    lines.append(" ipv6 rip rip1 enable")
                elif proto.lower() == 'ospf':
                    lines.append(" ipv6 ospf 5 area 0")

            lines.append( "exit")
            lines.append("!")
        for proto  in protocoles_a_activer:
            if proto.lower() in protocoles_dict:
                p = protocoles_dict[proto.lower()]
                if p.get('nom').upper() == 'RIP':
                    lines.append("ipv6 router rip rip1")
                    if p.get('parametres',{}).get('redistribution'):
                        lines.append(" redistribute connected")
                    lines.append(" exit")
                elif p.get('nom').upper() == 'OSPF':
                    lines.append("ipv6 router ospf 5")
                    digits = re.findall(r'\d+', hostname)
                    if digits:
                        rid=digits[0]
                        lines.append(f" router-id {rid}.{rid}.{rid}.{rid}")
                    else:
                        lines.append(" router-id 1.1.1.1")
                    lines.append(" exit")
                lines.append("!")
        if 'bgp_neighbors' in r and r['bgp_neighbors']:
            bgp_neighbors = r['bgp_neighbors']
            asn = r['asn']
            lines.append(f"router bgp {asn}")
            
            if 'router_id' in r:
                lines.append(f" bgp router-id {r['router_id']}")
            
            lines.append(" no bgp default ipv4-unicast")
            lines.append(" bgp log-neighbor-changes")
            
            a_voisins_externes = any(n['remote_as'] != asn for n in bgp_neighbors)
            
            if isinstance(bgp_neighbors, list):
                for neighbor in bgp_neighbors:
                    lines.append(f" neighbor {neighbor['ip']} remote-as {neighbor['remote_as']}")
                    if neighbor['remote_as'] == asn:
                        lines.append(f" neighbor {neighbor['ip']} update-source Loopback0")
                    if neighbor.get('update_source'):
                        lines.append(f" neighbor {neighbor['ip']} update-source {neighbor['update_source']}")
                
                lines.append(" !")
                lines.append(" address-family ipv6")
                
                if 'networks' in r:
                    for net in r['networks']:
                        lines.append(f"  network {net}")
                
                for neighbor in bgp_neighbors:
                    lines.append(f"  neighbor {neighbor['ip']} activate")
                    if neighbor['remote_as'] == asn:
                        lines.append(f"  neighbor {neighbor['ip']} next-hop-self")
                    elif neighbor.get('next_hop_self'):
                        lines.append(f"  neighbor {neighbor['ip']} next-hop-self")
                
                lines.append(" exit-address-family")
            
            lines.append(" exit")
            lines.append("!")
        filename=os.path.join(output_dir, f"{hostname}.cfg")
        try:
            with open(filename,'w') as f_out:
                f_out.write('\n'.join(lines))
            print(f"   -> Fichier généré : {filename}")
        except IOError as e:
            print(f"   Erreur lors de l'écriture de {filename} : {e}")
    print(f"\nTerminé. Les configurations se trouvent dans le dossier '{output_dir}'.")

if __name__=='__main__':
    genere_config()



