import json
import os #créer des dossiers et manipuler les chemins de fichiers
import re #recherches rapide
import getpass
import platform

intent_file='intent_file.json' #fichier source

def check_system():
    version = platform.release().lower()
    if "microsoft" in version:
        return "wsl"
    if platform.system() == "Windows":
        return "windows_native"
    return "linux_native"


def get_path():
    ask_path = input("Voulez-vous entrer le chemin vers votre projet GNS3 manuellement ? (y/n) ")

    if ask_path == 'y':
        while True:
            project_path = input("Veuillez entrer le chemin vers votre projet : ")
            if os.path.exists(project_path):
                break
            print("Erreur : Le chemin spécifié n'existe pas. Réessayez.")
    else:
        project_name = input("Entrez le nom du projet : ")
        user = getpass.getuser()
        sys_type = check_system()
        project_path = None

        if sys_type == "wsl":
            win_user = input(f"Nom d'utilisateur Windows (par défaut '{user}') : ") or user
            paths_to_check = [
                f"/mnt/c/Users/{win_user}/GNS3/projects/{project_name}",
                f"/mnt/d/Users/{win_user}/GNS3/projects/{project_name}"
            ]
        elif sys_type == "windows_native":
            paths_to_check = [
                f"C:/Users/{user}/GNS3/projects/{project_name}",
                f"D:/Users/{user}/GNS3/projects/{project_name}"
            ]
        else:
            paths_to_check = [f"/home/{user}/GNS3/projects/{project_name}"]

        for path in paths_to_check:
            if os.path.exists(path):
                project_path = path
                print("Project Path Valide ! ")
                break
        
        if not project_path:
            print("Chemin introuvable, veuillez relancer et/ou entrer le chemin manuellement.")

    return project_path

def getPolicies():
    data = {}
    try:
        with open('intent_file.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Fichier policies.json introuvable. Les politiques par défaut seront utilisées.")
    except json.JSONDecodeError:
        print("Erreur de décodage JSON dans policies.json. Les politiques par défaut seront utilisées.")
    return data

def trouver_fichier_config(dossier_router, nom_fichier):
    for racines, dirs, files in os.walk(dossier_router):# parcourir les dossiers racine=fichier courant, dirs=dossiers, files=fichiers
        if nom_fichier in files:
            return os.path.join(racines, nom_fichier)
        
project_path = get_path()

def trouver_fichier_config(dossier_router, nom_fichier):
    for racines, dirs, files in os.walk(dossier_router):
        if nom_fichier in files:
            return os.path.join(racines, nom_fichier)
        
def configPolicies(lines, r):
    asn = r["asn"]

    # Community-lists définitions des communautés
    lines.append(f"ip community-list standard CUSTOMER permit {asn}:100")
    lines.append(f"ip community-list standard PEER permit {asn}:200")
    lines.append(f"ip community-list standard PROVIDER permit {asn}:300")
    lines.append("!")
    # Route-maps sortie fixe pour marquer les routes locales
    lines.append("route-map TAG-LOCAL permit 10")
    lines.append(f" set community {asn}:100") # On leur donne le badge CUSTOMER
    lines.append("!")

    # Route-maps entree fixe pour chaque type de voisin regarde d'ou ça vient et les marques
    lines.append("route-map FROM-CUSTOMER permit 10")
    lines.append(f" set community {asn}:100 additive")
    lines.append("!")

    lines.append("route-map FROM-PEER permit 10")
    lines.append(f" set community {asn}:200 additive")
    lines.append("!")

    lines.append("route-map FROM-PROVIDER permit 10")
    lines.append(f" set community {asn}:300 additive")
    lines.append("!")

    # Route-maps sortie filtre en fonction du type de voisin
    lines.append("route-map EXPORT-TO-PROVIDER permit 10")
    lines.append(" match community CUSTOMER")
    lines.append("!")
    lines.append("route-map EXPORT-TO-PROVIDER deny 20")
    lines.append("!")

    lines.append("route-map EXPORT-TO-PEER permit 10")
    lines.append(" match community CUSTOMER")
    lines.append("!")
    lines.append("route-map EXPORT-TO-PEER deny 20")
    lines.append("!")

        
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
        lines.append("ip bgp-community new-format")
        lines.append("!")
        protocoles_a_activer= set() #création d'un set vide pour ne pas avoir de doublons
        for interface in r['interfaces']:
            if not interface.get('ipv6') or interface['ipv6'].strip() == '':
                continue
            #configuration de l'interface desIP
            lines.append(f"interface {interface['name']}")
            lines.append(" no ip address")            
            lines.append(" ipv6 enable")
            lines.append(f" ipv6 address {interface['ipv6']}")
            lines.append(" no shutdown")
            protocoles_actifs=interface.get('protocole',[]) #stock liste des proto sur cette interface
            for proto in protocoles_actifs:
                protocoles_a_activer.add(proto) #on ajt ce proto a configurer
                if proto.lower() == 'rip':#RIP ou rip def
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
                    lines.append("ipv6 router rip rip1")#crée rip
                    if p.get('parametres',{}).get('redistribution'):
                        lines.append(" redistribute connected")#annonce à ses voisins que rip est actif
                    lines.append(" exit")
                elif p.get('nom').upper() == 'OSPF':
                    lines.append(f"ipv6 router ospf {asn}")#crée ospf
                    digits = re.findall(r'\d+', hostname) #re.findall extrait le chiffre du nom du routeur
                    if digits:
                        rid=digits[0]
                        lines.append(f" router-id {rid}.{rid}.{rid}.{rid}")
                    else: #id par defaut
                        lines.append(" router-id 1.1.1.1")
                    if p.get('parametres',{}).get('redistribution'):
                        lines.append(" redistribute connected")
                    lines.append(" exit")
                lines.append("!")

        if 'bgp_neighbors' in r and r['bgp_neighbors']:#verif si y'a des voisins BGP
            bgp_neighbors = r['bgp_neighbors']
            asn = r['asn']
            configPolicies(lines, r)  #def routes map et community list
            
            lines.append(f"router bgp {asn}")
            if 'router_id' in r:
                lines.append(f" bgp router-id {r['router_id']}")
            
            lines.append(" no bgp default ipv4-unicast")
            lines.append(" bgp log-neighbor-changes")#affiche si un routeur est down ou up
            
            # Configuration globale des voisins
            if isinstance(bgp_neighbors, list):
                for n in bgp_neighbors:
                    lines.append(f" neighbor {n['ip']} remote-as {n['remote_as']}")#remote as du voisin
                    if n['remote_as'] == asn or n.get('update_source'):#iBGp ou eBgP
                        source = n.get('update_source', 'Loopback0')#update source sur la loopback si ça coupe cherche si source défini sinon loopback0
                        lines.append(f" neighbor {n['ip']} update-source {source}")#source=nom interface
                
                lines.append(" !")
                lines.append(" address-family ipv6")
                lines.append("  redistribute connected route-map TAG-LOCAL") #annonce les routes connectées avec la route map
                
                if 'networks' in r: #annonce les réseaux si y'en a
                    for net in r['networks']:
                       lines.append(f"  network {net} route-map TAG-LOCAL")
                
                # Activation et Politiques par voisin
                for n in bgp_neighbors:
                    lines.append(f"  neighbor {n['ip']} activate")#active bgp
                    lines.append(f"  neighbor {n['ip']} send-community both") #envoie les communautés

                    if n['remote_as'] == asn:
                        lines.append(f"  neighbor {n['ip']} next-hop-self")#passe par le routeur de bordure pour prendre le chemin

                    # Application des route-maps
                    rel = n.get("relationship")
                    if rel == "customer":
                        lines.append(f"  neighbor {n['ip']} route-map FROM-CUSTOMER in")#crée route map
                    elif rel == "peer":
                        lines.append(f"  neighbor {n['ip']} route-map FROM-PEER in")#
                        lines.append(f"  neighbor {n['ip']} route-map EXPORT-TO-PEER out")#filtre les routes envoyé donne que celle qui viennent des clients 
                    elif rel == "provider":
                        lines.append(f"  neighbor {n['ip']} route-map FROM-PROVIDER in")
                        lines.append(f"  neighbor {n['ip']} route-map EXPORT-TO-PROVIDER out")#filtre les routes envoyé donne que celle qui viennent des clients 
                
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

