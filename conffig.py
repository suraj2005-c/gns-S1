import json
import os #pour les dossiers
import re #pour rechercher rapidement

def generate_configurations():
    intent_file = 'intent_file.json'
    output_dir = "configs"
    try: #vérifie si le fichier existe
        with open(intent_file, 'r') as f:
            data = json.load(f)#lis et converti en dico
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{intent_file}' est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de lire le fichier '{intent_file}'. Vérifiez la syntaxe JSON.")
        return
    protocol_definitions = data.get('protocol_definitions',{}) #récupération du fichier json sous forme de dico/get en cas d'oubli crée un dico vide
    if not os.path.exists(output_dir): #si le dossier config n'existe pas ->création  protocol_definitions
        os.makedirs(output_dir)
    project_name = data.get('project_name','Projet_GNS')
    print(f"Demarrage de la generation pour le projet : {project_name}")



    protocoles_list = data.get('protocoles', [])
    # Traducteur pour faire le lien avec ton JSON
    mapping = {"1": "RIP", "OSPF": "OSPF", "RIP": "RIP", "BGP": "BGP"}
    for proto in protocoles_list:
        nom = proto.get('nom', '')
        if nom:
            nom = nom.upper() # Transforme "rip" ou "RIP" en "RIP"
            params = proto.get('parametres', {})
            protocol_definitions[nom] = {
                'protocol_type': 'rip' if nom == 'RIP' else 'ospf' if nom == 'OSPF' else 'bgp',
                'process_id': 1,
                'area': params.get('area', 0),
                # AJOUT des deux lignes manquantes :
                'redistribute_connected': proto.get('redistribution', False),
                'router_id_auto': True
            }
    for router in data['routeurs']:
        hostname = router['hostname']
        print(f"Traitement de la configuration pour {hostname}...")
        lines = []
        lines.append("!")
        lines.append(f"hostname {hostname}")
        lines.append("ipv6 unicast-routing")
        lines.append("!")
        protocols_to_activate = set() #création d'un set vide != liste pour ne pas avoir de doublons active_protocols
        for intf in router['interfaces']:
            lines.append(f"interface {intf['name']}")
            lines.append(f" ipv6 address {intf['ipv6']}")
            lines.append(" ipv6 enable")
            lines.append(" no shutdown")
            active_protos = intf.get('protocole', [])#regarde quel protocole doit etre activé et fait une liste pour chaque routeur
            
            for proto_ref in active_protos: 
                # Traduction de la clé
                proto_name = mapping.get(proto_ref, proto_ref).upper()
                
                if proto_name in protocol_definitions: #verifie si le protocole existe dans le fichier json 
                    recup_prot = protocol_definitions[proto_name]#récupération du protocole sur json
                    protocols_to_activate.add(proto_name)#note le protocole dans le set
                    if recup_prot['protocol_type'] == 'rip':#si cest rip on l'active dans l'interface avec son nom de processus
                        lines.append(" ipv6 rip enable")
                    
                    elif recup_prot['protocol_type'] == 'ospf':#la meme avec ospf
                        lines.append(f" ipv6 ospf {recup_prot['process_id']} area {recup_prot['area']}")
            lines.append(" exit")
            lines.append("!")
        
        for proto_ref in protocols_to_activate: #config le protocole avec le set une fois par routeru
            recup_prot = protocol_definitions[proto_ref]#récupération du protocole sur json

            if recup_prot['protocol_type'] == 'rip': #vérifie si c'est RIP
                lines.append("ipv6 router rip ") #creation du rip global
                if recup_prot.get('redistribute_connected'):#prend les réseaux et les partagent aux routeurs via le protocole
                    lines.append(" redistribute connected")
                lines.append(" exit")

            elif recup_prot['protocol_type'] == 'ospf':
                lines.append(f"ipv6 router ospf {recup_prot['process_id']}")
                if recup_prot.get('router_id_auto'):#cherche le num du routeur pour creer l'id
                    digits = re.findall(r'\d+', hostname)#re.findall cherche partout dans le txt
                    if digits:
                        val = digits[0]#on récupere le premier chiffre du routeur (a modifier)
                        lines.append(f" router-id {val}.{val}.{val}.{val}")#on crée l'id
                    else:# on donne un id par defaut si le routeur n'a pas de chiffre
                        lines.append(" router-id 1.1.1.1")
                lines.append(" exit")
            lines.append("!")

        if 'bgp_neighbors' in router: #on vérifie si le routeur a des voisins bgp dans json
            bgp = router['bgp_neighbors'] #on recup la liste
            num_as = router['asn'] #et le num de l'as
            
            lines.append(f"router bgp {num_as}") #on rentre dans la conf bgp
            nb = hostname.replace('R', '')# on prend que le num et on remplace R par vide
            lines.append(f" bgp router-id {nb}.{nb}.{nb}.{nb}")#creation de l'id
            lines.append(" no bgp default ipv4-unicast")
            
            # voisins bgp
            for neighbor in bgp:
                lines.append(f" neighbor {neighbor['ip']} remote-as {neighbor['remote_as']}")#dit au routeur a quelvoisin parler et dans quel as il est

            lines.append(" !")
            lines.append(" address-family ipv6")
            lines.append("  redistribute connected")
            
            # ajt des Route-Maps
            for neighbor in bgp:
                lines.append(f"  neighbor {neighbor['ip']} activate")#autorisation de communiquer entre routeurs par bgp
                
                # On récupère le nom de la politique dans le JSON
                # Si c'est vide, on met PROV_IN par défaut pour pas que ça bug
                policy_name = neighbor.get('policies', {}).get('in', 'PROV_IN')
                lines.append(f"  neighbor {neighbor['ip']} route-map {policy_name} in")
                
            lines.append(" exit-address-family")
            lines.append(" exit")
        #policies
        lines.append("!")
        lines.append("route-map CLIENT_IN permit 10")
        lines.append(" set local-preference 200")
        lines.append("!")
        lines.append("route-map PEER_IN permit 10")
        lines.append(" set local-preference 150")
        lines.append("!")
        lines.append("route-map PROV_IN permit 10")
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


 #next hop self affiche l'ip du routeur externe -> les routeurs dans l'as ne connaissent pas l'ip. true->ip du routeur frontière affiché
