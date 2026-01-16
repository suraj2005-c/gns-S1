import json
import os
import re

def generate_configurations():
    intent_file = 'intent_file.json'
    output_dir = "configs"
    try:
        with open(intent_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{intent_file}' est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de lire le fichier '{intent_file}'. Vérifiez la syntaxe JSON.")
        return
    protocol_definitions = data.get('protocol_definitions', {})
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    project_name = data.get('project_name', 'Projet_Reseau')
    print(f"Demarrage de la generation pour le projet : {project_name}")
    for router in data['routers']:
        hostname = router['hostname']
        print(f"Traitement de la configuration pour {hostname}...")
        lines = []
        lines.append("!")
        lines.append(f"hostname {hostname}")
        lines.append("ipv6 unicast-routing")
        lines.append("!")
        protocols_to_activate = set()
        for intf in router['interfaces']:
            lines.append(f"interface {intf['name']}")
            lines.append(f" ipv6 address {intf['ipv6']}")
            lines.append(" ipv6 enable")
            lines.append(" no shutdown")
            active_protos = intf.get('active_protocols', [])
            
            for proto_ref in active_protos:
                if proto_ref in protocol_definitions:
                    p_def = protocol_definitions[proto_ref]
                    protocols_to_activate.add(proto_ref)
                    if p_def['protocol_type'] == 'rip':
                        lines.append(f" ipv6 rip {p_def['process_name']} enable")
                    
                    elif p_def['protocol_type'] == 'ospf':
                        lines.append(f" ipv6 ospf {p_def['process_id']} area {p_def['area']}")

            lines.append(" exit")
            lines.append("!")
        for proto_ref in protocols_to_activate:
            p_def = protocol_definitions[proto_ref]

            if p_def['protocol_type'] == 'rip':
                lines.append(f"ipv6 router rip {p_def['process_name']}")
                if p_def.get('redistribute_connected'):
                    lines.append(" redistribute connected")
                lines.append(" exit")

            elif p_def['protocol_type'] == 'ospf':
                lines.append(f"ipv6 router ospf {p_def['process_id']}")
                if p_def.get('router_id_auto'):
                    digits = re.findall(r'\d+', hostname)
                    if digits:
                        rid_val = digits[0]
                        lines.append(f" router-id {rid_val}.{rid_val}.{rid_val}.{rid_val}")
                    else:
                        lines.append(" router-id 1.1.1.1")
                lines.append(" exit")
            lines.append("!")
        if 'bgp_config' in router:
            bgp = router['bgp_config']
            local_asn = router['asn']
            lines.append(f"router bgp {local_asn}")
            if 'router_id' in bgp:
                lines.append(f" bgp router-id {bgp['router_id']}")
            lines.append(" no bgp default ipv4-unicast")
            lines.append(" bgp log-neighbor-changes")
            for neighbor in bgp.get('neighbors', []):
                lines.append(f" neighbor {neighbor['ip']} remote-as {neighbor['remote_as']}")
                if neighbor.get('update_source'):
                    lines.append(f" neighbor {neighbor['ip']} update-source {neighbor['update_source']}")
                if neighbor.get('password'):
                    lines.append(f" neighbor {neighbor['ip']} password {neighbor['password']}")
            lines.append(" !")
            lines.append(" address-family ipv6")
            for net in bgp.get('networks', []):
                lines.append(f"  network {net}")
            for neighbor in bgp.get('neighbors', []):
                lines.append(f"  neighbor {neighbor['ip']} activate")
                if 'next_hop_self' in neighbor:
                    if neighbor['next_hop_self']:
                        lines.append(f"  neighbor {neighbor['ip']} next-hop-self")
                elif neighbor['remote_as'] == local_asn:
                    pass
                if 'policies' in neighbor:
                     pol = neighbor['policies']
                     if 'in' in pol:
                        lines.append(f"  neighbor {neighbor['ip']} route-map {pol['in']} in")
                     if 'out' in pol:
                        lines.append(f"  neighbor {neighbor['ip']} route-map {pol['out']} out")
            lines.append(" exit-address-family")
            lines.append(" exit")
        filename = os.path.join(output_dir, f"{hostname}.cfg")
        try:
            with open(filename, 'w') as f_out:
                f_out.write('\n'.join(lines))
            print(f"   -> Fichier genere : {filename}")
        except IOError as e:
            print(f"   Erreur lors de l'ecriture de {filename} : {e}")
    print(f"\nTermine. Les configurations se trouvent dans le dossier '{output_dir}'.")
if __name__ == "__main__":
    generate_configurations()