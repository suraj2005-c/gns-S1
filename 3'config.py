import json
import os #créer des dossiers et manipuler les chemins de fichiers
import re #recherches rapide

def genere_config():
    intent_file='intent_file.json' #fichier source
    output_dir='configs' #dossier contenant les fichiers .cfg
    try:
        with open(intent_file,'r') as f:
            data=json.load(f) #lis et converti en dico
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{intent_file}' est introuvable.")
        return
    except json.JSONDecodeError:
        print(f"Erreur : Impossible de lire le fichier '{intent_file}'. Vérifiez la syntaxe JSON. ")
        return
    protocoles_dict = {p['nom'].lower(): p for p in data.get('protocoles',[])} #récupération des protocoles sous forme de dico
    if not os.path.exists(output_dir): #cree le dossier s'il n'existe pas
        os.makedirs(output_dir)
    for r in data['routeurs']: #pour chaque routeur
        asn=r['asn'] #prend le num de l'as
        hostname=r['hostname'] #et son nom
        lines=[]
        lines.append("!")
        lines.append("\n")
        lines.append("!")
        lines.append("version 15.2")
        lines.append("service timestamps debug datetime msec")
        lines.append("service timestamps log datetime msec")
        lines.append("!")
        lines.append(f"hostname {hostname}")
        lines.append("ipv6 unicast-routing")
        lines.append("!")
        protocoles_a_activer= set() #création d'un set vide pour ne pas avoir de doublons
        for interface in r['interfaces']:
            lines.append(f"interface {interface['name']}")
            lines.append(f" ipv6 address {interface['ipv6']}")
            lines.append(" ipv6 enable")
            lines.append(" no shutdown")
            protocoles_actifs=interface.get('protocole',[]) #liste des proto sur cette interface
            for proto in protocoles_actifs:
                protocoles_a_activer.add(proto) #on ajt ce proto a configurer
                if proto.lower() == 'rip':
                    lines.append(f" ipv6 rip rip{asn} enable")
                elif proto.lower() == 'ospf':
                    lines.append(f" ipv6 ospf {asn} area 0")
                    # Ajoute le coût OSPF si défini
                    if 'cost' in interface:
                        lines.append(f" ipv6 ospf cost {interface['cost']}")

            lines.append( "exit")
            lines.append("!")
        for proto in protocoles_a_activer: #config le protocole avec le set une fois par routeur
            if proto.lower() in protocoles_dict: #converti en minuscule lower
                p = protocoles_dict[proto.lower()]
                if p.get('nom').upper() == 'RIP': #upper majuscule
                    lines.append(f"ipv6 router rip rip{asn}")
                    if p.get('parametres',{}).get('redistribution'):
                        lines.append(" redistribute connected")
                    lines.append(" exit")
                elif p.get('nom').upper() == 'OSPF':
                    lines.append(f"ipv6 router ospf {asn}")
                    digits = re.findall(r'\d+', hostname) #re.findall cherche partout dans le txt
                    if digits:
                        rid=digits[0]
                        lines.append(f" router-id {rid}.{rid}.{rid}.{rid}")
                    else: #id par defaut
                        lines.append(" router-id 1.1.1.1")
                    lines.append(" exit")
                lines.append("!")
        if 'bgp_neighbors' in r and r['bgp_neighbors']: #vérifie si le routeur a des voisins bgp
            bgp_neighbors = r['bgp_neighbors'] #on recup la liste
            asn = r['asn'] #et le num de l'as
            lines.append(f"router bgp {asn}") #on rentre dans la conf bgp
            
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
                lines.append(" address-family ipv6") #famille d'adresse ipv6
                
                if 'networks' in r:
                    for net in r['networks']:
                        lines.append(f"  network {net}")
                
                for neighbor in bgp_neighbors:
                    lines.append(f"  neighbor {neighbor['ip']} activate") #active le voisin
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
                f_out.write('\n'.join(lines)) #ecrit les lignes dans le fichier
            print(f"   -> Fichier généré : {filename}")
        except IOError as e:
            print(f"   Erreur lors de l'écriture de {filename} : {e}")
    print(f"\nTerminé. Les configurations se trouvent dans le dossier '{output_dir}'.")

if __name__=='__main__':
    genere_config()
