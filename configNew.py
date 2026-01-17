import json
import os #pour les dossiers
import re #pour rechercher rapidement

def generate_configurations():
    intent_file = 'intent_file.json'
    output_dir = "configs"
    try: #vérifie si le fichier existe
        with open(intent_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{intent_file}' est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de lire le fichier '{intent_file}'. Vérifiez la syntaxe JSON.")
        return
    protocol_definitions = data.get('protocol_definitions',{}) #récupération du fichier json sous forme de dico/get en cas d'oubli crée un dico vide
    if not os.path.exists(output_dir): #si le dossier config n'existe pas ->création
        os.makedirs(output_dir)
    project_name = data.get('project_name','Projet_GNS')
    print(f"Demarrage de la generation pour le projet : {project_name}")
    for router in data['routers']:
        hostname = router['hostname']
        print(f"Traitement de la configuration pour {hostname}...")
        lines = []
        lines.append("!")
        lines.append(f"hostname {hostname}")
        lines.append("ipv6 unicast-routing")
        lines.append("!")
        protocols_to_activate = set() #création d'un set vide != liste pour ne pas avoir de doublons
        for intf in router['interfaces']:
            lines.append(f"interface {intf['nom']}")
            lines.append(f" ipv6 address {intf['ipv6']}")
            lines.append(" ipv6 enable")
            lines.append(" no shutdown")
            active_protos = intf.get('active_protocols', [])#regarde quel protocole doit etre activé 
            
            for proto_ref in active_protos: 
                if proto_ref in protocol_definitions: #verifie si le protocole exite dans le fichier json
                    p_def = protocol_definitions[proto_ref]#récupération du protocole sur json
                    protocols_to_activate.add(proto_ref)#note le protocole dans le set
                    if p_def['protocol_type'] == 'rip':#si cest rip on l'active dans l'interface avec son nom de processus
                        lines.append(f" ipv6 rip {p_def['process_name']} enable")
                    
                    elif p_def['protocol_type'] == 'ospf':#la meme avec ospf
                        lines.append(f" ipv6 ospf {p_def['process_id']} area {p_def['area']}")

            lines.append(" exit")
            lines.append("!")
        for proto_ref in protocols_to_activate: #config le protocole avec le set une fois par routeru
            p_def = protocol_definitions[proto_ref]#récupération du protocole sur json

            if p_def['protocol_type'] == 'rip': #vérifie si c'est RIP
                lines.append(f"ipv6 router rip {p_def['process_name']}") #creation du rip global
                if p_def.get('redistribute_connected'):#prend les réseaux et les partagent aux routeurs via le protocole
                    lines.append(" redistribute connected")
                lines.append(" exit")

            elif p_def['protocol_type'] == 'ospf':
                lines.append(f"ipv6 router ospf {p_def['process_id']}")
                if p_def.get('router_id_auto'):#cherche le num du routeur pour creer l'id
                    digits = re.findall(r'\d+', hostname)#re.findall cherche partout dans le txt
                    if digits:
                        rid_val = digits[0]#on récupere le premier chiffre du routeur (a modifier)
                        lines.append(f" router-id {rid_val}.{rid_val}.{rid_val}.{rid_val}")#on crée l'id
                    else:# on donne un id par defaut si le routeur n'a pas de chiffre
                        lines.append(" router-id 1.1.1.1")
                lines.append(" exit")
            lines.append("!")

        if 'bgp_neighbors' in router: #on vérifie si le routeur a des voisins bgp dans json
            bgp = router['bgp_neighbors'] #on recup la liste
            local_asn = router['asn'] #et le num de l'as
            
            lines.append(f"router bgp {local_asn}") #on rentre dans la conf bgp
            rid = hostname.replace('R', '')# on prend que le num et on remplace R par vide
            lines.append(f" bgp router-id {rid}.{rid}.{rid}.{rid}")#creation de l'id
            lines.append(" no bgp default ipv4-unicast")
            
            # voisins bgp
            for neighbor in bgp:
                lines.append(f" neighbor {neighbor['ip']} remote-as {neighbor['remote_as']}")#dit au routeur a quelvoisin parler et dans quel as il est

            lines.append(" !")
            lines.append(" address-family ipv6")
            lines.append("  redistribute connected")
            
            # ajt des route maps
            for neighbor in bgp:
                lines.append(f"  neighbor {neighbor['ip']} activate")#autorisation de communiquer entre routeurs par bgp
                
                # On récupère le nom de la politique dans le JSON
                # Si c'est vide, on met RM_PROV_IN par défaut pour pas que ça bug
                policy_name = neighbor.get('policies', {}).get('in', 'RM_PROV_IN')
                lines.append(f"  neighbor {neighbor['ip']} route-map {policy_name} in")
                
            lines.append(" exit-address-family")
            lines.append(" exit")
        #policies
        lines.append("!")
        lines.append("route-map RM_CLIENT_IN permit 10")
        lines.append(" set local-preference 200")
        lines.append("!")
        lines.append("route-map RM_PEER_IN permit 10")
        lines.append(" set local-preference 150")
        lines.append("!")
        lines.append("route-map RM_PROV_IN permit 10")
        lines.append(" set local-preference 100")
        lines.append("!")
        filename = os.path.join(output_dir, f"{hostname}.cfg")#chemin vers le fichier
        try:
            with open(filename, 'w') as f_out:
                f_out.write('\n'.join(lines))
            print(f"   -> Fichier genere : {filename}")
        except IOError as e:
            print(f"   Erreur lors de l'ecriture de {filename} : {e}")
    print(f"\nTermine. Les configurations se trouvent dans le dossier '{output_dir}'.")
if __name__ == "__main__":
    generate_configurations()
