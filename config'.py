import json
import os #créer des dossiers et manipuler les chemins de fichiers
import re #recherches rapide
import getpass
import platform

intent_file='intent_file.json' #fichier source

def genere_config():


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
    for r in data['routeurs']: #pour chaque routeur
        asn=r['asn'] #prend le num de l'as
        hostname=r['hostname'] #et son nom
        lines=[]
        lines.append("!")
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
            if not interface.get('ipv6') or interface['ipv6'].strip() == '':
                continue
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
                if p.get('nom').upper() == 'RIP':
                    lines.append("ipv6 router rip rip1")
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
                    if p.get('parametres',{}).get('redistribution'):
                        lines.append(" redistribute connected")
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
                for n in bgp_neighbors:
                    lines.append(f" neighbor {n['ip']} remote-as {n['remote_as']}")
                    if n['remote_as'] == asn:
                        lines.append(f" neighbor {n['ip']} update-source Loopback0")
                    if n.get('update_source'):
                        lines.append(f" neighbor {n['ip']} update-source {n['update_source']}")
                
                lines.append(" !")
                lines.append(" address-family ipv6") #famille d'adresse ipv6
                lines.append("  redistribute connected")
                
                if 'networks' in r:
                    for net in r['networks']:
                        lines.append(f"  network {net}")
                
                for n in bgp_neighbors:
                    lines.append(f"  neighbor {n['ip']} activate") #active le voisin
                    if n['remote_as'] == asn:
                        lines.append(f"  neighbor {n['ip']} next-hop-self")
                    elif n.get('next_hop_self'):
                        lines.append(f"  neighbor {n['ip']} next-hop-self")
                    elif n.get('next_hop_self'):
                        lines.append(f"  neighbor {n['ip']} next-hop-self")
                
                lines.append(" exit-address-family")
            
            lines.append(" exit")
            lines.append("!")
        lines.append("!")
        lines.append("line con 0")
        lines.append(" exec-timeout 0 0")
        lines.append(" logging synchronous")
        lines.append(" privilege level 15")
        lines.append(" no login")
        lines.append("line aux 0")
        lines.append(" exec-timeout 0 0")
        lines.append(" logging synchronous")
        lines.append(" privilege level 15")
        lines.append(" no login")
        lines.append("!")
        lines.append("end")
        index=re.findall(r'\d+', hostname)
        index_rtr=index[0]
        filename=f"i{index_rtr}_startup-config.cfg"
        chemin_complet=trouver_fichier_config(project_path,filename)
        try:
            with open(chemin_complet,'w') as f_out:
                f_out.write('\n'.join(lines)) #ecrit les lignes dans le fichier
            print(f"   -> Fichier généré : {filename}")
        except IOError as e:
            print(f"   Erreur lors de l'écriture de {filename} : {e}")
    print(f"\nTerminé. Les fichiers config ont été générés et placés dans les dossiers des routeurs correspondants.")

if __name__=='__main__':
    genere_config()
